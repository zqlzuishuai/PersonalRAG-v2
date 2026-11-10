"""Public web registration; existing tenant RLS remains in force."""
import asyncio
import re
import time
from collections import deque
from ipaddress import ip_address
from uuid import uuid4

from argon2 import PasswordHasher
from psycopg import Error as DatabaseError
from psycopg.errors import UniqueViolation
from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse

from config import env_bool
from db import user_transaction
from origin_guard import origin_allowed


def validate_registration(login_name, password):
    if not isinstance(login_name,str) or not isinstance(password,str):
        raise ValueError('请提供用户名和密码')
    name=login_name.strip().lower()
    if not re.fullmatch(r'[a-z0-9_][a-z0-9_-]{2,31}',name):
        raise ValueError('用户名须为 3–32 位字母、数字、下划线或短横线')
    if not 10 <= len(password) <= 128 or not password.strip():
        raise ValueError('密码长度须为 10–128 位，不能全为空格')
    return name


def register_user(settings, login_name, password):
    name=validate_registration(login_name,password)
    digest=PasswordHasher().hash(password)
    user_id=uuid4()
    with user_transaction(settings,user_id) as conn:
        conn.execute('INSERT INTO rag.users (id,login_name,password_hash) VALUES (%s,%s,%s)',(user_id,name,digest))
    return user_id


class RegistrationGuard:
    def __init__(self):
        self.addresses={}
        self.global_attempts=deque()
        self.hash_slots=asyncio.Semaphore(2)

    def allow(self,address,now=None):
        now=time.monotonic() if now is None else now
        cutoff=now-900
        while self.global_attempts and self.global_attempts[0]<=cutoff:self.global_attempts.popleft()
        self.addresses={key:deque(t for t in times if t>cutoff) for key,times in self.addresses.items() if times and times[-1]>cutoff}
        if len(self.global_attempts)>=30 or (address not in self.addresses and len(self.addresses)>=1024):return False
        attempts=self.addresses.setdefault(address,deque())
        if len(attempts)>=5:return False
        attempts.append(now);self.global_attempts.append(now)
        return True


async def register_endpoint(request):
    if not origin_allowed(request):
        return JSONResponse({'error':'请求来源不允许'},status_code=403)
    if not env_bool('PERSONALRAG_WEB_REGISTRATION_OPEN',default=False):
        return JSONResponse({'error':'暂未开放注册'},status_code=403)
    try:
        body=await request.json()
        if not isinstance(body,dict):raise ValueError('请提供用户名和密码')
        name=validate_registration(body.get('login_name'),body.get('password'))
    except ValueError as error:
        return JSONResponse({'error':str(error)},status_code=400)
    guard=request.app.state.registration_guard
    address=request.client.host if request.client else 'unknown'
    # Cloudflare overwrites this header; accept it only from the local tunnel.
    try:
        if ip_address(address).is_loopback and request.headers.get('cf-connecting-ip'):
            address=str(ip_address(request.headers['cf-connecting-ip']))
    except ValueError:pass
    if not guard.allow(address):
        return JSONResponse({'error':'注册请求过于频繁，请在 15 分钟后重试'},status_code=429,headers={'Retry-After':'900'})
    # Do not queue unbounded Argon2 work under simultaneous requests.
    if guard.hash_slots.locked():
        return JSONResponse({'error':'注册服务繁忙，请稍后重试'},status_code=429,headers={'Retry-After':'5'})
    try:
        async with guard.hash_slots:
            await run_in_threadpool(register_user,request.app.state.settings,name,body['password'])
    except UniqueViolation:
        return JSONResponse({'error':'该用户名已被使用'},status_code=409)
    except DatabaseError:
        return JSONResponse({'error':'注册服务暂不可用，请稍后重试'},status_code=503)
    return JSONResponse({'message':'注册成功，请使用新账号登录'},status_code=201)
