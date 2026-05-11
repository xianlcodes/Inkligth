import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.deps import get_current_user
from app.utils.task_store import task_store

logger = logging.getLogger(__name__)
router = APIRouter(tags=["tasks"])


@router.get("/tasks/{task_id}")
async def get_task_status(
    task_id: str,
    current_user=Depends(get_current_user),
):
    task = await task_store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    return task.to_dict()