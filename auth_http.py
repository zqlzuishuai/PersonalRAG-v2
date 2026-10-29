import asyncio
from contextvars import ContextVar
from uuid import UUID

from psycopg import Error as PsycopgError
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from auth import authenticate_token
from config import Settings

current_user_id: ContextVar[UUID | None] = ContextVar(
    "current_user_id",
    default=None
)


def get_current_user_id()->UUID:
    """供业务工具读取当前请求的已认证用户

    Returns:
        UUID: 用户的id
    """
    user_id = current_user_id.get()

    if user_id is None:
        raise PermissionError("当前请求尚未认证")

    return user_id


class BearerAuthMiddleware:
    def __init__(self,app: ASGIApp, settings: Settings):
        self.app = app
        self.settings= settings

    async def __call__(
            self,
            scope: Scope,
            receive: Receive,
            send: Send
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope,receive,send)
            return

        request = Request(scope) 
        authorization = request.headers.get("authorization","")

        try:
            parts = authorization.split()

            if len(parts) !=2 or parts[0].lower() != "bearer":
                raise PermissionError("无效的访问令牌")

            raw_token = parts[1]

            user_id = await asyncio.to_thread(
                authenticate_token,
                self.settings,
                raw_token
            )

        except PermissionError:
            response = JSONResponse(
                {"detail": "无效的访问令牌"},
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )
            await response(scope,receive,send)
            return

        except PsycopgError:
            response = JSONResponse(
                {"detail":"认证服务暂不可用"},
                status_code=503,
            )
            await response(scope,receive,send)
            return

        context_token = current_user_id.set(user_id)

        try:
            await self.app(scope,receive,send)
        finally:
            current_user_id.reset(context_token)