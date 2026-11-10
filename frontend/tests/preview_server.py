"""Isolated UI fixture server. No database, model, production credentials or disk writes.

From project root: .venv\Scripts\python.exe frontend/tests/preview_server.py
Demo credentials: preview / preview. All records are explicitly synthetic.
Uses the production static routing helper so /assets compatibility is exercised.
"""
import asyncio
import sys
from pathlib import Path

import uvicorn
from starlette.applications import Starlette
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from web_frontend import add_frontend_routes

DOC = '11111111-1111-4111-8111-111111111111'
VERSION = '22222222-2222-4222-8222-222222222222'
FOLDER = '33333333-3333-4333-8333-333333333333'
TIME = '2026-11-08T04:00:00Z'
document = {'id': DOC, 'title': '界面验收示例 · 知识归档笔记', 'tags': ['示例', '知识管理'],
            'updated_at': TIME, 'created_at': TIME, 'latest_version_id': VERSION, 'folder_id': None}
folders = [{'id': FOLDER, 'name': '示例文件夹', 'parent_id': None}]
trashed_documents = [{'id': '44444444-4444-4444-8444-444444444444', 'title': '示例 · 已回收草稿', 'deleted_at': TIME}]
trashed_folders = [{'id': '55555555-5555-4555-8555-555555555555', 'name': '示例 · 旧归档', 'deleted_at': TIME}]


async def api(request):
    path, method = request.url.path, request.method
    if path == '/api/auth/login':
        body = await request.json()
        await asyncio.sleep(.65)
        if body.get('login_name') not in ('preview', 'preview-expired', 'preview-unavailable') or body.get('password') != 'preview':
            return JSONResponse({'error': '用户名或密码错误'}, status_code=401)
        response = JSONResponse({'user': {'id': DOC, 'login_name': 'preview'}})
        cookie = {'preview': 'yes', 'preview-expired': 'expired', 'preview-unavailable': 'unavailable'}[body['login_name']]
        response.set_cookie('ui_preview', cookie, httponly=True, samesite='lax')
        return response
    if path == '/api/auth/logout':
        response = Response(status_code=204)
        response.delete_cookie('ui_preview')
        return response
    if path == '/api/auth/me' and request.cookies.get('ui_preview') == 'unavailable':
        return JSONResponse({'error': '示例会话检查失败'}, status_code=503)
    if request.cookies.get('ui_preview') != 'yes':
        return JSONResponse({'error': '请先登录'}, status_code=401)
    if path == '/api/auth/me':
        return JSONResponse({'user': {'id': DOC, 'login_name': 'preview'}})
    if path == '/api/folders' and method == 'GET':
        return JSONResponse({'folders': [] if request.query_params.get('parent_id') else folders})
    if path == '/api/folders' and method == 'POST':
        body = await request.json()
        entry = {'id': '66666666-6666-4666-8666-666666666666', 'name': body['name'], 'parent_id': body.get('parent_id')}
        folders.append(entry)
        return JSONResponse(entry, status_code=201)
    if path == '/api/documents' and method == 'GET':
        q = request.query_params.get('q', '')
        return JSONResponse({'documents': [] if q and q not in document['title'] else [document]})
    if path == f'/api/documents/{DOC}' and method == 'GET':
        return JSONResponse(document)
    if path == f'/api/documents/{DOC}' and method == 'PATCH':
        document.update(await request.json())
        return Response(status_code=204)
    if path == f'/api/documents/{DOC}/tags':
        document['tags'] = (await request.json())['tags']
        return Response(status_code=204)
    if path == f'/api/documents/{DOC}/versions':
        return JSONResponse({'versions': [{'id': VERSION, 'version_no': 1, 'captured_at': TIME, 'byte_size': 1024}]})
    if path == f'/api/versions/{VERSION}/processing-runs':
        return JSONResponse({'runs': [{'id': DOC, 'status': 'succeeded', 'is_published': True, 'chunk_count': 3}]})
    if path == '/api/trash/documents':
        return JSONResponse({'documents': trashed_documents})
    if path == '/api/trash/folders':
        return JSONResponse({'folders': trashed_folders})
    if path.endswith('/restore'):
        items = trashed_folders if '/folders/' in path else trashed_documents
        items[:] = [item for item in items if item['id'] not in path]
        return Response(status_code=204)
    if path == '/api/search':
        return JSONResponse({'results': [{'chunk_id': DOC, 'document_id': DOC, 'title': document['title'],
            'version_no': 1, 'locator': {'ordinal': 0},
            'content': '这是一段用于界面验收的示例原文。资料上传后需要手动处理，才会进入正文检索；搜索结果保留标题、版本和片段来源。'}]})
    return JSONResponse({'error': '此隔离预览未模拟该操作'}, status_code=501)


app = Starlette(routes=[Route('/api/{path:path}', api, methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE'])])
add_frontend_routes(app, ROOT / 'frontend' / 'dist')

if __name__ == '__main__':
    uvicorn.run(app, host='127.0.0.1', port=5188, log_level='warning')
