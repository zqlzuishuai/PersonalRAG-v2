import re
from typing import Any
from uuid import UUID

from psycopg.types.json import Jsonb

from answering import AISearchResult, validate_citations
from config import Settings
from conversations import save_user_message_with_conn
from db import user_transaction


def start_answer_run(
        settings:Settings,
        user_id:UUID,
        conversation_id:UUID,
        question_message_id:UUID,
        client_request_id:UUID
        ) -> UUID:

    """创建一个回答运行记录，返回回答运行记录的 UUID"""
    with user_transaction(settings,user_id) as conn:
        # 确认会话属于用户且未删除
        row=conn.execute(
            """
            SELECT 1
            FROM rag.conversations
            WHERE id=%s
                AND user_id=%s
                AND deleted_at IS NULL
            FOR UPDATE
            """,
            (conversation_id,user_id),
        ).fetchone()
        if row is None:
            raise ValueError("会话不存在、已删除或不属于当前用户")


        # 确认问题消息属于该会话，且是 role='user'、status='completed'
        row=conn.execute(
            """
            SELECT 1
            FROM rag.messages
            WHERE user_id=%s
                AND conversation_id=%s
                AND id=%s
                AND role='user'
                AND status='completed'
            FOR UPDATE
            """,
            (user_id, conversation_id, question_message_id)
        ).fetchone()
        if row is None:
            raise ValueError("问题消息不存在、不属于该会话或状态不正确")

        # 检查该请求者是否已有任务
        row=conn.execute(
            """
            SELECT id,conversation_id,question_message_id  
            FROM rag.answer_runs
            WHERE user_id = %s 
                AND client_request_id = %s
            """,
            (user_id, client_request_id)
        ).fetchone()
        if row is not None:
            if row[1] == conversation_id and row[2] == question_message_id:
                # 如果已有任务且与当前会话和问题消息匹配，则直接返回已有任务的 run_id
                return row[0]
            else:
                # 如果已有任务但与当前会话或问题消息不匹配，则抛出异常
                raise ValueError("已有任务正在运行，且与当前会话或问题消息不匹配")
        else:
                
            # 插入开始回答记录
            answer_run=conn.execute(
                """
                INSERT INTO rag.answer_runs (
                    user_id,
                    conversation_id,
                    question_message_id,
                    client_request_id,
                    status,
                    retrieval_config,
                    model_config,
                    retrieval_query,
                    started_at)
                VALUES (
                    %s, %s, %s, %s, 'running', '{}', '{}', '', now()
                )
                RETURNING id
                """,
                (user_id, conversation_id, question_message_id, client_request_id)
            ).fetchone()

            if answer_run is None:
                raise RuntimeError("创建回答运行记录失败")
        return answer_run[0]


def start_answer_run_with_conn(
        conn,
        settings:Settings,
        user_id:UUID,
        conversation_id:UUID,
        question_message_id:UUID,
        client_request_id:UUID
        ) -> UUID:

    """创建一个回答运行记录，返回回答运行记录的 UUID"""
    # 确认会话属于用户且未删除
    row=conn.execute(
        """
        SELECT 1
        FROM rag.conversations
        WHERE id=%s
            AND user_id=%s
            AND deleted_at IS NULL
        FOR UPDATE
        """,
        (conversation_id,user_id),
    ).fetchone()
    if row is None:
        raise ValueError("会话不存在、已删除或不属于当前用户")


    # 确认问题消息属于该会话，且是 role='user'、status='completed'
    row=conn.execute(
        """
        SELECT 1
        FROM rag.messages
        WHERE user_id=%s
            AND conversation_id=%s
            AND id=%s
            AND role='user'
            AND status='completed'
        FOR UPDATE
        """,
        (user_id, conversation_id, question_message_id)
    ).fetchone()
    if row is None:
        raise ValueError("问题消息不存在、不属于该会话或状态不正确")

    # 检查该请求者是否已有任务
    row=conn.execute(
        """
        SELECT id,conversation_id,question_message_id  
        FROM rag.answer_runs
        WHERE user_id = %s 
            AND client_request_id = %s
        """,
        (user_id, client_request_id)
    ).fetchone()
    if row is not None:
        if row[1] == conversation_id and row[2] == question_message_id:
            # 如果已有任务且与当前会话和问题消息匹配，则直接返回已有任务的 run_id
            return row[0]
        else:
            # 如果已有任务但与当前会话或问题消息不匹配，则抛出异常
            raise ValueError("已有任务正在运行，且与当前会话或问题消息不匹配")
    else:
            
        # 插入开始回答记录
        answer_run=conn.execute(
            """
            INSERT INTO rag.answer_runs (
                user_id,
                conversation_id,
                question_message_id,
                client_request_id,
                status,
                retrieval_config,
                model_config,
                retrieval_query,
                started_at)
            VALUES (
                %s, %s, %s, %s, 'running', '{}', '{}', '', now()
            )
            RETURNING id
            """,
            (user_id, conversation_id, question_message_id, client_request_id)
        ).fetchone()

        if answer_run is None:
            raise RuntimeError("创建回答运行记录失败")
    return answer_run[0]

    

