import json
from dataclasses import dataclass
from uuid import UUID

from psycopg.rows import dict_row

from config import Settings, load_settings
from db import user_transaction
from embedding import embed_texts


@dataclass
class RecallChunk:
    """召回的块"""
    chunk_id:UUID
    document_id:UUID
    version_id:UUID
    run_id:UUID
    content:str
    locator:dict
    distance:float | None = None
    rrf_score: float | None = None
    vector_distance: float | None = None
    bm25_distance: float | None = None
    

def semantic_recall(settings: Settings,user_id: UUID,query: str, embedding_config: dict, top_k: int =5)-> list[RecallChunk]:
    """搜索文档的向量嵌入块。
    返回粗查询列表
    """

    if query is None or not query.strip():
        raise ValueError("查询字符串不能为空")
    if isinstance(top_k, bool) or not isinstance(top_k, int):
        raise TypeError("top_k 必须是一个正整数")
    if not (1 <= top_k <= 100):
        raise ValueError("top_k 必须在1到100之间")
    # 问题向量化
    query_embedding = embed_texts([query], embedding_config)[0]
    # 查余弦相似度最高的前top_k个块
    with user_transaction(settings, user_id) as conn:
        conn.row_factory=dict_row # type: ignore
        results = conn.execute(
            "select id as chunk_id," \
            "document_id," \
            "version_id," \
            "run_id," \
            "content," \
            "locator," \
            "embedding <=> %s::public.vector as distance " \
            "from rag.searchable_chunks " \
            "where embedding_config = %s::jsonb " \
            "order by embedding <=> %s::public.vector " \
            "limit %s",
            (json.dumps(query_embedding,allow_nan=False),json.dumps(embedding_config,allow_nan=False),json.dumps(query_embedding,allow_nan=False), top_k)
        ).fetchall()
        if not results:
            return []
        return [RecallChunk(**result) for result in results] # type: ignore

def keyword_recall(settings: Settings,user_id: UUID,query: str, top_k: int =5)-> list[RecallChunk]:
    """搜索文档的关键字块。
    返回粗查询列表
    """
    if query is None or not query.strip():
        raise ValueError("查询字符串不能为空")
    if isinstance(top_k, bool) or not isinstance(top_k, int):
        raise TypeError("top_k 必须是一个正整数")
    if not (1 <= top_k <= 100):
        raise ValueError("top_k 必须在1到100之间")
    # 查关键字匹配度最高的前top_k个块
    with user_transaction(settings, user_id) as conn:
        conn.row_factory=dict_row # type: ignore
        results = conn.execute(
            """
            SELECT *
            FROM (
                SELECT
                    id AS chunk_id,
                    document_id,
                    version_id,
                    run_id,
                    content,
                    locator,
                    content <@> public.to_bm25query(
                        %s, 'rag.chunks_content_bm25'
                    ) AS distance
            FROM rag.searchable_chunks
            ) sub
            WHERE distance < 0
            ORDER BY distance
            LIMIT %s
            """,
            (query, top_k),
        ).fetchall()
        if not results:
            return []
        return [RecallChunk(**result) for result in results] # type: ignore
