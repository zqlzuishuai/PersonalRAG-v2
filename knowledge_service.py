from uuid import UUID

from psycopg.rows import dict_row

from config import Settings
from db import user_transaction
from rerank import rerank_chunks
from retrieval import hybrid_recall


def search_knowledge(settings: Settings, user_id:UUID, query: str, top_k: int = 5):
    """搜索知识库，将结果提取关键信息拼成字典返回"""
    # 验证输入参数
    if not isinstance(query,str):
        raise TypeError("查询必须是字符串")
    if not query.strip():
        raise ValueError("查询不能为空")
    if isinstance(top_k, bool) or not isinstance(top_k, int) or not 1<= top_k <= 20:
        raise ValueError("top_k 必须是1~20的整数")
    
    # 调用混合检索函数
    recall_results = hybrid_recall(settings,user_id,query,top_k=30)

    if not recall_results:
        return []

    # 对结果进行重排序
    rerank_results = rerank_chunks(settings,recall_results,query,top_n=top_k)

    if not rerank_results:
        raise ValueError("重排序时出错，未能返回有效结果")

    chunk_ids = [
        UUID(str(result.chunk.chunk_id))
        for result in rerank_results
    ]

    with user_transaction(settings, user_id) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            rows = cur.execute(
                """
                SELECT c.id AS chunk_id, d.title, v.version_no
                FROM rag.searchable_chunks AS c
                JOIN rag.documents AS d
                    ON d.id = c.document_id
                    AND d.user_id = c.user_id
                JOIN rag.document_versions AS v
                    ON v.id = c.version_id
                    AND v.document_id = c.document_id
                    AND v.user_id = c.user_id
                WHERE c.user_id = %s
                    AND c.id = ANY(%s::uuid[])
                """,
                (user_id, chunk_ids),
            ).fetchall()

    metadata_by_id = {
        row["chunk_id"]: row
        for row in rows
    }

    returning = []
    for result in rerank_results:
        chunk = result.chunk
        metadata = metadata_by_id.get(UUID(str(chunk.chunk_id)))
        # Ignore chunks recycled or superseded since recall.
        if metadata is None:
            continue

        returning.append({
            "chunk_id": str(chunk.chunk_id),
            "document_id": str(chunk.document_id),
            "version_id": str(chunk.version_id),
            "run_id": str(chunk.run_id),
            "title": metadata["title"],
            "version_no": metadata["version_no"],
            "content": chunk.content,
            "locator": chunk.locator,
        })

    return returning

def fetch_knowledge(settings: Settings, user_id: UUID, chunk_id: UUID):
    with user_transaction(settings,user_id) as conn, conn.cursor(row_factory=dict_row) as cur:
        result = cur.execute(
            """
            SELECT 
                c.content,
                d.title,
                v.version_no,
                c.locator
            FROM rag.chunks as c
            JOIN rag.documents as d 
                ON c.document_id = d.id
            JOIN rag.document_versions as v
                ON c.version_id = v.id
            JOIN rag.processing_runs as p
                ON c.run_id = p.id
            WHERE c.id = %s
                AND c.user_id = %s
                AND p.status = 'succeeded' 
                AND d.deleted_at IS NULL
            """,
            (chunk_id, user_id)
        ).fetchone()

        if result is None or len(result) == 0:
            raise ValueError(f"片段不存在或不可访问,chunk_id: {chunk_id}")

        returning={
            "content": result["content"],
            "title": result["title"],
            "version_no": result["version_no"],
            "locator": result["locator"]
        }
        return returning

def main():
    from config import load_settings
    settings = load_settings()
    user_id = UUID("db1e84a8-87c3-4b10-ab50-b56fc99e0a7c")
    query = "毛泽东思想活的灵魂是什么"
    results = search_knowledge(settings,user_id,query,top_k=5)
    # print(f"搜索结果数量：{len(results)}")
    for result in results:
        import json
        print(json.dumps(result,ensure_ascii=False,indent=4,default=str))
if __name__ == "__main__":
    main()