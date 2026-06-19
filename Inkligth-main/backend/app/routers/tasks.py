import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.database import get_db
from app.utils.task_store import task_store, TaskStatus
from app.services.translation_service import TranslationService
from app.models.literature import Literature
from sqlalchemy import update
from datetime import datetime, timedelta
from app.core.config import settings

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


@router.post("/tasks/{task_id}/cancel")
async def cancel_task(
    task_id: str,
    current_user=Depends(get_current_user),
):
    from app.routers.literature import request_cancellation

    task = await task_store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")

    if task.status not in (TaskStatus.PENDING, TaskStatus.RUNNING):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="任务不在运行中，无需取消")

    request_cancellation(task_id)
    await task_store.update_task(task_id, status=TaskStatus.CANCELLED, error="用户取消翻译")
    logger.info(f"Task cancelled by user: {task_id}")
    return {"code": 200, "msg": "success", "data": {"task_id": task_id, "status": "cancelled"}}


@router.post("/tasks/cancel-all")
async def cancel_all_user_tasks(
    current_user=Depends(get_current_user),
):
    count = await task_store.cancel_user_tasks(str(current_user.id))
    logger.info("User %s cancelled %d running tasks", current_user.id, count)
    return {"code": 200, "msg": "success", "data": {"cancelled_count": count}}


@router.post("/tasks/translations/cleanup")
async def cleanup_translations(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    deleted = await TranslationService.cleanup_expired_translations(db)

    cutoff = datetime.utcnow() - timedelta(days=settings.TRANSLATION_CACHE_TTL_DAYS)
    await db.execute(
        update(Literature)
        .where(Literature.translated_at < cutoff)
        .values(translated_text=None, translated_at=None)
    )
    await db.commit()

    logger.info("Cleanup completed: %d translation records removed, cutoff: %s", deleted, cutoff.isoformat())
    return {
        "code": 200,
        "msg": "success",
        "data": {"deleted": deleted, "cutoff": cutoff.isoformat(), "ttl_days": settings.TRANSLATION_CACHE_TTL_DAYS},
    }
