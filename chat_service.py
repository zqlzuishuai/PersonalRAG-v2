from uuid import UUID

from langchain.chat_models import BaseChatModel
from psycopg.rows import dict_row

from answer_runs import (
    fail_answer_run,
    finish_answer_run,
)
from answer_runs import (
    perpare_answer_run as prepare_answer_run,
)
from answering import generate_system_message
from config import Settings
from db import user_transaction


def get_answer_run_result(
        settings: Settings,
        user_id: UUID,
        run_id: UUID,
        )-> dict:
    """获取指定用户的回答运行结果及其引用信息。"""
    with user_transaction(settings, user_id) as conn, conn.cursor(row_factory=dict_row) as cur:
        row=cur.execute(
            """
            SELECT 
                a.id AS run_id,
                a.status,
                a.question_message_id,
                a.answer_message_id,
                m.content AS answer,
                a.error_code,
                a.error_summary
            FROM rag.answer_runs AS a
            JOIN rag.conversations AS c
                ON c.id = a.conversation_id
                    AND c.user_id = a.user_id
            LEFT JOIN rag.messages AS m
                ON m.id = a.answer_message_id
                    AND m.user_id = a.user_id
            WHERE a.id = %s
                AND a.user_id = %s
                AND c.deleted_at is NULL
            """,
            (run_id,user_id)
        ).fetchone()

        if row is None:
            raise ValueError(f"回答运行不存在或不属于用户 {user_id}: {run_id}")
        # assert isinstance(row,dict)
        row["citations"] = []

        if row["status"] == "succeeded":
            row["citations"] = cur.execute(
                """
                SELECT 
                    citation_no,
                    document_id,
                    version_id,
                    chunk_id,
                    locator,
                    quote,
                    source_status
                FROM rag.citations
                WHERE answer_message_id = %s
                    AND user_id = %s
                ORDER BY citation_no
                """,
                (row["answer_message_id"],user_id)
            ).fetchall()

    return row




def ask_question(
        settings: Settings, 
        user_id: UUID,
        conversation_id: UUID, 
        query: str, 
        client_request_id: UUID,
        chat_model: BaseChatModel
        ):
    """111"""
    # 网页端请求的 user_id 是 str，转换为 UUID 以便在数据库中使用。
    user_id = UUID(str(user_id))
    conversation_id = UUID(str(conversation_id))
    client_request_id = UUID(str(client_request_id))

    if not isinstance(query, str):
        raise TypeError("query 必须是字符串")
    if not query.strip():
        raise ValueError("query 不能为空")

    prepared = prepare_answer_run(
        settings,
        user_id,
        conversation_id,
        query,
        client_request_id,
    )
    run_id = prepared["run_id"]

    # 重复请求，读已有请求
    if not prepared["created"]:
        return get_answer_run_result(settings, user_id, run_id)

    try:
        result = generate_system_message(
            settings,
            user_id,
            chat_model,
            query,
        )
        finish_answer_run(
            settings,
            user_id,
            conversation_id,
            run_id,
            result,
        )

    except Exception as original_error:
        try:
            stored = get_answer_run_result(settings, user_id, run_id)

            if stored["status"] == "succeeded":
                # 说明原始异常发生在 finish_answer_run 内部，已经成功写回数据库。
                return stored

            if stored["status"] == "running":
                # 说明原始异常发生在 generate_system_message 内部，尚未写回数据库。
                fail_answer_run(
                    settings,
                    user_id,
                    run_id,
                    type(original_error).__name__, # type: ignore
                    "问答执行失败，请检查服务端异常",
                )

        except Exception as recovery_error:
            original_error.add_note(
                "核对火记录任务状态失败："
                + type(recovery_error).__name__
            )

        raise

    return get_answer_run_result(settings, user_id, run_id)