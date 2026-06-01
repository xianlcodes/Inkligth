import asyncio
import uuid
import logging
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


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
        }


class TaskStore:
    def __init__(self):
        self._tasks: dict[str, TaskInfo] = {}
        self._cancel_events: dict[str, asyncio.Event] = {}
        self._lock = asyncio.Lock()

    async def create_task(self, task_type: str, user_id: str = "") -> TaskInfo:
        task_id = str(uuid.uuid4())
        task = TaskInfo(task_id, task_type, user_id=user_id)
        async with self._lock:
            self._tasks[task_id] = task
        logger.info(f"Task created: {task_id}, type: {task_type}, user: {user_id}")
        return task

    async def get_task(self, task_id: str) -> Optional[TaskInfo]:
        async with self._lock:
            return self._tasks.get(task_id)

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

    async def register_cancel_event(self, task_id: str) -> asyncio.Event:
        event = asyncio.Event()
        async with self._lock:
            self._cancel_events[task_id] = event
        return event

    async def cancel_task(self, task_id: str) -> bool:
        async with self._lock:
            task = self._tasks.get(task_id)
            event = self._cancel_events.get(task_id)
        if task and task.status in (TaskStatus.PENDING, TaskStatus.RUNNING):
            task.status = TaskStatus.CANCELLED
            task.error = "任务已被取消"
            if event:
                event.set()
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

    async def cleanup_old_tasks(self, max_age_seconds: int = 3600):
        pass


task_store = TaskStore()