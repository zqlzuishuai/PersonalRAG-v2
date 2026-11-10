
import logging
from ipaddress import ip_address
from pathlib import Path
from uuid import UUID

from psycopg.errors import UniqueViolation
from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse, Response
from starlette.routing import Route

from auth import authenticate_password
from config import env_bool, load_settings, required_env
from documents import (
    DocumentRestoreConflictError,
    FolderNotFoundError,
    get_document,
    list_deleted_documents,
    list_document_versions,
    list_documents,
    move_document,
    rename_document,
    restore_document,
    set_document_tags,
    soft_delete_document,
    upload_bytes,
)
from folder import (
    FolderMoveConflictError,
    FolderRestoreConflictError,
    create_folder,
    list_deleted_folders,
    list_folders,
    move_folder,
    rename_folder,
    restore_folder_tree,
    soft_delete_folder_tree,
)
from knowledge_service import search_knowledge
from origin_guard import origin_allowed
from processing import (
    VersionNotFoundError,
    list_version_processing_runs,
    process_version,
)
from registration import RegistrationGuard, register_endpoint

logger = logging.getLogger(__name__)
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

def _is_plain_http(request):
    """Cloudflare Tunnel 同时接受 http 和 https；明文页面会让 Secure Cookie 失效，
    也让 Origin 变成 http:// 形式。"""
    if request.url.scheme != "http":
        return False
    forwarded=request.headers.get("x-forwarded-proto","").split(",")[0].strip().lower()
    if forwarded:
        return forwarded=="http"
    client=request.client
    if client is None:
        return False
    try:
        return not ip_address(client.host).is_loopback
    except ValueError:
        return True

class ForceHTTPSMiddleware:
    """页面请求强制跳到 https；写接口直接拒绝，避免明文提交密码。"""

    def __init__(self,app):
        self.app=app

    async def __call__(self,scope,receive,send):
        if scope["type"]!="http":
            await self.app(scope,receive,send)
            return
        request=Request(scope)
        if not _is_plain_http(request):
            await self.app(scope,receive,send)
            return
        if request.method in ("GET","HEAD"):
            response=RedirectResponse(str(request.url.replace(scheme="https")),status_code=308)
        else:
            response=JSONResponse({"error":"请通过 HTTPS 访问本站"},status_code=403)
        await response(scope,receive,send)

def healthz(request):
    return JSONResponse({"status": "ok"})

def create_app():
    middleware=[
        Middleware(ForceHTTPSMiddleware),
        Middleware(
            SessionMiddleware,
            secret_key=required_env("PERSONALRAG_WEB_SESSION_SECRET"),
            https_only=env_bool("PERSONALRAG_WEB_COOKIE_SECURE", default=True),
            same_site="lax",
            max_age=8*60*60),
    ]

    app = Starlette(
        debug=env_bool("PERSONALRAG_WEB_DEBUG",default=False),
        routes=[
            Route("/api/healthz",healthz,methods=["GET"]),
            Route("/api/auth/me",get_current_user_id,methods=["GET"]),
            Route("/api/auth/login",login,methods=["POST"]),
            Route("/api/auth/register",register_endpoint,max_body_size=4096,methods=["POST"]),
            Route("/api/auth/logout",logout,methods=["POST"]),
            Route("/api/documents",list_documents_endpoint,methods=["GET"]),
            Route("/api/documents",upload_bytes_endpoint,max_body_size=MAX_FILE_SIZE + 1024*1024,methods=["POST"]),
            Route("/api/folders",list_folders_endpoint,methods=["GET"]),
            Route("/api/folders/{scope}/{folder_id}",list_folders_endpoint,methods=["GET"]),
            Route("/api/folders",create_folder_endpoint,methods=["POST"]),
            Route("/api/folders/{folder_id}",rename_folder_endpoint,methods=["PATCH"]),
            Route("/api/documents/{document_id}",get_document_endpoint,methods=["GET"]),
            Route("/api/documents/{document_id}/versions",list_document_versions_endpoint,methods=["GET"]),
            Route("/api/documents/{document_id}/versions",upload_bytes_with_document_id_endpoint,max_body_size=MAX_FILE_SIZE + 1024*1024,methods=["POST"]),
            Route("/api/documents/{document_id}",rename_document_endpoint,methods=["PATCH"]),
            Route("/api/documents/{document_id}/tags",set_document_tags_endpoint,methods=["PUT"]),
            Route("/api/documents/{document_id}/folder",move_document_endpoint,methods=["PUT"]),
            Route("/api/documents/{document_id}",soft_delete_document_endpoint,methods=["DELETE"]),
            Route("/api/trash/documents",list_deleted_documents_endpoint,methods=["GET"]),
            Route("/api/documents/{document_id}/restore",restore_document_endpoint,methods=["POST"]),
            Route("/api/folders/{folder_id}/parent",move_folder_endpoint,methods=["PUT"]),
            Route("/api/folders/{folder_id}", soft_delete_folder_tree_endpoint, methods=["DELETE"]),
            Route("/api/trash/folders", list_deleted_folders_endpoint, methods=["GET"]),
            Route("/api/folders/{folder_id}/restore", restore_folder_tree_endpoint, methods=["POST"]),
            Route("/api/versions/{version_id}/process",process_version_endpoint,methods=["POST"]),
            Route("/api/versions/{version_id}/processing-runs",list_version_processing_runs_endpoint,methods=["GET"]),
            Route("/api/search",search_knowledge_endpoint,methods=["POST"])
        ],
        middleware=middleware,
        )

    app.state.settings = load_settings()
    app.state.registration_guard = RegistrationGuard()
    app.state.web_origin = required_env("PERSONALRAG_WEB_ORIGIN")
    if env_bool("PERSONALRAG_WEB_SERVE_FRONTEND", default=False):
        from web_frontend import add_frontend_routes
        add_frontend_routes(app, Path(__file__).resolve().parent / "frontend" / "dist")
    return app

