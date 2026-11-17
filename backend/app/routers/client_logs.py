"""前端错误上报端点：收集浏览器端 JS 错误，落入后端日志统一排查。

设计要点：
- 不要求登录：登录页白屏等场景同样收得到；靠 IP 限流 + 字段长度上限防滥用；
- 写入 logger "inklight.client"（WARNING/ERROR 级别），自动带上本次上报请求的
  request_id；前端会额外回传「出错那次请求」的 request_id 用于串联前后端日志；
- 上报内容只收 message/stack/url 等诊断信息，前端已确保不含业务数据。
"""
import logging
import time
from collections import deque
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.core.request_context import get_client_ip

logger = logging.getLogger("inklight.client")

router = APIRouter(prefix="/client-logs", tags=["client-logs"])

_MAX_REPORTS_PER_WINDOW = 10       # 单 IP 每分钟最多上报次数
_WINDOW_SECONDS = 60.0
_ip_report_times: dict[str, deque] = {}


class ClientLogPayload(BaseModel):
    level: str = Field("error", description="error | warning")
    message: str = Field(..., max_length=500, description="错误摘要")
    stack: Optional[str] = Field(None, max_length=4000, description="JS 堆栈")
    url: Optional[str] = Field(None, max_length=500, description="出错的页面地址")
    request_id: Optional[str] = Field(None, max_length=64, description="出错 API 请求的 X-Request-ID")


def _check_rate_limit(ip: str) -> bool:
    """滑动窗口限流：单 IP 每分钟最多 _MAX_REPORTS_PER_WINDOW 次。"""
    now = time.monotonic()
    times = _ip_report_times.setdefault(ip, deque())
    while times and now - times[0] > _WINDOW_SECONDS:
        times.popleft()
    if len(times) >= _MAX_REPORTS_PER_WINDOW:
        return False
    times.append(now)
    # 防止 dict 无限增长（保留最近活跃的 IP）
    if len(_ip_report_times) > 10000:
        for key in [k for k, v in _ip_report_times.items() if not v]:
            _ip_report_times.pop(key, None)
    return True


@router.post("")
async def report_client_log(payload: ClientLogPayload, request: Request):
    # 经 nginx 反代时取 X-Forwarded-For 第一跳，否则只记到代理 IP
    ip = get_client_ip(request)
    if not _check_rate_limit(ip):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="上报过于频繁")

    level = logging.ERROR if payload.level == "error" else logging.WARNING
    # 出错请求的 request_id 前端可能回传，用于串联前后端日志
    origin = f" origin_request_id={payload.request_id}" if payload.request_id else ""
    stack = payload.stack.strip()[:4000] if payload.stack and payload.stack.strip() else ""
    logger.log(
        level,
        "前端报错 [%s] %s | page=%s ip=%s%s%s",
        payload.level, payload.message[:500], (payload.url or "-")[:500], ip, origin,
        f"\n{stack}" if stack else "",
    )
    return {"ok": True}
