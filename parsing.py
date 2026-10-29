# import json
import mimetypes
from pathlib import Path
from uuid import UUID

from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
    # RecursiveJsonSplitter,
)

from config import load_settings
from db import user_transaction
from documents import compute_file_hash, storage_path


def mime_extensions(mime_type):
    if not mime_type:
        return set()
    exts = mimetypes.guess_all_extensions(mime_type, strict=False) or []
    return {e.lower() for e in exts} 

def locate_verison_doc(file_path:Path) -> bool:
    return file_path.exists() and file_path.is_file()

def split_text(text: str) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=120)
    return splitter.split_text(text)


def split_file(settings, user_id, version_id)-> list[str]:
    with user_transaction(settings, user_id) as conn:


        row=conn.execute(
            "select storage_key, media_type, raw_sha256, byte_size " \
            "from rag.document_versions " \
            "where id=%s "
            "order by version_no desc limit 1",
            (version_id,)
        ).fetchone() # type: ignore
        if not row:
            raise ValueError(f"文档版本不存在: {version_id}")

    storage_key, media_type, raw_sha256, byte_size = row

    file_path=storage_path(settings.raw_storage_dir, storage_key)
    if not locate_verison_doc(file_path):
        raise ValueError(f"文档版本文件不存在: {file_path}")
    with open(file_path, "rb") as f:
        content=f.read()
        # 校验和解析使用同一份字节，避免损坏的原文被当作已登记版本处理。
        if len(content) != byte_size:
            raise ValueError(f"文档版本原文大小不匹配: {version_id}")
        if compute_file_hash(content) != raw_sha256:
            raise ValueError(f"文档版本原文 SHA-256 不匹配: {version_id}")
        if media_type.startswith("text/"):
            content=content.decode("utf-8")
            splits = split_text(content)
        # elif media_type=="application/json":
        #     content=content.decode("utf-8")
        #     content=json.loads(content)
        #     splitter = RecursiveJsonSplitter(512)
        #     splits=splitter.split_json(content)
        #     splits=[json.dumps(split,ensure_ascii=False) for split in splits]
        else:
            raise ValueError(f"不支持的媒体类型: {media_type}")
    return splits

def main():
    settings = load_settings()
    user_id =UUID("db1e84a8-87c3-4b10-ab50-b56fc99e0a7c")

    doc_id=None
    doc_id=UUID("b6313961-4979-468e-91b2-44d97bfd4103")

    # 模拟获取获取最新版本 ID 的过程，实际使用中应根据业务逻辑获取。
    with user_transaction(settings,user_id) as conn:
        latest_version_id_cur=conn.execute(
        "select latest_version_id " \
        "from rag.documents " \
        "where id=%s "
        "and deleted_at is null ",
        (doc_id,)
        )
        if latest_version_id_cur.rowcount==0:
            raise ValueError(f"文档不存在或不属于用户 {user_id}")
        latest_version_id=latest_version_id_cur.fetchone()[0] if latest_version_id_cur.rowcount>0 else None # type: ignore
        if not latest_version_id:
            raise ValueError(f"文档 {doc_id} 没有最新版本")
    
    splits=split_file(settings,user_id,latest_version_id)
    print(f"分割结果: {len(splits)} 段")


if __name__ == "__main__":
    main()