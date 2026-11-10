"""原文上传：每个版本保存独立的、不可覆盖的文件。"""
import mimetypes
import os
import re
import tempfile
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from uuid import UUID, uuid4

from psycopg.rows import dict_row

from config import Settings, load_settings
from db import lock_folder_tree, user_transaction


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

class FolderNotFoundError(ValueError):
    """指定的文件夹不存在或不属于当前用户。"""

class DocumentRestoreConflictError(ValueError):
    """The document must be restored through its folder or after its folder."""


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
    settings: Settings, 
    user_id: UUID, 
    file_path: Path,
    document_id: UUID | None = None,
    *,
    folder_id: UUID | None = None
) -> UploadResult:
    """上传本地文件，或为已有资料增加一个原文版本。"""
    if document_id is not None and folder_id is not None:
        raise ValueError("请使用move_document移动资料到文件夹")
    file_path = Path(file_path)
    return upload_bytes(
        settings=settings,
        user_id=user_id,
        file_name=file_path.name,
        content=file_path.read_bytes(),
        document_id=document_id,
        folder_id=folder_id
    )





def upload_bytes(
        settings: Settings,
        user_id: UUID,
        file_name: str,
        content: bytes,
        document_id: UUID | None = None,
        *,
        folder_id: UUID | None = None
    ) -> UploadResult:
    """上传字节内容，或为已有资料增加一个原文版本。

    Args:
        settings: 应用配置，包含原始文件存储目录等设置。
        user_id: 当前用户的唯一标识。
        file_name: 原始文件名，必须是纯文件名，不能包含路径分隔符。
        content: 文件的字节内容。
        document_id: 要追加版本的资料 ID；为 ``None`` 时创建新资料。
        folder_id: 新资料所属文件夹 ID。与 ``document_id`` 不能同时提供。

    Returns:
        事务成功提交后返回的上传结果。
    """
    # 类型检查
    if document_id is not None and folder_id is not None:
        raise ValueError("请使用move_document移动资料到文件夹")

    if not isinstance(file_name, str):
        raise TypeError("file_name必须是字符串")
    
    file_name = file_name.strip()

    if not file_name.strip():
        raise ValueError("file_name不能为空")

    if file_name in {".", ".."} or any(
        char in file_name for char in ("/", "\\", "\x00")
    ):
        raise ValueError("file_name必须是纯文件名")

    if not isinstance(content, bytes):
        raise TypeError("content必须是字节类型")


    file_hash = compute_file_hash(content)
    root = settings.raw_storage_dir.resolve()
    # 资料 ID 决定版本归属；同名文件不会自动归为同一资料。
    created_document = document_id is None
    document_id = uuid4() if created_document else UUID(str(document_id))
    # MIME 类型供后续解析器选择处理方式；未知扩展名使用二进制类型。
    media_type = {".txt": "text/plain", ".md": "text/markdown", ".json": "application/json"}.get(
        Path(file_name).suffix.lower(), mimetypes.guess_type(file_name)[0] or "application/octet-stream"
    )


    # 事务内绑定当前用户供 RLS 使用；离开 with 时提交，发生异常则回滚。
    # 文件系统不参与数据库事务，所以仍需在失败路径中单独处理文件。
    with user_transaction(settings, user_id) as conn:
        latest = None
        if created_document:
            # 先创建资料，再插入版本，最后回填 latest_version_id，满足外键关系。
            # 查资料前先确定 folder_id 是否存在且属于当前用户，避免创建无效资料。
            if folder_id:
                lock_folder_tree(conn, user_id)
                row=conn.execute(
                    """
                    SELECT id 
                    FROM rag.folders 
                    WHERE id = %s 
                        AND user_id = %s
                        AND deleted_at IS NULL
                    """,
                    (folder_id, user_id)
                ).fetchone()

                if not row:
                    raise FolderNotFoundError("指定的文件夹不存在或不属于当前用户")

            # 新建资料
            conn.execute(
                "INSERT INTO rag.documents (id, folder_id, user_id, title, source_type, source_key) "
                "VALUES (%s,%s,%s,%s,%s,%s)",
                (document_id, folder_id, user_id, file_name, "file", f"upload/{document_id}"),
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
            suffix = Path(file_name).suffix.lower()
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


def list_documents(
    settings: Settings,
    user_id: UUID,
    folder_id: UUID | None = None,
    limit: int = 50,
    offset: int = 0,
    *,
    scope: str = "folder",
    q: str | None = None,
    tags: list[str] | None = None,
) -> list[dict]:
    """列出未删除的资料，可按目录范围、标题和标签筛选。

    Args:
        settings: 应用配置。
        user_id: 用户 ID。
        folder_id: 文件夹 ID；为空时表示根目录。
        limit: 返回的最大资料数，范围为 1~100。
        offset: 跳过的资料数。
        scope: 查询范围，可选 ``folder``、``subtree`` 或 ``all``。
        q: 按标题筛选的关键词。
        tags: 按标签筛选的标签列表。

    Returns:
        未删除的资料的字典列表。
    """
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise TypeError("limit必须是整数")
    if isinstance(offset, bool) or not isinstance(offset, int):
        raise TypeError("offset必须是整数")
    if not 1 <= limit <= 100:
        raise ValueError("limit必须在1~100之间")
    if offset < 0:
        raise ValueError("offset必须大于等于0")

    if scope not in ("folder", "all", "subtree"):
        raise ValueError("scope必须是folder、all或subtree")
    if scope == "subtree" and folder_id is None:
        raise ValueError("subtree范围必须指定folder_id")
    if scope == "all" and folder_id is not None:
        raise ValueError("all范围不能同时指定folder_id")
    if q is not None and not isinstance(q, str):
        raise TypeError("q必须是字符串")
    if tags is not None and (
        not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags)
    ):
        raise TypeError("tags必须是字符串列表")

    params = {"user_id": user_id, "limit": limit, "offset": offset}
    conditions = ["d.user_id = %(user_id)s", "d.deleted_at IS NULL"]
    cte = ""
    if scope == "subtree":
        cte = """
        WITH RECURSIVE folder_tree(id) AS (
            SELECT id
            FROM rag.folders
            WHERE id = %(folder_id)s AND user_id = %(user_id)s AND deleted_at IS NULL

            UNION

            SELECT f.id
            FROM rag.folders AS f
            JOIN folder_tree AS t ON f.parent_id = t.id
            WHERE f.user_id = %(user_id)s AND f.deleted_at IS NULL
        )
        """
        params["folder_id"] = folder_id
        conditions.append("d.folder_id IN (SELECT id FROM folder_tree)")
    elif scope == "folder":
        if folder_id is None:
            conditions.append("d.folder_id IS NULL")
        else:
            params["folder_id"] = folder_id
            conditions.append("d.folder_id = %(folder_id)s")

    if q and (title := q.strip()):
        escaped = title.replace("!", "!!").replace("%", "!%").replace("_", "!_")
        params["title"] = f"%{escaped}%"
        conditions.append("d.title ILIKE %(title)s ESCAPE '!'")

    if tags:
        clean_tags = list(dict.fromkeys(tag.strip() for tag in tags))
        if any(not tag or len(tag) > 50 for tag in clean_tags):
            raise ValueError("标签长度必须在1~50之间")
        params["tags"] = clean_tags
        conditions.append("d.tags @> %(tags)s::text[]")

    where = " AND ".join(conditions)
    query = f"""
        {cte}
        SELECT d.id, d.title, d.folder_id, d.tags, d.source_type,
               d.latest_version_id, d.active_run_id, d.updated_at
        FROM rag.documents AS d
        WHERE {where}
        ORDER BY d.updated_at DESC, d.id DESC
        LIMIT %(limit)s OFFSET %(offset)s
    """
    with user_transaction(settings, user_id) as conn, conn.cursor(row_factory=dict_row) as cur:
        return cur.execute(query, params).fetchall() # type: ignore


