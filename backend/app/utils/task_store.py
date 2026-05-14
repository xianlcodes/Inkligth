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
    def __init__(self, task_id: str, task_type: str):
        self.task_id = task_id
        self.task_type = task_type
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
        self._lock = asyncio.Lock()

    async def create_task(self, task_type: str) -> TaskInfo:
        task_id = str(uuid.uuid4())
        task = TaskInfo(task_id, task_type)
        async with self._lock:
            self._tasks[task_id] = task
        logger.info(f"Task created: {task_id}, type: {task_type}")
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

    async def cleanup_old_tasks(self, max_age_seconds: int = 3600):
        pass


task_store = TaskStore()