import json
import sys
from uuid import UUID, uuid4

from psycopg.types.json import Jsonb

from config import Settings, load_settings
from db import user_transaction
from documents import compute_file_hash, save_snapshot, storage_path
from embedding import embed_texts
from parsing import split_file


def create_processing_run(
        settings:Settings,
        user_id:UUID,
        version_id:UUID,
        config:dict,
) -> UUID:
    with user_transaction(settings,user_id) as conn:
        version = conn.execute(
            "select v.document_id " \
            "from rag.document_versions as v " \
            "join rag.documents as d " \
            "on d.id = v.document_id and d.user_id = v.user_id " \
            "where v.id = %s and d.deleted_at is null",
            (version_id,)
        ).fetchone()

        if version is None:
            raise ValueError(f"文档版本不存在或不属于用户 {user_id}: {version_id}")

        document_id = version[0]

        run = conn.execute(
            "insert into rag.processing_runs " \
            "(user_id, document_id, version_id, config) " \
            "values (%s, %s, %s, %s) " \
            "on conflict (version_id,config_hash) do nothing " \
            "returning id",
            (user_id, document_id, version_id, Jsonb(config)),
        ).fetchone()

        if run is None:
            raise ValueError(f"处理运行已存在: {version_id} {config}")

        run_id = run[0]
    return run_id