async def get_current_user_id(request: Request):
    # if request.headers.get("origin") != request.app.state.web_origin:
    #     return JSONResponse({"error": "请求来源不允许"}, status_code=403)

    user_id = request.session.get("user_id")
    if not user_id:
        return JSONResponse({"error": "未登录"}, status_code=401)

    return JSONResponse({"user_id": user_id},status_code=200)

async def login(request:Request):
    if not origin_allowed(request):
        return JSONResponse({"error": "请求来源不允许"}, status_code=403)

    try:
        body = await request.json()
    except ValueError:
        return JSONResponse({"error": "请求体必须是有效的JSON"}, status_code=400)

    if (
        not isinstance(body, dict)
        or not isinstance(body.get("login_name"), str)
        or not isinstance(body.get("password"), str)
    ):
        return JSONResponse({"error": "请提供用户名和密码"}, status_code=400)

    try:
        user_id = await run_in_threadpool(
            authenticate_password,
            request.app.state.settings,
            body["login_name"],
            body["password"],
        )
    except PermissionError:
        return JSONResponse({"error": "用户名或密码错误"}, status_code=401)

    request.session.clear()
    request.session["user_id"] = str(user_id)
    return JSONResponse({"message": "登录成功"})

async def logout(request: Request):
    if not origin_allowed(request):
        return JSONResponse({"error": "请求来源不允许"}, status_code=403)

    request.session.clear()
    return Response(status_code=204)

async def list_folders_endpoint(request: Request):

    user_id = request.session.get("user_id")
    if not user_id:
        return JSONResponse({"error": "未登录"}, status_code=401)

    raw_parent_id = request.query_params.get("parent_id")
    try:
        parent_id = UUID(raw_parent_id) if raw_parent_id else None
    except ValueError:
        return JSONResponse({"error": "parent_id必须是有效的UUID"}, status_code=400)

    folders = await run_in_threadpool(
        list_folders,
        request.app.state.settings,
        UUID(user_id),
        parent_id
    )
    return JSONResponse({
        "folders":[
            {
                "id": str(folder["id"]),
                "name": folder["name"],
                "parent_id": (
                    str(folder["parent_id"]) if folder["parent_id"] else None
                )
            }
            for folder in folders
        ]
    })

