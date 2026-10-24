"""通过 LangChain 调用阿里云的 OpenAI 兼容向量接口。"""
import math

from langchain_openai import OpenAIEmbeddings

from config import required_env


def embed_texts(texts: list[str], config: dict) -> list[list[float]]:
    """每个输入片段对应一个 1024 维向量，返回顺序与输入一致。"""
    if config.get("provider") != "aliyun" or config.get("dimensions") != 1024:
        raise ValueError("当前只支持阿里云 1024 维向量")
    model = config.get("model")
    if not isinstance(model, str) or not model.strip():
        raise ValueError("embedding 配置缺少模型名称")
    if not texts:
        return []

    client = OpenAIEmbeddings(
        api_key=required_env("DASHSCOPE_API_KEY"),
        base_url=required_env("DASHSCOPE_BASE_URL"),
        model=model,
        dimensions=1024,
        model_kwargs={"encoding_format": "float"},
        # 发送原始字符串，避免用 OpenAI 的 tokenizer 编码阿里云模型输入。
        check_embedding_ctx_length=False,
        chunk_size=10,
        request_timeout=60,
        max_retries=2,
    )
    vectors = client.embed_documents(texts)
    if len(vectors) != len(texts):
        raise ValueError("返回的向量数量与片段数量不一致")
    for vector in vectors:
        if len(vector) != 1024 or not all(math.isfinite(v) for v in vector):
            raise ValueError("向量必须为 1024 维且不能包含 NaN 或无穷大")
        if not any(v != 0 for v in vector):
            raise ValueError("不能保存全零向量")
    return vectors
