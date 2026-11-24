import asyncio
from contextvars import ContextVar
from uuid import UUID

import jwt
from jwt import PyJWKClient
from psycopg import Error as PsycopgError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from auth import authenticate_token, resolve_cloudflare_user_id
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


class CloudflareUserBindingMiddleware(BaseHTTPMiddleware):
    def __init__(self,app:ASGIApp,*,settings:Settings,issuer:str):
        super().__init__(app)
        self.settings=settings
        self.issuer=issuer

    async def dispatch(self,request:Request,call_next):
        cf_user=getattr(request.state,"user",None)
        subject=getattr(cf_user,"sub",None)

        if not subject:
            return JSONResponse(
                {"detail": "缺少用户身份"},
                status_code=403
            )

        try:
            user_id=await asyncio.to_thread(
                resolve_cloudflare_user_id,
                self.settings,
                self.issuer,
                subject
            )
        except PsycopgError:
            return JSONResponse(
                {"detail":"认证服务暂不可用"},
                status_code=503,
            )
        if not user_id:
            return JSONResponse(
                {"detail": "账号未授权"},
                status_code=403
            )
        context_token=current_user_id.set(user_id)

        try:
            return await call_next(request)
        finally:
            current_user_id.reset(context_token)


# 未启用该中间件,改用封装包验签
class CloudflareAccessAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self,app: ASGIApp, team_domain:str,audience:str):
        super().__init__(app)
        self.issuer=team_domain.rstrip("/")
        self.audience=audience

        self.jwks_client=PyJWKClient(
            self.issuer+"/cdn-cgi/access/certs",
            cache_jwk_set=True,
            lifespan=300
        )

    async def dispatch(self,request:Request,call_next):
        token=request.headers.get("Cf-Access-Jwt-Assertion") or \
                request.cookies.get("CF_Authorization")

        if not token:
            return JSONResponse(
                {"detail": "无效的访问令牌"},
                status_code=401
            )

        try:
            signing_key=self.jwks_client.get_signing_key_from_jwt(token)
            payload=jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self.audience,
                issuer=self.issuer,
                options={"require": ["exp", "iat", "iss", "aud"]}
            )

            request.state.user=payload

        except jwt.PyJWTError as e:
            return JSONResponse(
                {"detail": f"无效的访问令牌:{e}"},
                status_code=401
            )

        return await call_next(request)


        





    # async def __call__(
    #         self,
    #         scope: Scope,
    #         receive: Receive,
    #         send: Send
    # ) -> None:
    #     if scope["type"] != "http":
    #         await self.app(scope,receive,send)
    #         return

    #     request = Request(scope) 
    #     cf_access_jwt = request.headers.get("cf-access-jwt-assertion","")

    #     if not cf_access_jwt:
    #         response = JSONResponse(
    #             {"detail": "无效的访问令牌"},
    #             status_code=401,
    #             headers={"WWW-Authenticate": "Bearer"},
    #         )
    #         await response(scope,receive,send)
    #         return

    #     # 这里可以添加对 Cloudflare Access JWT 的验证逻辑
    #     # 如果验证失败，返回 401 响应
    #     PyJWT[crypto]

    #     await self.app(scope,receive,send)