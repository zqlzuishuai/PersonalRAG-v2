import json
from uuid import UUID, uuid4

from psycopg import Error as PsycopgError
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from config import Settings, load_settings
from db import user_transaction
from documents import compute_file_hash, save_snapshot, storage_path
from embedding import embed_texts
from parsing import split_file


class ProcessingRunNotClaimedError(ValueError):
    """本次调用未领取到任务"""

class VersionNotFoundError(ValueError):
    """文档版本不存在或不属于用户"""

def create_processing_run(
        settings:Settings,
        user_id:UUID,
        version_id:UUID,
        config:dict,
) -> UUID:
    """创建一个处理运行；若已存在相同配置的运行，则返回其 ID"""
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
            raise VersionNotFoundError(f"文档版本不存在或不属于用户 {user_id}: {version_id}")

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
            run = conn.execute(
                """
                SELECT id
                FROM rag.processing_runs
                WHERE version_id = %s 
                    AND config_hash = rag.json_sha256(%s::jsonb)
                    AND user_id = %s
                """,
                (version_id, Jsonb(config), user_id)
            ).fetchone()

            if run:
                return run[0]
            else:
                raise RuntimeError("任务创建发生冲突，但未找到对应的处理运行")
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
            raise ProcessingRunNotClaimedError("任务不存在、不属于当前用户、尚未到执行时间或不是 queued 状态")

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
        except PsycopgError as recovery_error:
            error.add_note("失败状态也未能写回数据库，请人工核对任务状态")
        # 提交结果不确定时保留解析文件，避免误删已提交记录引用的文件。
        raise
    return True

def get_processing_run(
        settings: Settings,
        user_id: UUID,
        run_id: UUID,
)->dict:
    """获取一个处理运行的详细信息"""
    with user_transaction(settings, user_id) as conn,conn.cursor(row_factory=dict_row) as cur:
        row=cur.execute(
            """
            SELECT r.id,
                r.document_id,
                r.version_id,
                r.config_hash,
                r.status,
                r.attempt_count,
                r.chunk_count,
                r.next_attempt_at,
                r.error_code,
                r.error_summary,
                r.created_at,
                r.updated_at,
                r.started_at,
                r.finished_at,
                COALESCE(d.active_run_id = r.id, FALSE) AS is_published,
                COALESCE(d.latest_version_id = r.version_id, FALSE) AS is_latest_version
            FROM rag.processing_runs AS r
            JOIN rag.documents AS d ON d.id = r.document_id AND d.user_id = r.user_id
            WHERE r.id=%s
                AND r.user_id=%s
                AND d.deleted_at IS NULL
            """,
            (run_id,user_id)
        ).fetchone()

        if not row:
            raise ValueError(f"处理运行不存在或不属于用户或所属资料已删除 {user_id}: {run_id}")

        return row


def list_version_processing_runs(
    settings: Settings,
    user_id: UUID,
    version_id: UUID,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """列出一个文档版本的处理运行列表"""
    if isinstance(limit,bool) or not isinstance(limit, int):
        raise TypeError("limit必须是整数")
    if isinstance(offset,bool) or not isinstance(offset, int):
        raise TypeError("offset必须是整数")
    
    if not 1 <= limit <= 100:
        raise ValueError("limit必须在1~100之间")
    if offset<0:
        raise ValueError("offset必须大于等于0")

    with user_transaction(settings, user_id) as conn,conn.cursor(row_factory=dict_row) as cur:
        row=cur.execute(
            """
            SELECT 1
            FROM rag.document_versions AS v
            JOIN rag.documents AS d 
                ON d.id = v.document_id 
                AND d.user_id = v.user_id
            WHERE v.id=%s
                AND d.user_id=%s
                AND d.deleted_at IS NULL
            """,
            (version_id,user_id)
        ).fetchone()
        if not row:
            raise VersionNotFoundError(f"文档版本不存在或不属于用户或所属资料已删除 {user_id}: {version_id}")

        results=cur.execute(
            """
            SELECT r.id,
                r.document_id,
                r.version_id,
                r.config_hash,
                r.status,
                r.attempt_count,
                r.chunk_count,
                r.next_attempt_at,
                r.error_code,
                r.error_summary,
                r.created_at,
                r.updated_at,
                r.started_at,
                r.finished_at,
                COALESCE(d.active_run_id = r.id, FALSE) AS is_published,
                COALESCE(d.latest_version_id = r.version_id, FALSE) AS is_latest_version
            FROM rag.processing_runs AS r
            JOIN rag.documents AS d ON d.id = r.document_id AND d.user_id = r.user_id
            WHERE r.version_id=%s
                AND r.user_id=%s
                AND d.deleted_at IS NULL
            ORDER BY r.created_at DESC,r.id DESC
            LIMIT %s OFFSET %s
            """,
            (version_id,user_id,limit,offset)
        ).fetchall()

    return results

def build_processing_config(
        settings: Settings,
)->dict:
    if settings.embedding_chunk_size != 800:
        raise ValueError("当前解析器要求切块大小为 800")

    if settings.embedding_chunk_overlap != 120:
        raise ValueError("当前解析器要求切块重叠为 120")

    if settings.embedding_dimensions != 1024:
        raise ValueError("当前数据库要求向量维度为 1024")
    processing_config = {
        "parser":{
            "mime_type": "text/plain",
            "encoding": "utf-8",
        },
        "chunker":{
            "type":"RecursiveTextSplitter",
            "chunk_size": settings.embedding_chunk_size,
            "chunk_overlap": settings.embedding_chunk_overlap,
        },
        "embedding":{
            "provider":settings.embedding_provider,
            "model":settings.embedding_model,
            "dimensions": settings.embedding_dimensions,
        },
    }
    return processing_config

def process_version(
        settings: Settings,
        user_id: UUID,
        version_id: UUID,
        config: dict | None = None,
)->dict:
    """处理入口，创建并执行文档版本的处理运行。

    参数:
        settings: 用于创建和执行处理运行的应用配置。
        user_id: 文档版本所属用户的标识。
        version_id: 要处理的文档版本标识。
        config: 可选的处理配置；省略时使用基于应用配置生成的默认配置。

    返回:
        最终的处理运行状态。
    """
    if config is None:
        config = build_processing_config(settings)
    run_id=create_processing_run(settings, user_id, version_id, config)
    run_status=get_processing_run(settings, user_id, run_id)
    if run_status["status"]=="queued":
        try:
            execute_processing_run(settings, user_id, run_id)
            run_status=get_processing_run(settings, user_id, run_id)
        except ProcessingRunNotClaimedError as e:
            run_status=get_processing_run(settings, user_id, run_id)
            return run_status

    return run_status

def main():
    from rich import print as rprint
    settings = load_settings()
    user_id = UUID("db1e84a8-87c3-4b10-ab50-b56fc99e0a7c")
    # run_id = UUID("0fa106e0-cc47-4238-a58c-f19532b28144")
    
    # version_id = UUID("d2007773-3720-4213-b22d-707b0bcc1552")
    version_id = UUID("e42d100d-8d28-402b-bb7a-728458806b05") # 毛概
    from documents import upload_bytes
    uploadResult=upload_bytes(
        settings,
        user_id,
        "1.txt",
        content=open("1.txt", "rb").read()
    )
    # 处理文档版本
    run_status = process_version(settings, user_id, uploadResult.version_id)
    rprint("处理运行状态:", run_status)

    if run_status["status"] == "succeeded" and run_status["is_published"]:
        rprint("处理成功并已发布为最新版本的运行。")


if __name__ == "__main__":
    main()