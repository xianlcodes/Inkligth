import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.core.deps import get_current_user
from app.schemas.storage import CheckInStatusResponse, CheckInResponse
from app.services.check_in_service import CheckInService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("", response_model=CheckInResponse)
async def check_in(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await CheckInService.check_in(db, current_user.id)
    if result.get("already_checked_in"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="今日已签到",
        )
    return CheckInResponse(
        streak_days=result["streak_days"],
        reward_bytes=result["reward_bytes"],
        total_check_in_bonus=result["total_check_in_bonus"],
    )


@router.get("/status", response_model=CheckInStatusResponse)
async def get_check_in_status(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await CheckInService.get_status(db, current_user.id)
    return CheckInStatusResponse(
        checked_in_today=result["checked_in_today"],
        streak_days=result["streak_days"],
        today_reward=result["today_reward"],
        checked_dates=result["checked_dates"],
        next_milestone_reward=result["next_milestone_reward"],
        next_milestone_day=result["next_milestone_day"],
    )