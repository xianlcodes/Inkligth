"""请求上下文与错误处理：request_id 贯穿一次请求（含其触发的后台任务）的所有日志。

- request_id 存在 contextvar 中，由 RequestIdFilter 注入每条日志记录
  （filter 挂在 handler 上，对全部子 logger 的传播记录生效）；
- HTTP 中间件为每个请求生成 request id、写响应头 X-Request-ID，
  并输出一条 access 日志（方法、路径、状态码、耗时、user_id），
  取代被静音的 uvicorn access log；
- Starlette 的 BackgroundTasks 在同一任务内执行，contextvar 自动传播，
  因此 background_tasks.add_task(...) 派生的后台任务日志自带触发请求的
  request_id（后台任务自身还会打 task_id，两者都可检索）。
"""
import logging
import time
import uuid
from contextvars import ContextVar

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

access_logger = logging.getLogger("inklight.access")
error_logger = logging.getLogger("inklight.error")

# 这些路径只记 DEBUG，避免健康检查刷屏
_QUIET_PATH_PREFIXES = ("/api/v1/health", "/health", "/favicon.ico")


def get_request_id() -> str:
    return request_id_var.get()


class RequestIdFilter(logging.Filter):
    """把 request_id 注入每条日志记录（非请求上下文为 "-"）。"""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


def get_client_ip(request: Request) -> str:
    """取真实客户端 IP：经 nginx 反代时 X-Forwarded-For 的第一跳才是用户。

    request.client.host 在反代场景下是 nginx 的地址，没有排查价值。
    """
    forwarded = request.headers.get("x-forwarded-for") or ""
    first_hop = forwarded.split(",")[0].strip()
    if first_hop:
        return first_hop
    return request.headers.get("x-real-ip") or (
        request.client.host if request.client else "-"
    )


def _extract_user_id(request: Request) -> str:
    """从 Authorization 头解出 user_id（不查库；失败返回 anon）。

    仅用于 access 日志，绝不能因为 token 解析问题影响请求本身。
    """
    auth = request.headers.get("authorization") or ""
    if not auth.lower().startswith("bearer "):
        return "anon"
    try:
        from app.core.security import decode_token
        return str(decode_token(auth[7:].strip()) or "anon")
    except Exception:
        return "anon"


async def _request_context_middleware(request: Request, call_next):
    rid = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
    token = request_id_var.set(rid)
    start = time.perf_counter()
    try:
        response = await call_next(request)
        status_code = response.status_code
        response.headers["X-Request-ID"] = rid
    except Exception:
        # 全局异常 handler 通常已把异常转成响应；能走到这里说明 handler 也失败
        error_logger.exception(
            "请求处理失败 %s %s", request.method, request.url.path
        )
        status_code = 500
        response = JSONResponse(
            status_code=500,
            content={"detail": "服务器内部错误，请稍后重试", "request_id": rid},
            headers={"X-Request-ID": rid},
        )
    finally:
        duration_ms = (time.perf_counter() - start) * 1000
        path = request.url.path
        user_id = _extract_user_id(request)
        client_ip = get_client_ip(request)
        log = access_logger.debug if path.startswith(_QUIET_PATH_PREFIXES) else access_logger.info
        log(
            "%s %s -> %s (%.0fms) ip=%s user=%s",
            request.method, path, status_code, duration_ms, client_ip, user_id,
        )
        request_id_var.reset(token)
    return response


def register(app: FastAPI) -> None:
    """在 main.py 中注册请求上下文中间件。

    未捕获异常统一由 _request_context_middleware 的 except 分支兜底：
    记录完整堆栈并返回带 request_id 的 500 响应（该分支位于所有路由
    外侧，是唯一入口；add_exception_handler(Exception) 反而在其外侧、
    永远不会触发，故不注册）。
    """
    app.middleware("http")(_request_context_middleware)
