"""原文上传：每个版本保存独立的、不可覆盖的文件。"""
import mimetypes
import os
import re
import tempfile
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from uuid import UUID, uuid4

from config import Settings, load_settings
from db import user_transaction


@dataclass(frozen=True)
class UploadResult:
    """统一的上传结果；frozen=True 防止返回后意外修改字段。

    document_id 标识资料，version_id 标识本次使用的原文版本。
    version_no 是资料内部从 1 开始的版本号；storage_key 是相对存储路径。
    created_document 表示是否新建资料；created_version 表示是否新增版本。
    重复内容复用已有版本时，这两个标记均为 False。
    """
    document_id: UUID
    version_id: UUID
    version_no: int
    storage_key: str
    created_document: bool
    created_version: bool


def compute_file_hash(content_bin: bytes) -> str:
    """根据文件原始字节计算 SHA256，用于比较内容是否变化。"""
    return sha256(content_bin).hexdigest()


def storage_path(root: Path, key: str) -> Path:
    """数据库中的相对路径也必须落在原文根目录内。"""
    # resolve 展开 .. 和已有符号链接，再检查最终路径是否仍在根目录内。
    path = (root / key).resolve()
    if path == root or not path.is_relative_to(root):
        raise ValueError("原文路径超出存储目录")
    return path


