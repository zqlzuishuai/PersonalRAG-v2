from uuid import UUID, uuid4

from psycopg.rows import dict_row

from config import Settings
from db import lock_folder_tree, user_transaction


class FolderMoveConflictError(ValueError):
    """目标位置会使目录树形成环"""

class FolderRestoreConflictError(ValueError):
    """The folder cannot be restored independently in its current state."""


def create_folder(
        settings: Settings, 
        user_id: UUID, 
        name: str, 
        parent_id=None
        )-> UUID:
    """创建文件夹"""
    name = name.strip()
    if not name:
        raise ValueError("文件夹名称不能为空")

    if not 1<=len(name)<=200:
        raise ValueError("文件夹名称长度必须在1-200之间")

    # 检查父目录是否存在且属于当前用户
    with user_transaction(settings, user_id) as conn:
        lock_folder_tree(conn, user_id)
        if parent_id:
            parent=conn.execute(
                """
                SELECT id 
                FROM rag.folders
                WHERE user_id=%s
                    AND id=%s
                    AND deleted_at IS NULL
                """,
                (user_id, parent_id)
            ).fetchone()
            if not parent:
                raise ValueError("父目录不存在或不属于当前用户")

        # # 检查同级目录下是否已存在同名文件夹
        # existing=conn.execute(
        #     """
        #     SELECT id 
        #     FROM rag.folder
        #     WHERE user_id=%s
        #         AND parent_id=%s
        #         AND name=%s
        #     """,
        #     (str(user_id), str(parent_id) if parent_id else None, name)
        # ).fetchone()
        # if existing:
        #     raise ValueError("同级目录下已存在同名文件夹")

        # 插入新文件夹
        new_folder_id=conn.execute(
            """
            INSERT INTO rag.folders
                (user_id,parent_id,name)
            VALUES (%s,%s,%s)
            RETURNING id
            """,
            (user_id, parent_id if parent_id else None, name)
        ).fetchone()

        if new_folder_id is None:
            raise RuntimeError("创建文件夹失败，可能是因为存在同名文件夹或其他原因")

    return new_folder_id[0]


def list_folders(settings: Settings, user_id: UUID, parent_id: UUID | None=None):
    """列出指定父目录的直接子文件夹"""
    with user_transaction(settings,user_id) as conn:

        if parent_id:
            # 查询指定父目录下的直接子文件夹
            folders=conn.execute(
                """
                SELECT id,name,parent_id
                FROM rag.folders
                WHERE user_id=%s
                    AND parent_id=%s
                    AND deleted_at IS NULL
                ORDER BY name
                """,
                (user_id,parent_id)
            ).fetchall()

        else:
            folders=conn.execute(
                """
                SELECT id,name,parent_id
                FROM rag.folders
                WHERE user_id=%s
                    AND parent_id IS NULL
                    AND deleted_at IS NULL
                ORDER BY name
                """,
                (user_id,)
            ).fetchall()

        if not folders:
            return []

        returning=[
            {
                "id": folder[0],
                "name": folder[1],
                "parent_id": folder[2] if folder[2] else None
            } for folder in folders
        ]

    return returning


def rename_folder(settings: Settings, user_id: UUID,folder_id: UUID, new_name: str)->UUID:
    new_name = new_name.strip()
    if not new_name:
        raise ValueError("新文件夹名称不能为空")
    if not 1<=len(new_name)<=200:
        raise ValueError("新文件夹名称长度必须在1-200之间")
    with user_transaction(settings,user_id) as conn:
        lock_folder_tree(conn, user_id)
        # 检查文件夹是否存在且属于当前用户
        folder=conn.execute(
            """
            SELECT id,parent_id
            FROM rag.folders
            WHERE user_id=%s
                AND id=%s
                AND deleted_at IS NULL
            """,
            (user_id, folder_id)
        ).fetchone()
        if not folder:
            raise ValueError("文件夹不存在或不属于当前用户")

        # 更新文件夹名称
        updated=conn.execute(
            """
            UPDATE rag.folders
            SET name=%s
            WHERE user_id=%s
                AND id=%s
                AND deleted_at IS NULL
            RETURNING id
            """,
            (new_name, user_id, folder_id)
        ).fetchone()

        if not updated:
            raise RuntimeError("重命名文件夹失败，可能是因为不存在或其他原因")
    return updated[0]


