from contextlib import contextmanager
from uuid import UUID

import psycopg

from config import Settings


@contextmanager
def auth_connection(settings:Settings):
    """认证阶段：只读查询登录身份"""
    with psycopg.connect(
        settings.auth_database_url,
        connect_timeout=5,
        autocommit=True,
    ) as conn, conn.transaction():
        conn.execute("SET TRANSACTION READ ONLY")
        yield conn

@contextmanager
def user_transaction(settings:Settings,user_id:UUID):
    """业务阶段：在事务中绑定已经认证的用户"""
    user_id = UUID(str(user_id))
    with psycopg.connect(
        settings.app_database_url,
        connect_timeout=5,
        autocommit=True,
    ) as conn, conn.transaction():
        conn.execute(
            "SELECT set_config('app.user_id',%s,true)",
            (str(user_id),)
        )
        yield conn