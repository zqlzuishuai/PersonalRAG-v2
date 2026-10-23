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
    )
# print(f"App database URL: {required_env('PERSONALRAG_APP_DATABASE_URL')}")