def fail_answer_run(
        settings: Settings,
        user_id: UUID,
        run_id: UUID,
        error_code: int,
        error_summary: str
        )->UUID:
    """将失败的任务标记为失败状态"""
    with user_transaction(settings,user_id) as conn:
        row=conn.execute(
            """
            UPDATE rag.answer_runs
            SET status = 'failed' ,
                finished_at = now() ,
                error_code = %s ,
                error_summary = %s
            WHERE id = %s 
                AND user_id = %s
                AND status = 'running'
            RETURNING id
            """,
            (error_code, error_summary, run_id, user_id)
        ).fetchone()
        if row is None:
            raise ValueError("回答运行记录不存在或不属于当前用户,无法标记为失败")
        return row[0]


def finish_answer_run(
        settings: Settings,
        user_id: UUID,
        conversation_id: UUID,
        run_id: UUID,
        result: AISearchResult
        ) -> UUID:

    ######## 1.内容检查
    if result.ai_message.text.strip() == "":
        raise ValueError("AIMessage 内容不能为空")
    content = result.ai_message.content
    validate_citations(content, len(result.sources))


    # 断言content是str类型,提取实际引用编号并去重
    assert isinstance(content,str)

    citation_numbers = sorted({
        int(number)
        for number in re.findall(r"\[([0-9]+)\]", content)
    })

    # for number in citation_numbers:
    #     source = result.sources[number - 1]

    with user_transaction(settings,user_id) as conn:
    ######## 2.锁会话
        # 确认会话属于用户且未删除
        row=conn.execute(
            """
            SELECT 1
            FROM rag.conversations
            WHERE id=%s
                AND user_id=%s
                AND deleted_at IS NULL
            FOR UPDATE
            """,
            (conversation_id,user_id),
        ).fetchone()
        if row is None:
            raise ValueError("会话不存在、已删除或不属于当前用户")
        
        # 确认任务属于该会话
        row=conn.execute(
            """
            SELECT status,answer_message_id
            FROM rag.answer_runs
            WHERE id=%s 
                AND conversation_id=%s 
                AND user_id=%s 
            FOR UPDATE
            """,
            (run_id, conversation_id, user_id)
        ).fetchone()
        ####### 保存助手消息
        # 排除异常情况
        if row is None:
            raise ValueError("任务不存在、不属于该会话")
        status=row[0]
        answer_message_id=row[1]

        if status == "succeeded":
            return answer_message_id
        if status != "running":
            raise ValueError("answer_run状态错误，拒绝保存")
        ## 进入保存逻辑
        # 查next_message_sequence
        next_message_sequence=conn.execute(
            """
            UPDATE rag.conversations
            SET next_message_sequence = next_message_sequence + 1
            WHERE id = %s 
            RETURNING next_message_sequence - 1
            """,
            (conversation_id,)
        ).fetchone()
        if next_message_sequence is None:
            raise ValueError("会话不存在或不属于当前用户")
        next_message_sequence = next_message_sequence[0]

        # 插入助手消息到messages表
        message_row=conn.execute(
            """
            INSERT INTO rag.messages (
                user_id,
                conversation_id,
                sequence,
                role,
                content,
                status,
                completed_at
            ) 
            VALUES (
                %s, %s, %s, 'assistant', %s, 'completed', now()
            )
            RETURNING id
            """,
            (user_id, conversation_id, next_message_sequence, content)
        ).fetchone()
        if message_row is None:
            raise RuntimeError("保存助手消息失败")
        message_id = message_row[0]

        # 保存实际引用到引用表
        for number in citation_numbers:
            source = result.sources[number - 1] # RerankChunk 对象
            row=conn.execute(
                """
                INSERT INTO rag.citations (
                    user_id,
                    answer_message_id,
                    citation_no,
                    document_id,
                    version_id,
                    chunk_id,
                    locator,
                    quote
                    ) 
                VALUES ( %s, %s, %s, %s, %s, %s, %s, %s ) 
                RETURNING id
                """,
                (
                    user_id,
                    message_id,
                    number,
                    source.chunk.document_id,
                    source.chunk.version_id,
                    source.chunk.chunk_id,
                    Jsonb(source.chunk.locator),
                    source.chunk.content
                )
            ).fetchone()
            if row is None:
                raise RuntimeError(f"保存引用 {number} 失败")

        # 更新任务状态为成功
        snap_shot=[{
            "citation_no": number,
            "chunk_id": str(result.sources[number - 1].chunk.chunk_id),
            "version_id": str(result.sources[number - 1].chunk.version_id),
            "rerank_score": result.sources[number - 1].rerank_score
        } for number, source in enumerate(result.sources, start=1)]
        row=conn.execute(
            """
            UPDATE rag.answer_runs 
            SET status = 'succeeded' ,
                answer_message_id = %s ,
                finished_at = now() ,
                context_snapshot = %s::jsonb,
                usage = %s::jsonb,
                updated_at = now()
            WHERE id = %s
            RETURNING id,answer_message_id
            """,
            (
                message_id,
                Jsonb(snap_shot),
                Jsonb(result.ai_message.usage_metadata or {}),
                run_id
            )
        ).fetchone()
        if row is None:
            raise RuntimeError("更新任务状态失败")
        answer_message_id = row[1]
    return message_id
        