def move_document(
        settings: Settings, 
        user_id: UUID, 
        document_id: UUID, 
        target_folder_id: UUID | None=None
        ):
    """移动资料到指定文件夹，或移至根目录（target_folder_id=None）。"""
    with user_transaction(settings,user_id) as conn:
        lock_folder_tree(conn, user_id)
        row=conn.execute(
            """
            SELECT id
            FROM rag.documents
            WHERE user_id=%s
                AND id=%s
                AND deleted_at IS NULL
            """,
            (user_id, document_id)
        ).fetchone()

        if row is None:
            raise ValueError("资料不存在、已删除或不属于当前用户")



        if target_folder_id:
            # 检查目标文件夹是否存在且属于当前用户
            folder=conn.execute(
                """
                SELECT id
                FROM rag.folders
                WHERE user_id=%s
                    AND id=%s
                    AND deleted_at IS NULL
                """,
                (user_id, target_folder_id)
            ).fetchone()
            if folder is None:
                raise FolderNotFoundError("目标文件夹不存在或不属于当前用户")

        # 更新资料的文件夹
        row=conn.execute(
            """
            UPDATE rag.documents
            SET folder_id=%s
            WHERE id=%s
                AND user_id=%s
                AND deleted_at IS NULL
            RETURNING id
            """,
            (target_folder_id if target_folder_id is not None else None, document_id,user_id)
        ).fetchone()

        if row is None:
            raise RuntimeError("移动资料失败，可能是因为不存在或其他原因")
    return row[0]


