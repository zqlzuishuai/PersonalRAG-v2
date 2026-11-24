import hashlib
from uuid import UUID

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from psycopg.rows import dict_row

from config import Settings
from db import auth_connection


def authenticate_token(settings: Settings,token: str) -> UUID:
    """验证原始 token 返回他所属的用户ID"""
    if not isinstance(token, str) or not token.strip():
        raise PermissionError("无效的访问令牌")

    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()

    with auth_connection(settings) as conn:
        row = conn.execute(
            """
            SELECT id
            FROM rag.users
            WHERE mcp_token_hash = %s
                AND status = 'active'
            """,
            (token_hash,)
        ).fetchone()

    if row is None:
        raise PermissionError("无效的访问令牌")
    return UUID(str(row[0]))

def user_can_write_mcp(settings: Settings, user_id: UUID) -> bool:
    """Check MCP write permission using the read-only auth role."""
    with auth_connection(settings) as conn:
        row = conn.execute(
            """
            SELECT mcp_write_enabled
            FROM rag.users
            WHERE id = %s AND status = 'active'
            """,
            (user_id,),
        ).fetchone()
    return row is not None and row[0] is True


def authenticate_password(settings: Settings, login_name: str, password: str) -> UUID:
    """验证登录名和密码 返回他所属的用户ID"""
    if not isinstance(login_name, str) or not login_name.strip():
        raise PermissionError("无效的登录名")

    normalized_login_name = login_name.strip().lower()
    
    if not isinstance(password, str) or not password.strip():
        raise PermissionError("无效的密码")

    with auth_connection(settings) as conn,conn.cursor(row_factory=dict_row) as cur:
        user=cur.execute(
            """
            SELECT id,password_hash
            FROM rag.users
            WHERE login_name = %s
                AND status = 'active'
            """ ,
            (normalized_login_name,)
        ).fetchone()

        if user is None:
            raise PermissionError("用户名或密码错误")

        # 验证密码
        try:
            ph = PasswordHasher()
            ph.verify(user["password_hash"], password)
        except (VerifyMismatchError, InvalidHashError, VerificationError):
            raise PermissionError("用户名或密码错误")

    return user["id"]

def resolve_cloudflare_user_id(
        settings: Settings,
        issuer: str,
        subject: str,
)->UUID|None:
    with auth_connection(settings) as conn:
        row=conn.execute(
            """
            SELECT u.id
            FROM rag.mcp_access_identities AS identity
            JOIN rag.users AS u ON u.id = identity.user_id
            WHERE identity.issuer = %s
                AND identity.subject = %s
                AND u.status = 'active'    
            """,
            (issuer,subject)
        ).fetchone()
    return row[0] if row else None
    