async def list_documents_endpoint(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return JSONResponse({"error": "未登录"}, status_code=401)

    params = request.query_params
    scope = params.get("scope", "folder").strip().lower()
    if scope not in {"folder", "all", "subtree"}:
        return JSONResponse({"error": "scope 必须是 folder、all 或 subtree"}, status_code=400)

    raw_folder_id = params.get("folder_id", "").strip()
    try:
        folder_id = UUID(raw_folder_id) if raw_folder_id else None
    except ValueError:
        return JSONResponse({"error": "folder_id 必须是有效的 UUID"}, status_code=400)
    if scope == "subtree" and folder_id is None:
        return JSONResponse({"error": "subtree 范围必须指定 folder_id"}, status_code=400)
    if scope == "all" and folder_id is not None:
        return JSONResponse({"error": "all 范围不能同时指定 folder_id"}, status_code=400)

    q = params.get("q", "").strip() or None
    tags = [tag.strip() for tag in params.getlist("tag")]
    if any(not 1 <= len(tag) <= 50 for tag in tags):
        return JSONResponse({"error": "标签长度必须在 1 到 50 之间"}, status_code=400)

    try:
        limit = int(params.get("limit", 50))
        offset = int(params.get("offset", 0))
    except ValueError:
        return JSONResponse({"error": "limit 和 offset 必须是有效的整数"}, status_code=400)
    if not 1 <= limit <= 100:
        return JSONResponse({"error": "limit 必须在 1 到 100 之间"}, status_code=400)
    if offset < 0:
        return JSONResponse({"error": "offset 必须是非负整数"}, status_code=400)

    documents = await run_in_threadpool(
        list_documents,
        request.app.state.settings,
        UUID(user_id),
        folder_id,
        limit,
        offset,
        scope=scope,
        q=q,
        tags=tags,
    )
    return JSONResponse({
        "documents": [
            {
                "id": str(doc["id"]),
                "title": doc["title"],
                "folder_id": str(doc["folder_id"]) if doc["folder_id"] else None,
                "tags": doc["tags"],
                "latest_version_id": str(doc["latest_version_id"]) if doc["latest_version_id"] else None,
                "updated_at": doc["updated_at"].isoformat(),
            }
            for doc in documents
        ]
    })

async def create_folder_endpoint(request: Request):
    if not origin_allowed(request):
        return JSONResponse({"error": "请求来源不允许"}, status_code=403)



    user_id = request.session.get("user_id")
    if not user_id:
        return JSONResponse({"error": "未登录"}, status_code=401)
    
    try:
        body = await request.json()
    except ValueError:
        return JSONResponse({"error": "请求体必须是有效的JSON"}, status_code=400)



    if not isinstance(body, dict):
        return JSONResponse({"error": "请提供有效的名称和父文件夹ID"}, status_code=400)

    raw_name = body.get("name")
    name = raw_name.strip() if isinstance(raw_name, str) else ""
    if not 1 <= len(name) <= 200:
        return JSONResponse({"error": "名称长度必须在 1 到 200 之间"}, status_code=400)


    
    raw_parent_id = body.get("parent_id")
    if raw_parent_id is None or raw_parent_id == "":
        parent_id = None
    elif isinstance(raw_parent_id, str):
        try:
            parent_id = UUID(raw_parent_id)
        except ValueError:
            return JSONResponse({"error": "parent_id 必须是有效的 UUID"}, status_code=400)
    else:
        return JSONResponse({"error": "parent_id 必须是 UUID 或 null"}, status_code=400)

    try:
        folder_id = await run_in_threadpool(
            create_folder,
            request.app.state.settings,
            UUID(user_id),
            name,
            parent_id
        )
    except UniqueViolation:
        return JSONResponse({"error": "同级文件夹已存在同名目录"}, status_code=409)
    except ValueError:
        return JSONResponse({"error": "父文件夹不存在"}, status_code=404)
    
    return JSONResponse({
        "id": str(folder_id),
        "name": name,
        "parent_id": (
            str(parent_id) if parent_id else None
        )
    }, status_code=201)

async def rename_folder_endpoint(request: Request):
    if not origin_allowed(request):
        return JSONResponse({"error": "请求来源不允许"}, status_code=403)


    user_id = request.session.get("user_id")
    if not user_id:
        return JSONResponse({"error": "未登录"}, status_code=401)

    try:
        body = await request.json()
    except ValueError:
        return JSONResponse({"error": "请求体必须是有效的JSON"}, status_code=400)

    raw_name = body.get("name") if isinstance(body, dict) else None
    name = raw_name.strip() if isinstance(raw_name, str) else ""
    if not 1 <= len(name) <= 200:
        return JSONResponse({"error": "名称长度必须在 1 到 200 之间"}, status_code=400)

    try:
        folder_id = UUID(request.path_params["folder_id"])
    except ValueError:
        return JSONResponse({"error": "folder_id 必须是有效的 UUID"}, status_code=400)

    try:
        renamed_id = await run_in_threadpool(
            rename_folder,
            request.app.state.settings,
            UUID(user_id),
            folder_id,
            name,
        )
    except UniqueViolation:
        return JSONResponse({"error": "同级文件夹已存在同名目录"}, status_code=409)
    except ValueError:
        return JSONResponse({"error": "文件夹不存在"}, status_code=404)

    return JSONResponse({"id": str(renamed_id), "name": name})

async def upload_bytes_endpoint(request: Request):
    if not origin_allowed(request):
        return JSONResponse({"error": "请求来源不允许"}, status_code=403)

    user_id = request.session.get("user_id")
    if not user_id:
        return JSONResponse({"error": "未登录"}, status_code=401)

    async with request.form(max_files=1,max_fields=1) as form:
        file = form.get("file")
        raw_folder_id = form.get("folder_id")

        if not isinstance(raw_folder_id, str):
            return JSONResponse({"error": "请提供有效的 folder_id"}, status_code=400)
        if not isinstance(file,UploadFile) or not file.filename:
            return JSONResponse({"error": "请上传有效的文件"}, status_code=400)

        filename = file.filename.strip()
        if Path(filename).suffix.lower() not in {".txt",".md"}:
            return JSONResponse({"error": "仅支持上传 .txt 和 .md 文件"}, status_code=415)

        content =await file.read(MAX_FILE_SIZE + 1)
        if len(content) > MAX_FILE_SIZE:
            return JSONResponse({"error": "文件大小不能超过 10 MB"}, status_code=413)

        try:
            content.decode("utf-8")
        except UnicodeDecodeError:
            return JSONResponse({"error": "文件必须是有效的 UTF-8 编码文本"}, status_code=400)

        try:
            folder_id = UUID(raw_folder_id.strip()) if raw_folder_id.strip() else None
        except ValueError:
            return JSONResponse({"error": "folder_id 必须是有效的 UUID"}, status_code=400)


    try:
        upload_result=await run_in_threadpool(
            upload_bytes,
            request.app.state.settings,
            user_id,
            filename,
            content,
            folder_id=folder_id
        )
    except FolderNotFoundError:
        return JSONResponse({"error": "指定的文件夹不存在或不属于当前用户"}, status_code=404)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=404)

    return JSONResponse(
        {
            "document_id": str(upload_result.document_id), 
            "version_id": str(upload_result.version_id), 
            "version_no": upload_result.version_no
        }, 
        status_code=201
    )

