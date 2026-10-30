from uuid import UUID

from config import Settings
from db import user_transaction


def create_folder(settings: Settings, user_id: UUID, name: str, parent_id=None):
    """创建文件夹"""
    name = name.strip()
    if not name:
        raise ValueError("文件夹名称不能为空")

    if not 1<=len(name)<=200:
        raise ValueError("文件夹名称长度必须在1-200之间")

    # 检查父目录是否存在且属于当前用户
    with user_transaction(settings, user_id) as conn:
        if parent_id:
            parent=conn.execute(
                """
                SELECT id 
                FROM rag.folders
                WHERE user_id=%s
                    AND id=%s
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
        # 检查文件夹是否存在且属于当前用户
        folder=conn.execute(
            """
            SELECT id,parent_id
            FROM rag.folders
            WHERE user_id=%s
                AND id=%s
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
            RETURNING id
            """,
            (new_name, user_id, folder_id)
        ).fetchone()

        if not updated:
            raise RuntimeError("重命名文件夹失败，可能是因为不存在或其他原因")
    return updated[0]

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