def save_snapshot(path: Path, content: bytes) -> None:
    """先完整写入同目录临时文件，再原子替换为本版本的正式路径。

    正式路径由新的版本 UUID 生成；失败时清理本函数创建的临时文件。
    这只处理文件写入，不负责提交数据库事务。
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(path)
    temporary = None
    try:
        # 放在目标目录，确保临时文件和目标位于同一文件系统。
        # Windows 下先关闭临时文件，再重命名；因此使用 delete=False。
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(content)
            # flush 清空 Python 缓冲，fsync 请求操作系统将文件数据落盘。
            stream.flush()
            os.fsync(stream.fileno())
        # 读者只会看到完整的正式文件，不会看到写入了一半的内容。
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def upload_file(
    settings: Settings, user_id: UUID, file_path: Path,
    document_id: UUID | None = None,
) -> UploadResult:
    """上传本地文件，或为已有资料增加一个原文版本。

    document_id 为空时新建资料；提供该 ID 时只更新当前用户的未删除资料。
    仅与最新版本比较哈希：A→B→A 仍产生三个版本。
    调用者负责认证身份；此函数只登记原文，不执行解析、切块和向量化。
    只有数据库事务提交成功才返回 UploadResult；失败会抛出异常。
    """
    user_id = UUID(str(user_id))
    file_path = Path(file_path)
    # 只读取一次：计算哈希和保存文件使用同一份字节，避免源文件中途变化。
    content = file_path.read_bytes()
    file_hash = compute_file_hash(content)
    root = settings.raw_storage_dir.resolve()
    # 资料 ID 决定版本归属；同名文件不会自动归为同一资料。
    created_document = document_id is None
    document_id = uuid4() if created_document else UUID(str(document_id))
    # MIME 类型供后续解析器选择处理方式；未知扩展名使用二进制类型。
    media_type = {".txt": "text/plain", ".md": "text/markdown", ".json": "application/json"}.get(
        file_path.suffix.lower(), mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    )

    # 事务内绑定当前用户供 RLS 使用；离开 with 时提交，发生异常则回滚。
    # 文件系统不参与数据库事务，所以仍需在失败路径中单独处理文件。
    with user_transaction(settings, user_id) as conn:
        latest = None
        if created_document:
            # 先创建资料，再插入版本，最后回填 latest_version_id，满足外键关系。
            conn.execute(
                "INSERT INTO rag.documents (id,user_id,title,source_type,source_key) "
                "VALUES (%s,%s,%s,%s,%s)",
                (document_id, user_id, file_path.name, "file", f"upload/{document_id}"),
            )
        else:
            # 锁定资料行，将遵循此流程的并发更新串行化，避免生成相同版本号。
            # 查询同时检查归属和软删除状态，检查通过前不创建存储目录。
            document = conn.execute(
                "SELECT id, latest_version_id FROM rag.documents "
                "WHERE id = %s AND user_id = %s AND deleted_at IS NULL FOR UPDATE",
                (document_id, user_id),
            ).fetchone()
            if document is None:
                raise ValueError("文档不存在、已删除或不属于当前用户")
            # 元组顺序：(版本 ID, 版本号, 原文哈希, 相对存储路径)。
            # 按版本号取最新记录，也允许已有资料暂时没有任何版本。
            latest = conn.execute(
                "SELECT id, version_no, raw_sha256, storage_key FROM rag.document_versions "
                "WHERE document_id = %s AND user_id = %s ORDER BY version_no DESC LIMIT 1",
                (document_id, user_id),
            ).fetchone()

        if latest and latest[2] == file_hash:
            # 哈希相同还要检查实际原文；数据库有记录不代表磁盘文件仍然完整。
            previous_path = storage_path(root, latest[3])
            if compute_file_hash(previous_path.read_bytes()) != file_hash:
                raise ValueError("已有版本的原文哈希不匹配，需要先检查历史文件")
            # 兼容旧流程遗漏最新版本指针的情况，但不修改不可变的版本记录。
            if document[1] != latest[0]:
                conn.execute("UPDATE rag.documents SET latest_version_id = %s WHERE id = %s",
                             (latest[0], document_id))
            result = UploadResult(document_id, latest[0], latest[1], latest[3], False, False)
        else:
            version_id = uuid4()
            version_no = latest[1] + 1 if latest else 1
            # 仅保留简单扩展名；原文件名只作为资料标题，不直接构造保存路径。
            suffix = file_path.suffix.lower()
            if not re.fullmatch(r"\.[a-z0-9]{1,16}", suffix):
                suffix = ".bin"
            # 每个版本拥有独立路径，同名上传或后续更新不会覆盖历史原文。
            key = f"{user_id}/{document_id}/{version_id}{suffix}"
            destination = storage_path(root, key)
            # 原文保存完成后才写版本记录，避免将尚未写好的文件登记为可用。
            save_snapshot(destination, content)
            try:
                conn.execute(
                    "INSERT INTO rag.document_versions "
                    "(id,user_id,document_id,version_no,raw_sha256,storage_key,media_type,byte_size) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                    (version_id, user_id, document_id, version_no, file_hash, key, media_type, len(content)),
                )
                conn.execute("UPDATE rag.documents SET latest_version_id = %s WHERE id = %s",
                             (version_id, document_id))
            except BaseException as error:
                # 同时处理普通异常和中断：数据库回滚不会自动删除磁盘文件。
                # SQL 执行阶段失败，尚未请求提交，可移除本次新增文件。
                try:
                    destination.unlink(missing_ok=True)
                except OSError as cleanup_error:
                    # 清理失败作为补充信息，保留最初的数据库异常供排查。
                    error.add_note(f"清理本次原文失败：{cleanup_error}")
                raise
            result = UploadResult(document_id, version_id, version_no, key, created_document, True)
    # 提交阶段异常不能删除文件：服务器可能已提交，但客户端未收到确认。
    # 这种情况下异常仍向上传播，文件留待核对，不能直接报告上传成功。
    return result


def main():
    """直接修改下方变量后运行此脚本，即可上传原文。"""
    settings = load_settings()
    file_path = Path("C:/Users/茶鸣拾贰率/Desktop/3000字/实习报告.txt")
    user_a = UUID("db1e84a8-87c3-4b10-ab50-b56fc99e0a7c")

    # None 表示创建新资料；更新已有资料时，改为 UUID("已有资料的 document_id")。
    # 更新时使用 document_id，而不是 version_id。
    document_id = None
    result = upload_file(settings, user_a, file_path, document_id)
    print(result)


if __name__ == "__main__":
    main()