async def get_document_endpoint(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return JSONResponse({"error": "未登录"}, status_code=401)

    try:
        document_id = UUID(request.path_params["document_id"])
    except ValueError:
        return JSONResponse({"error": "document_id 必须是有效的 UUID"}, status_code=400)

    try:
        document_data = await run_in_threadpool(
            get_document,
            request.app.state.settings,
            UUID(user_id),
            document_id
        )
    except ValueError:
        return JSONResponse({"error": "文件不存在或不属于当前用户"}, status_code=404)

    return JSONResponse({
        "id": str(document_data["id"]),
        "title": document_data["title"],
        "folder_id": str(document_data["folder_id"]) if document_data["folder_id"] else None,
        "tags": document_data["tags"],
        "latest_version_id": str(document_data["latest_version_id"]) if document_data["latest_version_id"] else None,
        "created_at": document_data["created_at"].isoformat(),
        "updated_at": document_data["updated_at"].isoformat(),
    })

async def list_document_versions_endpoint(request: Request):

    user_id = request.session.get("user_id")
    if not user_id:
        return JSONResponse({"error": "未登录"}, status_code=401)

    try:
        document_id = UUID(request.path_params["document_id"])
    except ValueError:
        return JSONResponse({"error": "document_id 必须是有效的 UUID"}, status_code=400)

    try:
        limit = int(request.query_params.get("limit", 20))
        offset = int(request.query_params.get("offset", 0))
    except ValueError:
        return JSONResponse({"error": "limit 和 offset 必须是有效的整数"}, status_code=400)

    if limit < 1 or limit > 100:
        return JSONResponse({"error": "limit 必须在 1 到 100 之间"}, status_code=400)

    if offset < 0:
        return JSONResponse({"error": "offset 必须是非负整数"}, status_code=400)

    try:
        versions = await run_in_threadpool(
            list_document_versions,
            request.app.state.settings,
            UUID(user_id),
            document_id,
            limit=limit,
            offset=offset
        )
    except ValueError:
        return JSONResponse({"error": "文件不存在或不属于当前用户"}, status_code=404)

    return JSONResponse({
        "versions":[
            {
                "id": str(version["id"]),
                "version_no": version["version_no"],
                "media_type": version["media_type"],
                "byte_size": version["byte_size"],
                "captured_at": version["captured_at"].isoformat(),
            }
            for version in versions
        ]
    })

async def rename_document_endpoint(request: Request):
    if not origin_allowed(request):
        return JSONResponse({"error": "请求来源不允许"}, status_code=403)

    user_id = request.session.get("user_id")
    if not user_id:
        return JSONResponse({"error": "未登录"}, status_code=401)

    try:
        document_id = UUID(request.path_params["document_id"])
    except ValueError:
        return JSONResponse({"error": "document_id 必须是有效的 UUID"}, status_code=400)

    try:
        body = await request.json()
    except ValueError:
        return JSONResponse({"error": "请求体必须是有效的JSON"}, status_code=400)

    raw_title = body.get("title") if isinstance(body, dict) else None
    title = raw_title.strip() if isinstance(raw_title, str) else ""
    if not 1 <= len(title) <= 200:
        return JSONResponse({"error": "标题长度必须在 1 到 200 之间"}, status_code=400)

    try:
        renamed_id = await run_in_threadpool(
            rename_document,
            request.app.state.settings,
            UUID(user_id),
            document_id,
            title,
        )
    except ValueError:
        return JSONResponse({"error": "文件不存在或不属于当前用户"}, status_code=404)

    return Response(status_code=204)

async def set_document_tags_endpoint(request: Request):
    if not origin_allowed(request):
        return JSONResponse({"error": "请求来源不允许"}, status_code=403)

    user_id = request.session.get("user_id")
    if not user_id:
        return JSONResponse({"error": "未登录"}, status_code=401)

    try:
        document_id = UUID(request.path_params["document_id"])
    except ValueError:
        return JSONResponse({"error": "document_id 必须是有效的 UUID"}, status_code=400)

    try:
        body = await request.json()
    except ValueError:
        return JSONResponse({"error": "请求体必须是有效的JSON"}, status_code=400)

    tags = body.get("tags") if isinstance(body, dict) else None
    if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
        return JSONResponse({"error": "tags 必须是字符串数组"}, status_code=400)
    tags = [tag.strip() for tag in tags]
    if any(not tag or len(tag) > 50 for tag in tags) or len(tags) > 50:
        return JSONResponse({"error": "标签数量或长度无效"}, status_code=400)

    try:
        result = await run_in_threadpool(
            set_document_tags,
            request.app.state.settings,
            UUID(user_id),
            document_id,
            tags,
        )
    except ValueError:
        return JSONResponse({"error": "文件不存在或不属于当前用户"}, status_code=404)

    return Response(status_code=204)

async def move_document_endpoint(request: Request):
    if not origin_allowed(request):
        return JSONResponse({"error": "请求来源不允许"}, status_code=403)

    user_id = request.session.get("user_id")
    if not user_id:
        return JSONResponse({"error": "未登录"}, status_code=401)

    try:
        document_id = UUID(request.path_params["document_id"])
    except ValueError:
        return JSONResponse({"error": "document_id 必须是有效的 UUID"}, status_code=400)

    try:
        body = await request.json()
    except ValueError:
        return JSONResponse({"error": "请求体必须是有效的JSON"}, status_code=400)
    
    if not isinstance(body, dict) or "folder_id" not in body:
        return JSONResponse({"error": "请求体必须包含 folder_id"}, status_code=400)

    raw_folder_id = body["folder_id"]
    if raw_folder_id in (None, ""):
        folder_id = None
    elif isinstance(raw_folder_id, str):
        try:
            folder_id = UUID(raw_folder_id)
        except ValueError:
            return JSONResponse({"error": "folder_id 必须是有效的 UUID"}, status_code=400)
    else:
        return JSONResponse({"error": "folder_id 必须是 UUID 或 null"}, status_code=400)

    try:
        result = await run_in_threadpool(
            move_document,
            request.app.state.settings,
            UUID(user_id),
            document_id,
            folder_id,
        )
    except FolderNotFoundError:
        return JSONResponse({"error": "指定的文件夹不存在或不属于当前用户"}, status_code=404)
    except ValueError:
        return JSONResponse({"error": "文件不存在或不属于当前用户"}, status_code=404)

    return Response(status_code=204)

async def upload_bytes_with_document_id_endpoint(request: Request):
    if not origin_allowed(request):
        return JSONResponse({"error": "请求来源不允许"}, status_code=403)

    user_id = request.session.get("user_id")
    if not user_id:
        return JSONResponse({"error": "未登录"}, status_code=401)

    try:
        document_id = UUID(request.path_params["document_id"])
    except ValueError:
        return JSONResponse({"error": "document_id 必须是有效的 UUID"}, status_code=400)

    async with request.form(max_files=1,max_fields=0) as form:
        file = form.get("file")

        if not isinstance(file,UploadFile) or not file.filename:
            return JSONResponse({"error": "请上传有效的文件"}, status_code=400)

        filename = file.filename.strip()
        if Path(filename).suffix.lower() not in {".txt",".md"}:
            return JSONResponse({"error": "仅支持上传 .txt 和 .md 文件"}, status_code=415)

        content =await file.read(MAX_FILE_SIZE + 1)
        if len(content) > MAX_FILE_SIZE:
            return JSONResponse({"error": "文件大小不能超过 10 MB"}, status_code=413)

        try:
            content.decode("utf-8")
        except UnicodeDecodeError:
            return JSONResponse({"error": "文件必须是有效的 UTF-8 编码文本"}, status_code=400)


    try:
        upload_result=await run_in_threadpool(
            upload_bytes,
            request.app.state.settings,
            user_id,
            filename,
            content,
            document_id=document_id
        )
    except FolderNotFoundError:
        return JSONResponse({"error": "指定的文件夹不存在或不属于当前用户"}, status_code=404)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=404)

    return JSONResponse(
        {
            "document_id": str(upload_result.document_id), 
            "version_id": str(upload_result.version_id), 
            "version_no": upload_result.version_no,
            "created_version": upload_result.created_version
        }, 
        status_code=201 if upload_result.created_version else 200
    )

