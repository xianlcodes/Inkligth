from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.stats import RecordReadingRequest
from app.services.stats_service import StatsService

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/reading")
async def get_reading_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stats = await StatsService.get_reading_stats(db, str(current_user.id))
    return {
        "code": 200,
        "msg": "success",
        "data": stats,
    }


@router.get("/calendar")
async def get_calendar(
    days: int = Query(30, ge=7, le=90, description="统计天数"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = await StatsService.get_calendar(db, str(current_user.id), days)
    return {
        "code": 200,
        "msg": "success",
        "data": data,
    }


@router.post("/reading/record")
async def record_reading(
    body: RecordReadingRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await StatsService.record_reading(
        db,
        str(current_user.id),
        body.literature_id,
        body.current_page,
        body.duration_seconds,
    )
    return {
        "code": 200,
        "msg": "success",
        "data": {"message": "阅读记录已保存"},
    }