def hybrid_recall(settings: Settings,user_id: UUID,query: str, embedding_config: dict, top_k: int =5,candidate_k = None)-> list[RecallChunk]:
    """搜索文档的向量嵌入块和关键字块。
    返回粗查询列表
    """
    if query is None or not query.strip():
        raise ValueError("查询字符串不能为空")
    if isinstance(top_k, bool) or not isinstance(top_k, int):
        raise TypeError("top_k 必须是一个正整数")
    if not (1 <= top_k <= 100):
        raise ValueError("top_k 必须在1到100之间")
    if candidate_k is not None:
        if isinstance(candidate_k, bool) or not isinstance(candidate_k, int):
            raise TypeError("candidate_k 必须是整数")
        if not (1 <= candidate_k <= 500):
            raise ValueError("candidate_k 必须在 1 到 500 之间")
    # 问题向量化
    query_embedding = embed_texts([query], embedding_config)[0]
    query_text=query
    if candidate_k is None:
        candidate_k = min(max(top_k*4,30),200)
    candidate_k =max(candidate_k,top_k)
    # 查余弦相似度最高的前top_k个块
    with user_transaction(settings, user_id) as conn:
        conn.row_factory=dict_row # type: ignore
        results = conn.execute(
            """
            WITH
                -- 1. 向量召回候选集（只取 id 和 distance，减少物化体积）
                vector_candidates AS (
                    SELECT
                        c.id AS chunk_id,
                        c.embedding <=> %(query_embedding)s::public.vector AS distance
                    FROM rag.searchable_chunks c
                    Where c.embedding_config = %(embedding_config)s::jsonb
                    ORDER BY c.embedding <=> %(query_embedding)s::public.vector
                    LIMIT %(candidate_k)s
                ),
                -- 2. 向量路排名
                vector_ranking AS (
                    SELECT
                        chunk_id,
                        distance,
                        ROW_NUMBER() OVER (ORDER BY distance) AS rank_v
                    FROM vector_candidates
                ),
                -- 3. BM25 召回候选集
                keyword_candidates AS (
                    SELECT
                        c.id AS chunk_id,
                        c.content <@> public.to_bm25query(
                            %(query_text)s, 'rag.chunks_content_bm25'
                        ) AS distance
                    FROM rag.searchable_chunks c
                    ORDER BY c.content <@> public.to_bm25query(
                        %(query_text)s, 'rag.chunks_content_bm25'
                    )
                    LIMIT %(candidate_k)s
                ),
                -- 4. BM25 路排名
                keyword_ranking AS (
                    SELECT
                        chunk_id,
                        distance,
                        ROW_NUMBER() OVER (ORDER BY distance) AS rank_b
                    FROM keyword_candidates
                    WHERE distance < 0
                ),
                -- 5. RRF 融合：FULL OUTER JOIN 保证单路命中的 chunk 不丢
                fused AS (
                    SELECT
                        COALESCE(v.chunk_id, k.chunk_id) AS chunk_id,
                        0.5 * COALESCE(1.0 / (%(rrf_k)s + v.rank_v), 0)
                        + 0.5 * COALESCE(1.0 / (%(rrf_k)s + k.rank_b), 0) AS rrf_score,
                        v.distance AS vector_distance,
                        k.distance AS bm25_distance
                    FROM vector_ranking v
                    FULL OUTER JOIN keyword_ranking k ON v.chunk_id = k.chunk_id
                )
                -- 6. 回表取完整字段，按融合分数排序取最终 Top-K
                SELECT
                    c.id AS chunk_id,
                    c.document_id,
                    c.version_id,
                    c.run_id,
                    c.content,
                    c.locator,
                    f.rrf_score,
                    f.vector_distance,
                    f.bm25_distance
                FROM fused f
                JOIN rag.searchable_chunks c ON c.id = f.chunk_id
                ORDER BY f.rrf_score DESC
                LIMIT %(top_k)s;
            """
            , {
                "query_embedding": json.dumps(query_embedding, allow_nan=False),
                "query_text": query_text,
                "candidate_k": candidate_k,
                "rrf_k": 60,
                "top_k": top_k,
                "embedding_config": json.dumps(embedding_config, allow_nan=False),
            }).fetchall()
        if not results:
            return []
        return [RecallChunk(**result) for result in results] # type: ignore
def main():
    settings = load_settings()
    user_a=UUID("db1e84a8-87c3-4b10-ab50-b56fc99e0a7c")
    query="三步走"
    embedding_config={
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
            "dimensions":settings.embedding_dimensions,
        },
    }
    results_semantic = semantic_recall(settings,user_a,query,embedding_config["embedding"],top_k=50)
    results_keyword = keyword_recall(settings,user_a,query,top_k=50)
    results_hybrid = hybrid_recall(settings,user_a,query,embedding_config["embedding"],top_k=50)
    if results_semantic:
        print(f"向量相似度召回结果数量：{len(results_semantic)}")
        for i,result in enumerate(results_semantic):
            print(f"向量相似度召回结果：{i}\n{result.content}")
            print("***"*10)
        # print(f"向量相似度召回结果：\n{results_semantic[0].content}")
    print("==="*20)
    if results_keyword:
        print(f"关键字召回结果数量：{len(results_keyword)}")
        for i,result in enumerate(results_keyword):
            print(f"关键字召回结果：{i}\n{result.content}")
            print("***"*10)
        # print(f"关键字召回结果：\n{results_keyword[0].content}")
    print("==="*20)
    if results_hybrid:
        print(f"混合召回结果数量：{len(results_hybrid)}")
        for i,result in enumerate(results_hybrid):
            print(f"混合召回结果：{i}\n{result.content}")
            print("***"*10)
        # print(f"混合召回结果：\n{results_hybrid[0].content}")
if __name__ == "__main__":
    main()