async def soft_delete_document_endpoint(request: Request):
    if not origin_allowed(request):
        return JSONResponse({"error": "请求来源不允许"}, status_code=403)

    user_id = request.session.get("user_id")
    if not user_id:
        return JSONResponse({"error": "未登录"}, status_code=401)

    try:
        document_id = UUID(request.path_params["document_id"])
    except ValueError:
        return JSONResponse({"error": "document_id 必须是有效的 UUID"}, status_code=400)

    try:
        result = await run_in_threadpool(
            soft_delete_document,
            request.app.state.settings,
            UUID(user_id),
            document_id,
        )
    except ValueError:
        return JSONResponse({"error": "文件不存在或不属于当前用户"}, status_code=404)
    except RuntimeError:
        return JSONResponse({"error": "软删除资料失败，可能是因为不存在或其他原因"}, status_code=400)
    if not result:
        return JSONResponse({"error": "文件删除失败"}, status_code=400)
    return Response(status_code=204)

async def list_deleted_documents_endpoint(request: Request):
    # if request.headers.get("origin") != request.app.state.web_origin:
    #     return JSONResponse({"error": "请求来源不允许"}, status_code=403)

    user_id = request.session.get("user_id")
    if not user_id:
        return JSONResponse({"error": "未登录"}, status_code=401)
    
    params = request.query_params
    try:
        limit = int(params.get("limit", 50))
        offset = int(params.get("offset", 0))
    except ValueError:
        return JSONResponse({"error": "limit 和 offset 必须是有效的整数"}, status_code=400)
    if not 1 <= limit <= 100:
        return JSONResponse({"error": "limit 必须在 1 到 100 之间"}, status_code=400)
    if offset < 0:
        return JSONResponse({"error": "offset 必须是非负整数"}, status_code=400)

    try:
        deleted_documents = await run_in_threadpool(
            list_deleted_documents,
            request.app.state.settings,
            UUID(user_id),
            limit,
            offset,
        )
    except ValueError:
        return JSONResponse({"error": "用户不存在"}, status_code=404)
    return JSONResponse({
        "documents":[
            {
                "id":str(doc["id"]),
                "title":doc["title"],
                "folder_id":str(doc["folder_id"]) if doc["folder_id"] else None,
                "tags":doc["tags"],
                "deleted_at":doc["deleted_at"].isoformat(),
            }
            for doc in deleted_documents
        ]
        }, status_code=200)

