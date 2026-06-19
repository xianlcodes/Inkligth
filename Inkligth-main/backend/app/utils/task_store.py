import asyncio
import json
import uuid
import logging
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import redis.asyncio as aioredis
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False
    logger.info("redis.asyncio not available, task store will use in-memory only")


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskInfo:
    def __init__(self, task_id: str, task_type: str, user_id: str = ""):
        self.task_id = task_id
        self.task_type = task_type
        self.user_id = user_id
        self.status = TaskStatus.PENDING
        self.progress = 0
        self.total = 0
        self.result = None
        self.error = None

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "status": self.status.value,
            "progress": self.progress,
            "total": self.total,
            "result": self.result,
            "error": self.error,
            "user_id": self.user_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TaskInfo":
        task = cls(data["task_id"], data.get("task_type", "unknown"), data.get("user_id", ""))
        task.status = TaskStatus(data.get("status", "pending"))
        task.progress = data.get("progress", 0)
        task.total = data.get("total", 0)
        task.result = data.get("result")
        task.error = data.get("error")
        return task


class TaskStore:
    """Task store with Redis persistence (falls back to in-memory only).

    - In-memory dict for fast local access
    - Redis for cross-worker persistence and restart survival
    - Tasks auto-expire from Redis after 2 hours
    """

    def __init__(self):
        self._tasks: dict[str, TaskInfo] = {}
        self._cancel_events: dict[str, asyncio.Event] = {}
        self._lock = asyncio.Lock()
        self._redis = None
        self._redis_prefix = "task_store:"
        self._redis_ttl = 7200  # 2 hours

    async def _get_redis(self):
        if self._redis is None:
            if not HAS_REDIS:
                self._redis = False
                return None
            try:
                from app.core.config import settings
                url = settings.REDIS_URL_FINAL
                r = aioredis.from_url(url, decode_responses=True, socket_connect_timeout=2)
                await r.ping()
                self._redis = r
                logger.info("TaskStore connected to Redis at %s", url)
            except Exception as e:
                logger.warning("Redis unavailable for TaskStore: %s, using in-memory only", e)
                self._redis = False
                return None
        return self._redis if self._redis else None

    async def _redis_set(self, task_id: str, task: TaskInfo):
        redis = await self._get_redis()
        if redis:
            try:
                await redis.setex(
                    f"{self._redis_prefix}{task_id}",
                    self._redis_ttl,
                    json.dumps(task.to_dict(), default=str),
                )
            except Exception as e:
                logger.warning("Failed to persist task %s to Redis: %s", task_id, e)

    async def _redis_get(self, task_id: str) -> Optional[TaskInfo]:
        redis = await self._get_redis()
        if redis:
            try:
                data = await redis.get(f"{self._redis_prefix}{task_id}")
                if data:
                    return TaskInfo.from_dict(json.loads(data))
            except Exception as e:
                logger.warning("Failed to read task %s from Redis: %s", task_id, e)
        return None

    async def create_task(self, task_type: str, user_id: str = "") -> TaskInfo:
        task_id = str(uuid.uuid4())
        task = TaskInfo(task_id, task_type, user_id=user_id)
        async with self._lock:
            self._tasks[task_id] = task
        await self._redis_set(task_id, task)
        logger.warning("TASK_CREATED: task=%s type=%s user=%s redis=%s",
                       task_id, task_type, user_id,
                       self._redis is not False and self._redis is not None)
        return task

    async def get_task(self, task_id: str) -> Optional[TaskInfo]:
        # 1. Check in-memory first
        async with self._lock:
            task = self._tasks.get(task_id)
        if task:
            return task
        # 2. Fall back to Redis
        task = await self._redis_get(task_id)
        if task:
            async with self._lock:
                self._tasks[task_id] = task  # warm the in-memory cache
            return task
        logger.warning("TASK_NOT_FOUND: task=%s in_memory_keys=%d redis=%s",
                       task_id, len(self._tasks),
                       self._redis is not False and self._redis is not None)
        return None

    async def update_task(
        self,
        task_id: str,
        status: Optional[TaskStatus] = None,
        progress: Optional[int] = None,
        total: Optional[int] = None,
        result: Optional[dict] = None,
        error: Optional[str] = None,
    ):
        async with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                # Try to load from Redis (e.g. after server restart)
                loaded = await self._redis_get(task_id)
                if loaded:
                    self._tasks[task_id] = loaded
                    task = loaded
            if task:
                if status is not None:
                    task.status = status
                if progress is not None:
                    task.progress = progress
                if total is not None:
                    task.total = total
                if result is not None:
                    task.result = result
                if error is not None:
                    task.error = error
        if task:
            await self._redis_set(task_id, task)

    async def register_cancel_event(self, task_id: str) -> asyncio.Event:
        event = asyncio.Event()
        async with self._lock:
            self._cancel_events[task_id] = event
        return event

    async def cancel_task(self, task_id: str) -> bool:
        task = await self.get_task(task_id)
        if not task:
            return False
        if task.status in (TaskStatus.PENDING, TaskStatus.RUNNING):
            task.status = TaskStatus.CANCELLED
            task.error = "任务已被取消"
            async with self._lock:
                event = self._cancel_events.get(task_id)
            if event:
                event.set()
            await self._redis_set(task_id, task)
            logger.info("Task cancelled: %s", task_id)
            return True
        return False

    async def cancel_user_tasks(self, user_id: str) -> int:
        if not user_id:
            return 0
        cancelled = 0
        async with self._lock:
            for tid, task in self._tasks.items():
                if task.user_id == user_id and task.status in (TaskStatus.PENDING, TaskStatus.RUNNING):
                    task.status = TaskStatus.CANCELLED
                    task.error = "用户已登出，任务自动取消"
                    await self._redis_set(tid, task)
                    event = self._cancel_events.get(tid)
                    if event:
                        event.set()
                    cancelled += 1
        if cancelled:
            logger.info("Cancelled %d running tasks for user %s", cancelled, user_id)
        return cancelled

    async def is_cancelled(self, task_id: str) -> bool:
        async with self._lock:
            event = self._cancel_events.get(task_id)
        return event.is_set() if event else False

    async def remove_cancel_event(self, task_id: str):
        async with self._lock:
            self._cancel_events.pop(task_id, None)

    async def cleanup_stale_tasks(self):
        """Mark stale running/pending tasks as failed (called on startup)."""
        async with self._lock:
            count = 0
            stale_ids = []
            for task_id, task in self._tasks.items():
                if task.status in (TaskStatus.PENDING, TaskStatus.RUNNING):
                    task.status = TaskStatus.FAILED
                    task.error = "服务器重启，任务已终止"
                    stale_ids.append(task_id)
                    count += 1
            for task_id in stale_ids:
                await self._redis_set(task_id, self._tasks[task_id])
            if count:
                logger.info("Marked %d stale tasks as failed on startup", count)
        # Also check Redis for stale tasks from other workers
        redis = await self._get_redis()
        if redis:
            try:
                cursor = 0
                stale_count = 0
                while True:
                    cursor, keys = await redis.scan(cursor=cursor, match=f"{self._redis_prefix}*", count=100)
                    if keys:
                        for key in keys:
                            data = await redis.get(key)
                            if data:
                                info = json.loads(data)
                                if info.get("status") in ("pending", "running"):
                                    info["status"] = "failed"
                                    info["error"] = "服务器重启，任务已终止"
                                    await redis.setex(key, self._redis_ttl, json.dumps(info, default=str))
                                    stale_count += 1
                    if cursor == 0:
                        break
                if stale_count:
                    logger.info("Marked %d stale Redis tasks as failed on startup", stale_count)
            except Exception as e:
                logger.warning("Failed to clean stale Redis tasks: %s", e)


task_store = TaskStore()