def rename_document(
        settings:Settings,
        user_id:UUID,
        document_id:UUID,
        new_title:str
        )->UUID:
    """重命名文件资料标题，覆盖原有标题。"""
    if not isinstance(new_title,str):
        raise TypeError("new_title必须是字符串")

    
    new_title=new_title.strip()


    # 检查new_title是否为空或长度不在1-200之间
    if not new_title:
        raise ValueError("新标题不能为空")
    if len(new_title) < 1 or len(new_title) > 200:
        raise ValueError("新标题长度必须在1-200个字符之间")
    with user_transaction(settings,user_id) as conn:
        # 检查资料是否存在且属于当前用户
        document=conn.execute(
            """
            SELECT id
            FROM rag.documents
            WHERE user_id=%s
                AND id=%s
                AND deleted_at IS NULL
            """,
            (user_id, document_id)
        ).fetchone()
        if not document:
            raise ValueError("资料不存在、已删除或不属于当前用户")

        # 更新资料标题
        updated=conn.execute(
            """
            UPDATE rag.documents
            SET title=%s
            WHERE user_id=%s
                AND id=%s
                AND deleted_at IS NULL
            RETURNING id
            """,
            (new_title, user_id, document_id)
        ).fetchone()

        if not updated:
            raise RuntimeError("重命名资料失败，可能是因为不存在或其他原因")
    return updated[0]


def set_document_tags(
        settings: Settings,
        user_id: UUID,
        document_id: UUID,
        tags: list[str]
        )->UUID:
    """设置资料的标签列表，覆盖原有标签。"""

    if not isinstance(tags,list):
        raise TypeError("tags必须是字符串列表")

    clean_tags=[]
    for tag in tags:
        if not isinstance(tag, str):
            raise TypeError("标签必须是字符串")
        
        tag=tag.strip()

        if not tag.strip():
            raise ValueError("标签不能为空")
        
        if len(tag)>50:
            raise ValueError("标签长度不能超过50个字符")
        clean_tags.append(tag)
        
    unique_tags=list(dict.fromkeys(clean_tags))

    with user_transaction(settings,user_id) as conn:
        # 检查资料是否存在且属于当前用户
        document=conn.execute(
            """
            SELECT id
            FROM rag.documents
            WHERE user_id=%s
                AND id=%s
                AND deleted_at IS NULL
            """,
            (user_id, document_id)
        ).fetchone()
        if not document:
            raise ValueError("资料不存在、已删除或不属于当前用户")

        # 更新资料的标签列表
        updated=conn.execute(
            """
            UPDATE rag.documents
            SET tags=%s
            WHERE user_id=%s
                AND id=%s
                AND deleted_at IS NULL
            RETURNING id
            """,
            (unique_tags, user_id, document_id)
        ).fetchone()

        if not updated:
            raise RuntimeError("设置标签失败，可能是因为不存在或其他原因")
    return updated[0]


def soft_delete_document(
    settings: Settings,
    user_id: UUID,
    document_id: UUID,
) -> UUID:
    """软删除资料，标记deleted_at，不删除原文文件。"""
    
    with user_transaction(settings, user_id) as conn,conn.cursor(row_factory=dict_row) as cur:
        # 检查资料是否存在且属于当前用户
        document = cur.execute(
            """
            SELECT id,deleted_at
            FROM rag.documents
            WHERE user_id=%s
                AND id=%s
            FOR UPDATE
            """,
            (user_id, document_id)
        ).fetchone()
        if not document:
            raise ValueError("资料不存在、已删除或不属于当前用户")
        if document["deleted_at"] is not None:
            return document["id"]  # 已经软删除，直接返回 ID

        # 标记资料为已删除
        updated = cur.execute(
            """
            UPDATE rag.documents
            SET deleted_at=NOW()
            WHERE user_id=%s
                AND id=%s
                AND deleted_at IS NULL
            RETURNING id
            """,
            (user_id, document_id)
        ).fetchone()

        if not updated:
            raise RuntimeError("软删除资料失败，可能是因为不存在或其他原因")
    return updated["id"]