def execute_processing_run(settings: Settings, user_id: UUID, run_id: UUID) -> bool:
    """同步执行一个 queued 任务；成功返回 True，失败抛出原始异常。

    当前面向小文件的单进程学习版本，单任务租期 15 分钟；没有后台恢复器。
    成功结果只有仍对应文档最新版本时才会发布为 active_run_id。
    """
    user_id, run_id = UUID(str(user_id)), UUID(str(run_id))
    worker_id = str(uuid4())

    # 1. 用一次条件更新领取任务。事务很短，不在事务里等待模型 API。
    with user_transaction(settings, user_id) as conn: # type: ignore
        run = conn.execute(
            """
            UPDATE rag.processing_runs AS r
            SET status = 'running', worker_id = %s,
                attempt_count = attempt_count + 1, started_at = now(),
                heartbeat_at = now(), lease_expires_at = now() + interval '15 minutes',
                finished_at = NULL, error_code = NULL, error_summary = NULL
            WHERE r.id = %s AND r.status = 'queued' AND r.next_attempt_at <= now()
              AND EXISTS (
                  SELECT 1 FROM rag.documents AS d
                  WHERE d.id = r.document_id AND d.user_id = r.user_id
                    AND d.deleted_at IS NULL
              )
            RETURNING document_id, version_id, config
            """,
            (worker_id, run_id),
        ).fetchone()
        if run is None:
            raise ValueError("任务不存在、不属于当前用户、尚未到执行时间或不是 queued 状态")

    document_id, version_id, config = run
    try:
        # 它固定使用 UTF-8、800 字符和 120 字符重叠，配置必须如实记录。
        parser, chunker = config["parser"], config["chunker"]
        if parser.get("encoding", "utf-8") not in ("utf-8", "utf8", "UTF-8"):
            raise ValueError("当前 parsing.py 只支持 UTF-8 解码")
        if chunker.get("type") not in ("RecursiveTextSplitter", "recursive_character", "RecursiveCharacterTextSplitter"):
            raise ValueError("当前只支持递归字符切分器")
        if chunker.get("chunk_size") != 800 or chunker.get("chunk_overlap") != 120:
            raise ValueError(
                "当前 parsing.py 固定 chunk_size=800、chunk_overlap=120；"
                "请使用匹配配置创建新任务，不能更改已有任务的配置"
            )
        texts = split_file(settings, user_id, version_id)

        # 3. 真实向量全部准备好之后，才开始写 chunks；空白文件无需调用 API。
        vectors = embed_texts(texts, config["embedding"]) if texts else []
        if len(vectors) != len(texts):
            raise ValueError("向量数量与片段数量不一致")

        # 4. split_file 只返回片段列表。将完整列表存为 JSON 快照，
        # locator 用零起始序号定位其中的片段，不伪造原文字符偏移。
        key = f"{user_id}/{document_id}/parsed/{run_id}-{worker_id}.json"
        parsed_bytes = json.dumps({"chunks": texts}, ensure_ascii=False).encode("utf-8")
        save_snapshot(storage_path(settings.raw_storage_dir.resolve(), key), parsed_bytes)

        # 5. 在一个事务内写入片段、结束任务、发布结果，避免出现半份结果。
        with user_transaction(settings, user_id) as conn:
            # 与上传保持一致，先锁文档，再锁任务。
            document = conn.execute(
                "SELECT latest_version_id FROM rag.documents "
                "WHERE id = %s AND deleted_at IS NULL FOR UPDATE",
                (document_id,),
            ).fetchone()
            if document is None:
                raise ValueError("处理期间文档已删除，不能保存结果")
            owned_run = conn.execute(
                "SELECT id FROM rag.processing_runs "
                "WHERE id = %s AND worker_id = %s AND status = 'running' "
                "AND lease_expires_at > now() FOR UPDATE",
                (run_id, worker_id),
            ).fetchone()
            if owned_run is None:
                raise ValueError("任务已取消、租期已到或执行权已改变")

            for ordinal, (content, vector) in enumerate(zip(texts, vectors)):
                locator = {"type": "chunk", "ordinal": ordinal}
                conn.execute(
                    """
                    INSERT INTO rag.chunks (
                        user_id, document_id, version_id, run_id, ordinal,
                        content, embedding, locator
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s::public.vector, %s)
                    """,
                    (user_id, document_id, version_id, run_id, ordinal,
                     content, json.dumps(vector, allow_nan=False), Jsonb(locator)),
                )
            conn.execute(
                """
                UPDATE rag.processing_runs
                SET status = 'succeeded', chunk_count = %s,
                    parsed_storage_key = %s, parsed_sha256 = %s,
                    finished_at = now(), lease_expires_at = NULL
                WHERE id = %s
                """,
                (len(texts), key, compute_file_hash(parsed_bytes), run_id),
            )
            if document[0] == version_id:
                conn.execute(
                    "UPDATE rag.documents SET active_run_id = %s WHERE id = %s",
                    (run_id, document_id),
                )
    except Exception as error:
        # 6. 上面的结果事务已回滚。用新事务记录失败，并保留原始异常。
        # 若提交实际已经成功，status 条件会避免把 succeeded 改回 failed。
        try:
            with user_transaction(settings, user_id) as conn:
                conn.execute(
                    """
                    UPDATE rag.processing_runs
                    SET status = 'failed', finished_at = now(), lease_expires_at = NULL,
                        error_code = %s, error_summary = %s
                    WHERE id = %s AND status = 'running' AND worker_id = %s
                    """,
                    (type(error).__name__, "处理失败；请检查本地异常信息", run_id, worker_id),
                )
        except Exception:
            error.add_note("失败状态也未能写回数据库，请人工核对任务状态")
        # 提交结果不确定时保留解析文件，避免误删已提交记录引用的文件。
        raise
    return True


def main():
    settings = load_settings()
    user_id = UUID("db1e84a8-87c3-4b10-ab50-b56fc99e0a7c")
    run_id = UUID("0fa106e0-cc47-4238-a58c-f19532b28144")
    
    version_id = UUID("d2007773-3720-4213-b22d-707b0bcc1552")
    processing_config = {
        "parser":{
            "mime_type": "text/plain",
            "encoding": "utf-8",
        },
        "chunker":{
            "type":"RecursiveTextSplitter",
            "chunk_size": 800,
            "chunk_overlap": 120,
        },
        "embedding":{
            "provider":"aliyun",
            "model":"qwen3.7-text-embedding-flash",
            "dimensions": 1024,
        },
    }

    run_id = create_processing_run(settings, user_id, version_id, processing_config)
    print(f"任务 ID: {run_id}")
    print(f"执行任务：python processing.py {run_id}")

    if execute_processing_run(settings,user_id,run_id):
        print(f"任务 {run_id} 执行完成")
    else:
        print(f"任务 {run_id} 执行失败")


if __name__ == "__main__":
    main()