def move_folder(
        settings: Settings,
        user_id: UUID,
        folder_id: UUID,
        new_parent_id: UUID | None
)-> UUID:
    with user_transaction(settings,user_id) as conn,conn.cursor(row_factory=dict_row) as cur:
        lock_folder_tree(conn, user_id)

        source = cur.execute(
            """
            SELECT id
            FROM rag.folders
            WHERE user_id = %(user_id)s
                AND id = %(folder_id)s
                AND deleted_at IS NULL
            """,
            {
                "user_id": user_id,
                "folder_id": folder_id
            }
        ).fetchone()
        if not source:
            raise ValueError("文件夹不存在或不属于当前用户")

        if new_parent_id is not None:
            # 检查是否可以移动到新父目录
            target=cur.execute(
                """
                WITH RECURSIVE ancestors(id,parent_id) AS (
                    SELECT id,parent_id
                    FROM rag.folders
                    WHERE user_id = %(user_id)s
                        AND id = %(parent_id)s
                        AND deleted_at IS NULL
                    
                    UNION

                    SELECT f.id,f.parent_id
                    FROM rag.folders AS f
                    JOIN ancestors AS a ON f.id = a.parent_id
                    WHERE f.user_id = %(user_id)s AND f.deleted_at IS NULL
                )

                SELECT
                    EXISTS (SELECT 1 FROM ancestors) AS target_exists,
                    EXISTS (SELECT 1 FROM ancestors WHERE id = %(folder_id)s) AS contains_source
                """,
                {
                    "user_id":user_id,
                    "parent_id":new_parent_id,
                    "folder_id":folder_id
                },
            ).fetchone()
            if not target:
                raise ValueError("新父目录不存在或不属于当前用户")
            target_exists=target["target_exists"]
            contains_source=target["contains_source"]
            if not target_exists:
                raise ValueError("目标文件夹不存在或不可访问")
            if contains_source:
                raise FolderMoveConflictError("不能将文件夹移到自身或其子目录")
        moved=cur.execute(
            """
            UPDATE rag.folders
            SET parent_id = %(parent_id)s
            WHERE user_id = %(user_id)s
                AND id = %(folder_id)s
                AND deleted_at IS NULL
            RETURNING id
            """,
            {
                "parent_id": new_parent_id,
                "user_id": user_id,
                "folder_id": folder_id
            }
        ).fetchone()
        if moved is None:
            raise RuntimeError("移动文件夹失败，可能是因为不存在或其他原因")

    return moved["id"]



def soft_delete_folder_tree(settings: Settings, user_id: UUID, folder_id: UUID) -> UUID:
    """将活动子树及其中的活动文档作为一个批次移入回收站。"""
    with user_transaction(settings, user_id) as conn:
        lock_folder_tree(conn, user_id)
        row = conn.execute(
            "SELECT deleted_at FROM rag.folders WHERE user_id = %s AND id = %s",
            (user_id, folder_id),
        ).fetchone()
        if row is None:
            raise ValueError("文件夹不存在或不属于当前用户")
        if row[0] is not None:
            return folder_id

        conn.execute(
            """
            WITH RECURSIVE subtree(id) AS (
                SELECT id FROM rag.folders
                WHERE user_id = %(user_id)s AND id = %(folder_id)s AND deleted_at IS NULL
                UNION
                SELECT f.id FROM rag.folders AS f
                JOIN subtree AS s ON f.parent_id = s.id
                WHERE f.user_id = %(user_id)s AND f.deleted_at IS NULL
            ), trashed_folders AS (
                UPDATE rag.folders
                SET deleted_at = statement_timestamp(), trash_batch_id = %(batch_id)s
                WHERE user_id = %(user_id)s AND id IN (SELECT id FROM subtree)
                RETURNING id
            )
            UPDATE rag.documents
            SET deleted_at = statement_timestamp(), trash_batch_id = %(batch_id)s
            WHERE user_id = %(user_id)s AND deleted_at IS NULL
                AND folder_id IN (SELECT id FROM trashed_folders)
            """,
            {"user_id": user_id, "folder_id": folder_id, "batch_id": uuid4()},
        )
    return folder_id


