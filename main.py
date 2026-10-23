"""手动验证数据库的跨用户目录约束，结束后清理本次测试数据。"""
from uuid import UUID, uuid4

from psycopg.errors import ForeignKeyViolation

from config import Settings, load_settings
from db import user_transaction


def check_user_isolation(settings: Settings, user_a: UUID, user_b: UUID) -> None:
    """验证用户 B 无法将资料关联到用户 A 的目录。

    这是连接真实数据库的手动检查，会短暂创建测试记录。
    正常返回表示预期的外键拒绝发生且清理完成；其他失败继续抛出。
    该检查只覆盖跨用户目录关联，不代表全部 RLS 行为均已验证。
    """
    user_a, user_b = UUID(str(user_a)), UUID(str(user_b))
    if user_a == user_b:
        raise ValueError("隔离测试需要两个不同用户")
    # 先确认两个用户存在，避免把“用户不存在”的外键错误误认为隔离有效。
    for user_id in (user_a, user_b):
        with user_transaction(settings, user_id) as conn:
            if conn.execute("SELECT id FROM rag.users WHERE id = %s", (user_id,)).fetchone() is None:
                raise ValueError(f"测试用户不存在或不可见：{user_id}")

    # 每次使用随机 ID，避免重复运行冲突，也便于只清理本次产生的记录。
    folder_id, document_id = uuid4(), uuid4()
    with user_transaction(settings, user_a) as conn:
        conn.execute("INSERT INTO rag.folders (id,user_id,name) VALUES (%s,%s,%s)",
                     (folder_id, user_a, f"isolation-check-{folder_id}"))
    # A 的目录先提交，使 B 的独立事务能够进行真实的跨用户关联尝试。
    try:
        try:
            with user_transaction(settings, user_b) as conn:
                conn.execute(
                    "INSERT INTO rag.documents (id,user_id,folder_id,title,source_type,source_key) "
                    "VALUES (%s,%s,%s,%s,%s,%s)",
                    (document_id, user_b, folder_id, "isolation check", "file", f"test/{document_id}"),
                )
        # 只接受预期的外键拒绝；连接失败、权限错误等不能算验证通过。
        except ForeignKeyViolation:
            pass
        else:
            # else 仅在事务没有异常时执行；此断言不能被上面的 except 捕获。
            raise AssertionError("隔离失败：用户 B 成功关联用户 A 的目录")
    finally:
        # 仅清理本次随机 ID 对应的测试记录；异常成功时先删子记录。
        with user_transaction(settings, user_b) as conn:
            conn.execute("DELETE FROM rag.documents WHERE id = %s", (document_id,))
        with user_transaction(settings, user_a) as conn:
            conn.execute("DELETE FROM rag.folders WHERE id = %s", (folder_id,))


def main():
    """使用当前学习环境的两个测试用户执行检查；需要 .env 数据库配置。"""
    check_user_isolation(
        load_settings(),
        UUID("db1e84a8-87c3-4b10-ab50-b56fc99e0a7c"),
        UUID("8c02d060-65c3-43a2-be44-1a811821a9ef"),
    )
    print("跨用户目录关联被数据库拒绝，本次测试记录已清理")


if __name__ == "__main__":
    main()
