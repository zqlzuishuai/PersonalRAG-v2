import hashlib
from uuid import UUID

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

def main():
    import secrets

    from config import load_settings
    settings = load_settings()


    # token = secrets.token_urlsafe(32)
    # token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    # print(f"Token: {token}")
    # print(f"Token Hash: {token_hash}")


    token=settings.auth_token
    uesr_id = authenticate_token(settings, token)
    print(f"User ID: {uesr_id}")
if __name__ == "__main__":
    main()