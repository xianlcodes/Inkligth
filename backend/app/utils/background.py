"""后台任务派发助手。

为什么不用 FastAPI 的 BackgroundTasks：
FastAPI 的 yield 型依赖（如 Depends(get_db)）会在**后台任务执行完毕之后**
才回收，也就是说后台任务跑 3 分钟，那个数据库连接就被占 3 分钟。
PDF/PPT/全文翻译这类任务动辄几分钟，并发几个就能把连接池（10+20）打满，
导致全站请求排队 30 秒后 500（2026-11-26 事故）。

用 asyncio.create_task 派发，请求返回后依赖立刻回收连接，后台任务
自己用独立会话（各任务内部本来就已 async with session_factory()）。
"""
import asyncio
import logging

logger = logging.getLogger(__name__)

# 持有任务强引用，防止被 GC 提前回收（Python 官方文档的建议做法）
_background_tasks: set[asyncio.Task] = set()


def _on_done(task: asyncio.Task) -> None:
    _background_tasks.discard(task)
    if task.cancelled():
        return
    exc = task.exception()
    if exc is not None:
        logger.error("后台任务异常退出: %s: %s", type(exc).__name__, exc, exc_info=exc)


def spawn_background(coro, *, name: str | None = None) -> asyncio.Task:
    """派发后台任务（不阻塞响应、不占用请求级数据库会话）。"""
    task = asyncio.create_task(coro, name=name)
    _background_tasks.add(task)
    task.add_done_callback(_on_done)
    return task