async def restore_document_endpoint(request: Request):
    if not origin_allowed(request):
        return JSONResponse({"error": "请求来源不允许"}, status_code=403)

    user_id = request.session.get("user_id")
    if not user_id:
        return JSONResponse({"error": "未登录"}, status_code=401)

    try:
        document_id = UUID(request.path_params["document_id"])
    except ValueError:
        return JSONResponse({"error": "document_id 必须是有效的 UUID"}, status_code=400)

    try:
        result = await run_in_threadpool(
            restore_document,
            request.app.state.settings,
            UUID(user_id),
            document_id,
        )
    except DocumentRestoreConflictError as exc:
        return JSONResponse({"error": str(exc)}, status_code=409)
    except ValueError:
        return JSONResponse({"error": "文件不存在或不属于当前用户"}, status_code=404)
    except RuntimeError:
        return JSONResponse({"error": "恢复资料失败，可能是因为不存在或其他原因"}, status_code=400)
    if not result:
        return JSONResponse({"error": "文件恢复失败"}, status_code=400)
    return Response(status_code=204)

async def move_folder_endpoint(request: Request):
    if not origin_allowed(request):
        return JSONResponse({"error": "请求来源不允许"}, status_code=403)

    user_id = request.session.get("user_id")
    if not user_id:
        return JSONResponse({"error": "未登录"}, status_code=401)

    try:
        folder_id = UUID(request.path_params["folder_id"])
    except ValueError:
        return JSONResponse({"error": "folder_id 必须是有效的 UUID"}, status_code=400)

    try:
        body = await request.json()
    except ValueError:
        return JSONResponse({"error": "请求体必须是有效的JSON"}, status_code=400)
    
    if not isinstance(body, dict) or "parent_id" not in body:
        return JSONResponse({"error": "请求体必须包含 parent_id"}, status_code=400)

    raw_parent_id = body["parent_id"]
    if raw_parent_id in (None, ""):
        parent_id = None
    elif isinstance(raw_parent_id, str):
        try:
            parent_id = UUID(raw_parent_id)
        except ValueError:
            return JSONResponse({"error": "parent_id 必须是有效的 UUID"}, status_code=400)
    else:
        return JSONResponse({"error": "parent_id 必须是 UUID 或 null"}, status_code=400)

    try:
        result = await run_in_threadpool(
            move_folder,
            request.app.state.settings,
            UUID(user_id),
            folder_id,
            parent_id,
        )
    except UniqueViolation:
        return JSONResponse({"error": "同级文件夹已存在同名目录"}, status_code=409)
    except FolderMoveConflictError:
        return JSONResponse({"error": "目标位置会使目录树形成环"}, status_code=409)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=404)

    return Response(status_code=204)

