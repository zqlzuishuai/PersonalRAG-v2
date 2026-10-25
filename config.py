import os
from dotenv import load_dotenv
from dataclasses import dataclass,field
from pathlib import Path

ENV=Path(__file__).resolve().parent / ".env"
load_dotenv(ENV,override=True)
@dataclass(frozen=True)
class Settings:
    app_database_url: str = field(repr=False)
    auth_database_url: str = field(repr=False)
    raw_storage_dir: Path
    chat_model_api_key:str = field(repr=False)
    chat_model_base_url:str
    chat_model_provider:str
    chat_model_name:str
    embedding_provider: str
    embedding_model: str
    embedding_dimensions: int
    embedding_chunk_size: int
    embedding_chunk_overlap: int
    # embedding_request_timeout: int = field(default=60)
    embedding_api_key: str = field(repr=False)
    rerank_provider: str
    rerank_model: str
    rerank_api_key: str = field(repr=False)

def required_env(name: str) -> str:
    value = os.getenv(name,"").strip()
    if not value:
        raise ValueError(f"缺少环境变量:{name}")
    return value

def load_settings() -> Settings:

    return Settings(
        app_database_url=required_env("PERSONALRAG_APP_DATABASE_URL"),
        auth_database_url=required_env("PERSONALRAG_AUTH_DATABASE_URL"),
        raw_storage_dir=Path(
            os.getenv("PERSONALRAG_RAW_STORAGE_DIR", "./data/raw")
        ).resolve(),
        chat_model_name=required_env("CHAT_MODEL_NAME"),
        chat_model_api_key=required_env("CHAT_MODEL_API_KEY"),
        chat_model_base_url=required_env("CHAT_MODEL_BASE_URL"),
        chat_model_provider=required_env("CHAT_MODEL_PROVIDER"),
        embedding_provider=required_env("PERSONALRAG_EMBEDDING_PROVIDER"),
        embedding_model=required_env("PERSONALRAG_EMBEDDING_MODEL"),
        embedding_dimensions=int(required_env("PERSONALRAG_EMBEDDING_DIMENSIONS")),
        embedding_chunk_size=int(required_env("PERSONALRAG_EMBEDDING_CHUNK_SIZE")),
        embedding_chunk_overlap=int(required_env("PERSONALRAG_EMBEDDING_CHUNK_OVERLAP")),
        embedding_api_key=required_env("DASHSCOPE_API_KEY"),
        rerank_provider=required_env("PERSONALRAG_RERANK_PROVIDER"),
        rerank_model=required_env("PERSONALRAG_RERANK_MODEL"),
        rerank_api_key=required_env("DASHSCOPE_API_KEY"),
    )
# print(f"{load_settings()}")