def list_deleted_folders(
    settings: Settings, user_id: UUID, limit: int = 50, offset: int = 0,
) -> list[dict]:
    """List only the root of each folder trash batch."""
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("limit 必须在 1 到 100 之间")
    if type(offset) is not int or offset < 0:
        raise ValueError("offset 必须是非负整数")
    with user_transaction(settings, user_id) as conn, conn.cursor(row_factory=dict_row) as cur:
        return cur.execute(
            """
            SELECT f.id, f.name, f.parent_id, f.deleted_at
            FROM rag.folders AS f
            WHERE f.user_id = %s AND f.deleted_at IS NOT NULL
                AND NOT EXISTS (
                    SELECT 1 FROM rag.folders AS parent
                    WHERE parent.user_id = f.user_id AND parent.id = f.parent_id
                        AND parent.trash_batch_id = f.trash_batch_id
                )
            ORDER BY f.deleted_at DESC, f.id DESC
            LIMIT %s OFFSET %s
            """,
            (user_id, limit, offset),
        ).fetchall()

def restore_folder_tree(settings: Settings, user_id: UUID, folder_id: UUID) -> dict:
    """在原始父文件夹处于活动状态后，恢复一个文件夹回收批次。"""
    with user_transaction(settings, user_id) as conn, conn.cursor(row_factory=dict_row) as cur:
        lock_folder_tree(conn, user_id)
        trash_batch = cur.execute(
            """
            SELECT parent_id, trash_batch_id, deleted_at
            FROM rag.folders
            WHERE user_id = %s AND id = %s
            """,
            (user_id, folder_id),
        ).fetchone()
        if trash_batch is None:
            raise ValueError("指定的文件夹不存在或不属于当前用户")
        if trash_batch["deleted_at"] is None:
            return {"restored_folders": [], "restored_documents": []}

        parent_id = trash_batch["parent_id"]
        if parent_id is not None:
            parent = cur.execute(
                """
                SELECT name, trash_batch_id, deleted_at
                FROM rag.folders
                WHERE user_id = %s AND id = %s
                """,
                (user_id, parent_id),
            ).fetchone()
            if parent is None:
                raise FolderRestoreConflictError("原父目录不可用，无法恢复文件夹")
            if parent["trash_batch_id"] == trash_batch["trash_batch_id"]:
                raise FolderRestoreConflictError("请从回收站恢复该批次的根目录")
            if parent["deleted_at"] is not None:
                raise FolderRestoreConflictError(f"请先恢复父目录「{parent['name']}」")

        # 恢复回收站批次中的文件夹和文档
        restored_folders=cur.execute(
            """
            UPDATE rag.folders
            SET deleted_at = NULL, trash_batch_id = NULL
            WHERE user_id = %(user_id)s
                AND trash_batch_id = %(trash_batch)s
                AND deleted_at IS NOT NULL
            returning id
            """,
            {
                "user_id": user_id,
                "trash_batch": trash_batch["trash_batch_id"]
            }
        ).fetchall()

        restored_documents=cur.execute(
            """
            UPDATE rag.documents
            SET deleted_at = NULL, trash_batch_id = NULL
            WHERE user_id = %(user_id)s
                AND trash_batch_id = %(trash_batch)s
                AND deleted_at IS NOT NULL
            returning id
            """,
            {
                "user_id": user_id,
                "trash_batch": trash_batch["trash_batch_id"]
            }
        ).fetchall()

        if restored_folders is None or restored_documents is None:
            raise RuntimeError("恢复回收站批次失败，可能是因为不存在或其他原因")
        return {
            "restored_folders": [str(folder["id"]) for folder in restored_folders],
            "restored_documents": [str(doc["id"]) for doc in restored_documents]
        }

if __name__ == "__main__":
    from config import load_settings
    settings=load_settings()
    user_id=UUID("00000000-0000-0000-0000-000000000001")
    parent_id=None
    name="测试文件夹"
    new_folder_id=create_folder(settings,user_id,name,parent_id)
    print(f"新建文件夹ID: {new_folder_id}")

    folders=list_folders(settings,user_id,parent_id)
    print("当前父目录下的文件夹列表:")
    for folder in folders:
        print(folder)