async def soft_delete_folder_tree_endpoint(request: Request):
    if not origin_allowed(request):
        return JSONResponse({"error": "请求来源不允许"}, status_code=403)
    user_id = request.session.get("user_id")
    if not user_id:
        return JSONResponse({"error": "未登录"}, status_code=401)
    try:
        folder_id = UUID(request.path_params["folder_id"])
    except ValueError:
        return JSONResponse({"error": "folder_id 必须是有效的 UUID"}, status_code=400)
    try:
        await run_in_threadpool(
            soft_delete_folder_tree, 
            request.app.state.settings, 
            UUID(user_id), 
            folder_id,
        )
    except ValueError:
        return JSONResponse({"error": "文件夹不存在或不属于当前用户"}, status_code=404)
    return Response(status_code=204)

async def list_deleted_folders_endpoint(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return JSONResponse({"error": "未登录"}, status_code=401)
    try:
        limit = int(request.query_params.get("limit", 50))
        offset = int(request.query_params.get("offset", 0))
    except ValueError:
        return JSONResponse({"error": "limit 和 offset 必须是有效的整数"}, status_code=400)
    if not 1 <= limit <= 100 or offset < 0:
        return JSONResponse({"error": "limit 必须在 1 到 100 之间，offset 必须非负"}, status_code=400)
    folders = await run_in_threadpool(
        list_deleted_folders, request.app.state.settings, UUID(user_id), limit, offset,
    )
    return JSONResponse({"folders": [
        {
            "id": str(folder["id"]),
            "name": folder["name"],
            "parent_id": str(folder["parent_id"]) if folder["parent_id"] else None,
            "deleted_at": folder["deleted_at"].isoformat(),
        }
        for folder in folders
    ]})

async def restore_folder_tree_endpoint(request: Request):
    if not origin_allowed(request):
        return JSONResponse({"error": "请求来源不允许"}, status_code=403)
    user_id = request.session.get("user_id")
    if not user_id:
        return JSONResponse({"error": "未登录"}, status_code=401)
    try:
        folder_id = UUID(request.path_params["folder_id"])
    except ValueError:
        return JSONResponse({"error": "folder_id 必须是有效的 UUID"}, status_code=400)
    try:
        await run_in_threadpool(
            restore_folder_tree, 
            request.app.state.settings, 
            UUID(user_id), 
            folder_id,
        )
    except FolderRestoreConflictError as exc:
        return JSONResponse({"error": str(exc)}, status_code=409)
    except ValueError:
        return JSONResponse({"error": "文件夹不存在或不属于当前用户"}, status_code=404)
    return Response(status_code=204)

async def process_version_endpoint(request: Request):
    if not origin_allowed(request):
        return JSONResponse({"error": "请求来源不允许"}, status_code=403)
    user_id = request.session.get("user_id")
    if not user_id:
        return JSONResponse({"error": "未登录"}, status_code=401)
    try:
        version_id = UUID(request.path_params["version_id"])
    except ValueError:
        return JSONResponse({"error": "version_id 必须是有效的 UUID"}, status_code=400)
    try:
        await run_in_threadpool(
            process_version, 
            request.app.state.settings, 
            UUID(user_id), 
            version_id,
        )
    except VersionNotFoundError:
        return JSONResponse({"error": "版本不存在或不属于当前用户"}, status_code=404)
    except Exception:
        logger.exception("版本处理失败，version_id=%s", version_id)
        return JSONResponse({"error": "处理失败，请查看运行状态"}, status_code=500)
    return Response(status_code=200)

async def list_version_processing_runs_endpoint(request: Request):
    # if request.headers.get("origin") != request.app.state.web_origin:
    #     return JSONResponse({"error": "请求来源不允许"}, status_code=403)
    user_id = request.session.get("user_id")
    if not user_id:
        return JSONResponse({"error": "未登录"}, status_code=401)
    try:
        version_id = UUID(request.path_params["version_id"])
    except ValueError:
        return JSONResponse({"error": "version_id 必须是有效的 UUID"}, status_code=400)
    try:
        limit = int(request.query_params.get("limit", 50))
        offset = int(request.query_params.get("offset", 0))
    except ValueError:
        return JSONResponse({"error": "limit 和 offset 必须是有效的整数"}, status_code=400)
    if not 1 <= limit <= 100 or offset < 0:
        return JSONResponse({"error": "limit 必须在 1 到 100 之间，offset 必须非负"}, status_code=400)
    try:
        runs = await run_in_threadpool(
            list_version_processing_runs, 
            request.app.state.settings, 
            UUID(user_id), 
            version_id,
            limit,
            offset,
        )
    except VersionNotFoundError:
        return JSONResponse({"error": "版本不存在或不属于当前用户"}, status_code=404)
    except Exception:
        logger.exception("版本处理失败，version_id=%s", version_id)
        return JSONResponse({"error": "处理失败，请查看运行状态"}, status_code=500)
    return JSONResponse({"runs": [
        {
            "id": str(run["id"]),
            "version_id": str(run["version_id"]),
            "status": run["status"],
            "chunk_count": run["chunk_count"] if run["chunk_count"] is not None else None,
            "finished_at": run["finished_at"].isoformat() if run["finished_at"] else None,
            "error_summary": run["error_summary"] if run["error_summary"] else None,
            "is_published": run["is_published"],
            "is_latest_version": run["is_latest_version"],
        }
        for run in runs
    ]})

async def search_knowledge_endpoint(request: Request):
    if not origin_allowed(request):
        return JSONResponse({"error": "请求来源不允许"}, status_code=403)
    user_id = request.session.get("user_id")
    if not user_id:
        return JSONResponse({"error": "未登录"}, status_code=401)
    try:
        body = await request.json()
    except ValueError:
        return JSONResponse({"error": "请求体必须是有效的JSON"}, status_code=400)
    query = body.get("query", "") if isinstance(body, dict) else ""
    if not isinstance(query, str):
        return JSONResponse({"error": "查询内容必须是字符串"}, status_code=400)
    query=query.strip()
    if not query:
        return JSONResponse({"error": "查询内容不能为空"}, status_code=400)


    top_k = body.get("top_k", 5) if isinstance(body, dict) else 5
    if type(top_k) is not int or top_k < 1 or top_k > 20:
        return JSONResponse({"error": "top_k 必须是 1 到 20 之间的整数"}, status_code=400)
    
    try:
        results = await run_in_threadpool(
            search_knowledge,
            request.app.state.settings,
            UUID(user_id),
            query,
            top_k
        )
    except Exception:
        logger.exception("知识搜索失败，user_id=%s, query=%s", user_id, query)
        return JSONResponse({"error": "搜索失败，请稍后重试"}, status_code=500)

    return JSONResponse({
        "results": [
            {
                "chunk_id": str(result["chunk_id"]),
                "document_id": str(result["document_id"]),
                "version_id": str(result["version_id"]),
                "run_id": str(result["run_id"]),
                "title": result["title"],
                "version_no": result["version_no"],
                "content": result["content"],
                "locator": result["locator"],
            }
            for result in results
        ]
    })



if __name__ == "__main__":
    import uvicorn
    app = create_app()
    uvicorn.run(app, host="127.0.0.1",port=8001)