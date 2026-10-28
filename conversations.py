from uuid import UUID

# from answering import create_chat_model
from config import Settings
from db import user_transaction


def create_conversation(settings: Settings, user_id: UUID, title:str)-> UUID:
    """创建一个对话并返回对话 UUID"""
    title = title.strip() or "新对话"
    with user_transaction(settings, user_id) as conn:
        row=conn.execute(
            "insert into rag.conversations " \
            "(user_id,title) " \
            "values(%s,%s) "
            "returning id",
            ( user_id, title)
        ).fetchone()
        if row is None:
            raise RuntimeError("创建对话失败")
    return row[0]

def save_user_message(settings: Settings, user_id: UUID, conversation_id: UUID, content:str)-> UUID:
    """保存用户消息，成功时返回消息id"""
    if not content.strip():
        raise ValueError("消息内容不能为空")

    with user_transaction(settings,user_id) as conn:
        conversation_row=conn.execute(
            "update rag.conversations " \
            "set next_message_sequence = next_message_sequence + 1 " \
            "where id = %s " \
            "and user_id = %s " \
            "and deleted_at is null " \
            "returning next_message_sequence - 1",
            (conversation_id,user_id),
        ).fetchone()

        if conversation_row is None:
            raise ValueError("会话不存在、已删除或不属于当前用户")

        sequence = conversation_row[0]

        message_row=conn.execute(
            "insert into rag.messages " \
            "(user_id,conversation_id,sequence,role,content,status,completed_at) " \
            "values(%s,%s,%s,'user',%s,'completed',now()) " \
            "returning id",
            (user_id,conversation_id,sequence,content),
        ).fetchone()

        if message_row is None:
            raise RuntimeError("保存消息失败")

    return message_row[0]

def save_user_message_with_conn(conn ,settings: Settings, user_id: UUID, conversation_id: UUID, content:str)-> UUID:
    """保存用户消息，成功时返回消息id"""
    if not content.strip():
        raise ValueError("消息内容不能为空")

    conversation_row=conn.execute(
        "update rag.conversations " \
        "set next_message_sequence = next_message_sequence + 1 " \
        "where id = %s " \
        "and user_id = %s " \
        "and deleted_at is null " \
        "returning next_message_sequence - 1",
        (conversation_id,user_id),
    ).fetchone()

    if conversation_row is None:
        raise ValueError("会话不存在、已删除或不属于当前用户")

    sequence = conversation_row[0]

    message_row=conn.execute(
        "insert into rag.messages " \
        "(user_id,conversation_id,sequence,role,content,status,completed_at) " \
        "values(%s,%s,%s,'user',%s,'completed',now()) " \
        "returning id",
        (user_id,conversation_id,sequence,content),
    ).fetchone()

    if message_row is None:
        raise RuntimeError("保存消息失败")

    return message_row[0]


if __name__ == "__main__":
    from config import load_settings

    settings = load_settings()
    user_id = UUID("db1e84a8-87c3-4b10-ab50-b56fc99e0a7c")

    conversation_id = create_conversation(
        settings,
        user_id,
        "我的第一次问答",
    )
    print("会话创建成功：", conversation_id)

    first_id = save_user_message(
    settings, user_id, conversation_id, "你好，这是第一条消息"
    )

    second_id = save_user_message(
        settings, user_id, conversation_id, "这是第二条消息"
    )

    print("第一条消息 ID：", first_id)
    print("第二条消息 ID：", second_id)