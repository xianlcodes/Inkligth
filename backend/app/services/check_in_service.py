import logging
from datetime import date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.check_in import CheckIn
from app.services.storage_service import StorageService

logger = logging.getLogger(__name__)


def get_check_in_reward(streak_days: int) -> int:
    mb = 0
    if streak_days >= 90:
        mb = 500
    elif streak_days >= 30:
        mb = 100
    elif streak_days >= 7:
        mb = 20
    elif streak_days >= 3:
        mb = 10
    else:
        mb = 5
    return mb * 1024 * 1024


class CheckInService:
    @staticmethod
    async def get_today_check_in(db: AsyncSession, user_id: str) -> CheckIn | None:
        today = date.today()
        result = await db.execute(
            select(CheckIn).where(
                CheckIn.user_id == user_id,
                CheckIn.check_in_date == today,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_last_check_in(db: AsyncSession, user_id: str) -> CheckIn | None:
        result = await db.execute(
            select(CheckIn)
            .where(CheckIn.user_id == user_id)
            .order_by(CheckIn.check_in_date.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def check_in(db: AsyncSession, user_id: str) -> dict:
        existing = await CheckInService.get_today_check_in(db, user_id)
        if existing:
            return {
                "streak_days": existing.streak_days,
                "reward_bytes": 0,
                "already_checked_in": True,
            }

        last = await CheckInService.get_last_check_in(db, user_id)
        today = date.today()

        if last and last.check_in_date == today - timedelta(days=1):
            streak = last.streak_days + 1
        else:
            streak = 1

        reward = get_check_in_reward(streak)

        check_in_record = CheckIn(
            user_id=user_id,
            check_in_date=today,
            streak_days=streak,
            reward_bytes=reward,
        )
        db.add(check_in_record)

        if reward > 0:
            await StorageService.add_bonus_space(db, user_id, "check_in", reward)

        await db.commit()
        await db.refresh(check_in_record)

        storage = await StorageService.get_storage(db, user_id)

        return {
            "streak_days": streak,
            "reward_bytes": reward,
            "already_checked_in": False,
            "total_check_in_bonus": storage.check_in_bonus,
        }

    @staticmethod
    async def get_status(db: AsyncSession, user_id: str) -> dict:
        today_check = await CheckInService.get_today_check_in(db, user_id)
        last = await CheckInService.get_last_check_in(db, user_id)

        today = date.today()
        first_of_month = today.replace(day=1)

        result = await db.execute(
            select(CheckIn.check_in_date)
            .where(
                CheckIn.user_id == user_id,
                CheckIn.check_in_date >= first_of_month,
                CheckIn.check_in_date <= today,
            )
            .order_by(CheckIn.check_in_date)
        )
        checked_dates = [row[0] for row in result.all()]

        streak = last.streak_days if last else 0
        if last and last.check_in_date < today - timedelta(days=1):
            streak = 0

        return {
            "checked_in_today": today_check is not None,
            "streak_days": streak,
            "today_reward": get_check_in_reward(streak + 1) if not today_check else 0,
            "checked_dates": checked_dates,
        }