def list_deleted_documents(
    settings: Settings,
    user_id: UUID,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """列出已软删除的资料，按删除时间倒序排列。"""
    if isinstance(limit,bool) or not isinstance(limit, int):
        raise TypeError("limit必须是整数")
    if isinstance(offset,bool) or not isinstance(offset, int):
        raise TypeError("offset必须是整数")
    
    if not 1 <= limit <= 100:
        raise ValueError("limit必须在1~100之间")
    if offset<0:
        raise ValueError("offset必须大于等于0")

    with user_transaction(settings, user_id) as conn, conn.cursor(row_factory=dict_row) as cur:
        result = cur.execute(
            """
            SELECT
                id,
                title,
                folder_id,
                tags,
                deleted_at,
                updated_at
            FROM rag.documents
            WHERE user_id = %s
                AND deleted_at IS NOT NULL
                AND trash_batch_id IS NULL
            ORDER BY deleted_at DESC, id DESC
            LIMIT %s OFFSET %s
            """,
            (user_id, limit, offset)
        ).fetchall()

        if not result:
            return []

        return [dict(row) for row in result]


def restore_document(
    settings: Settings,
    user_id: UUID,
    document_id: UUID,
) -> UUID:
    """恢复已软删除的资料，将deleted_at置为NULL。"""
    with user_transaction(settings, user_id) as conn, conn.cursor(row_factory=dict_row) as cur:
        lock_folder_tree(conn, user_id)
        # 检查资料是否存在且属于当前用户
        document = cur.execute(
            """
            SELECT id, deleted_at, folder_id, trash_batch_id
            FROM rag.documents
            WHERE user_id=%s
                AND id=%s
            FOR UPDATE
            """,
            (user_id, document_id)
        ).fetchone()
        if not document:
            raise ValueError("资料不存在、未被删除或不属于当前用户")
        if document["deleted_at"] is None:
            return document["id"]  # 已经恢复，直接返回 ID

        if document["trash_batch_id"] is not None:
            raise DocumentRestoreConflictError("请从所属的文件夹回收批次恢复此资料")
        if document["folder_id"] is not None:
            parent = cur.execute(
                "SELECT id FROM rag.folders WHERE user_id = %s AND id = %s AND deleted_at IS NULL",
                (user_id, document["folder_id"]),
            ).fetchone()
            if parent is None:
                raise DocumentRestoreConflictError("请先恢复资料的原文件夹")

        # 恢复资料
        updated = cur.execute(
            """
            UPDATE rag.documents
            SET deleted_at=NULL
            WHERE user_id=%s
                AND id=%s
                AND deleted_at IS NOT NULL
            RETURNING id
            """,
            (user_id, document_id)
        ).fetchone()

        if not updated:
            raise RuntimeError("恢复资料失败，可能是因为不存在或其他原因")
    return updated["id"]


def get_document(
        settings: Settings,
        user_id: UUID,
        document_id: UUID,
)->dict:
    with user_transaction(settings,user_id) as conn,conn.cursor(row_factory=dict_row) as cur:
        document=cur.execute(
            """
            SELECT
                id,
                title,
                folder_id,
                tags,
                source_type,
                latest_version_id,
                active_run_id,
                created_at,
                updated_at
            FROM rag.documents
            WHERE user_id=%s
                AND id=%s
                AND deleted_at IS NULL
            """,
            (user_id, document_id)
        ).fetchone()

        if not document:
            raise ValueError("资料不存在、已删除或不属于当前用户")

        return dict(document)


def list_document_versions(
        settings: Settings,
        user_id: UUID,
        document_id: UUID,
        limit: int = 50,
        offset: int = 0,
)->list[dict]:
    """列出指定资料的所有原文版本，按版本号倒序排列。"""

    if isinstance(limit,bool) or not isinstance(limit, int):
        raise TypeError("limit必须是整数")
    if isinstance(offset,bool) or not isinstance(offset, int):
        raise TypeError("offset必须是整数")
    
    if not 1 <= limit <= 100:
        raise ValueError("limit必须在1~100之间")
    if offset<0:
        raise ValueError("offset必须大于等于0")

    with user_transaction(settings,user_id) as conn,conn.cursor(row_factory=dict_row) as cur:
        # 检查资料是否存在且属于当前用户
        document=cur.execute(
            """
            SELECT id
            FROM rag.documents
            WHERE user_id=%s
                AND id=%s
                AND deleted_at IS NULL
            """,
            (user_id, document_id)
        ).fetchone()
        if not document:
            raise ValueError("资料不存在、已删除或不属于当前用户")

        # 查询指定资料的所有原文版本，按版本号倒序排列
        versions=cur.execute(
            """
            SELECT
                id,
                document_id,
                version_no,
                media_type,
                byte_size,
                raw_sha256,
                captured_at
            FROM rag.document_versions
            WHERE user_id=%s
                AND document_id=%s
            ORDER BY version_no DESC
            LIMIT %s OFFSET %s
            """,
            (user_id, document_id, limit, offset)
        ).fetchall()

        if not versions:
            return []

        return [dict(version) for version in versions]


def main():
    """直接修改下方变量后运行此脚本，即可上传原文。"""
    settings = load_settings()
    file_path = Path("C:/Users/茶鸣拾贰率/Desktop/毛概/复习资料/综合复习手册_完整版.md")
    user_a = UUID("db1e84a8-87c3-4b10-ab50-b56fc99e0a7c")

    # None 表示创建新资料；更新已有资料时，改为 UUID("已有资料的 document_id")。
    # 更新时使用 document_id，而不是 version_id。
    document_id = None
    result = upload_file(settings, user_a, file_path, document_id)
    print(result)

if __name__ == "__main__":
    main()
