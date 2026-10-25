from dataclasses import dataclass
from http import HTTPStatus
from uuid import UUID

import dashscope
from rich import print as rprint

from config import Settings, load_settings
from retrieval import RecallChunk


@dataclass
class RerankChunk:
    """重排序块"""
    chunk:RecallChunk
    rerank_score: float | None = None

def rerank_chunks(settings: Settings,called_chunks:list[RecallChunk],query:str,top_n:int=5):
    """重排序召回的块"""
    if not called_chunks:
        return []
    if query is None or query.strip() == "":
        raise ValueError("query不能为空")
    if isinstance(top_n,bool) or not isinstance(top_n,int) or 0>=top_n:
        raise ValueError(f"top_n必须是正整数,当前值为{top_n}")
    if top_n>len(called_chunks):
        rprint(f"[yellow]警告: top_n({top_n})大于召回块数量({len(called_chunks)}),将使用召回块数量作为top_n[/yellow]")
    top_n=min(top_n,len(called_chunks))

    resp=dashscope.TextReRank.call(
        model=settings.rerank_model,
        api_key=settings.rerank_api_key,
        query=query,
        documents=[called_chunk.content for called_chunk in called_chunks],
        top_n=top_n,
        # return_documents=True,
    )

    if resp.status_code != HTTPStatus.OK:
        raise RuntimeError(f"重排序请求失败: {resp.status_code} {resp}")
    # print(f"{type(resp)}")
    # rprint(f"重排序结果: {resp}")
    return [RerankChunk(chunk=called_chunks[result["index"]],rerank_score=result["relevance_score"]) for result in resp.output.results]

def main():
    settings = load_settings()
    user_id = UUID("db1e84a8-87c3-4b10-ab50-b56fc99e0a7c")
    query = "毛泽东做了什么"
    embedding_config = {
        "provider": settings.embedding_provider,
        "model": settings.embedding_model,
        "dimensions": settings.embedding_dimensions,
    }
    from retrieval import hybrid_recall
    called_chunks = hybrid_recall(settings, user_id, query, embedding_config, top_k=30)
    rerank_results = rerank_chunks(settings, called_chunks, query, top_n=5)
    # print(f"重排序结果数量：{len(rerank_results)}")
    for rerank_result in rerank_results:
        print(f"重排序结果：{rerank_result.chunk.content}\n重排序分数：{rerank_result.rerank_score}")
        print("***" * 10)

if __name__ == "__main__":
    main()