def perpare_answer_run(
        settings: Settings,
        user_id: UUID,
        conversation_id: UUID,
        query: str,
        client_request_id: UUID
        ) -> dict[str,Any]:
    """准备回答运行记录，返回一个包含 run_id、question_message_id、response_message_id、status、created 的字典"""
    # 1.检测问题非空
    if isinstance(query,str) and query.strip() == "":
        raise ValueError("query不能为空")

    with user_transaction(settings,user_id) as conn:
    # 2.锁定会话
        row=conn.execute(
            """
            SELECT 1
            FROM rag.conversations
            WHERE id=%s
                AND user_id=%s
                AND deleted_at IS NULL
            FOR UPDATE
            """,
            (conversation_id,user_id),
        ).fetchone()
        if row is None:
            raise ValueError("会话不存在、已删除或不属于当前用户")

    # 3.查询是否已有运行记录
        row=conn.execute(
            """
            SELECT 
                m.content = %s , 
                a.id , 
                a.question_message_id , 
                a.answer_message_id ,
                a.status
            FROM rag.answer_runs AS a
            JOIN rag.messages AS m 
                ON a.question_message_id = m.id
            WHERE a.user_id = %s 
                AND a.client_request_id = %s
                AND a.conversation_id = %s
            """,
            (query, user_id, client_request_id, conversation_id)
        ).fetchone()
        if row and row[0]:
            # 如果任务相同，返回已有任务
            returning={
                "run_id":row[1],
                "question_message_id":row[2],
                "answer_message_id":row[3],
                "status":row[4],
                "created":False
            }
            return returning
        elif row and not row[0]:
            # 如果任务不同，抛出异常
            raise ValueError("同一个请求编号被用于不同问题")

    # 4.已确认任务是新任务，检查会话是否有running任务
        row=conn.execute(
            """
            SELECT 1
            FROM rag.answer_runs
            WHERE user_id = %s 
                AND conversation_id = %s
                AND status = 'running'
            """,
            (user_id, conversation_id)
        ).fetchone()
        if row:
            raise ValueError("当前会话已有正在运行的任务，请等待其完成或取消")
    # 5.已确认当前会话没有运行中任务，创建任务
        question_message_id=save_user_message_with_conn(conn,settings,user_id,conversation_id,query)
        run_id=start_answer_run_with_conn(conn,settings,user_id,conversation_id,question_message_id=question_message_id,client_request_id=client_request_id)
        returning={
            "run_id":run_id,
            "question_message_id":question_message_id,
            "answer_message_id":None,
            "status":"running",
            "created":True
        }
        return returning



def main():
    from config import load_settings

    settings=load_settings()
    user_id=UUID("db1e84a8-87c3-4b10-ab50-b56fc99e0a7c")
    question_message_id=UUID("68d365d0-d0da-4c49-b08f-10c69b7c3c57")
    client_request_id=UUID("f1e2d3c4-b5a6-7890-1234-56789abcdef7")
    conversation_id=UUID("1c1dcd20-cc01-40ab-8aaf-8ed4610b60ca")


    run_id=start_answer_run(settings,user_id,conversation_id,question_message_id,client_request_id)
    if run_id:
        print(f"创建回答运行记录成功, run_id={run_id}")
    else:
        print("创建回答运行记录失败")



    # run_id=UUID("fe2e373e-243d-4a71-ba9f-ac762f6ea83d")
    failed_run_id=fail_answer_run(settings,user_id,run_id,-1,"测试失败")
    if failed_run_id:
        print(f"标记回答运行记录失败成功, run_id={failed_run_id}")
    else:
        print(f"标记回答运行记录失败失败, run_id={run_id}")
if __name__ == "__main__":
    main()