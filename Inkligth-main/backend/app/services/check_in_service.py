import logging
from datetime import date, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.check_in import CheckIn
from app.services.storage_service import StorageService

logger = logging.getLogger(__name__)

# Milestone rewards in MB — each milestone is awarded only once per user lifetime.
MILESTONES: dict[int, int] = {
    3: 10,
    7: 20,
    14: 25,
    30: 30,
    60: 35,
    90: 50,
    180: 60,
    365: 70,
}


class CheckInService:
    @staticmethod
    async def _get_max_streak(db: AsyncSession, user_id: str) -> int:
        """Return the user's all-time maximum streak_days from check-in records."""
        result = await db.execute(
            select(func.max(CheckIn.streak_days)).where(CheckIn.user_id == user_id)
        )
        return result.scalar() or 0

    @staticmethod
    async def _get_milestone_reward(db: AsyncSession, user_id: str, streak_days: int) -> int:
        """Return the reward in bytes if *streak_days* is a milestone not yet claimed, else 0."""
        if streak_days not in MILESTONES:
            return 0
        max_streak = await CheckInService._get_max_streak(db, user_id)
        if max_streak >= streak_days:
            return 0  # already claimed this milestone
        return MILESTONES[streak_days] * 1024 * 1024

    @staticmethod
    async def _get_next_milestone_reward(db: AsyncSession, user_id: str) -> int:
        """Return the reward (bytes) of the next unclaimed milestone, or 0 if all are claimed."""
        max_streak = await CheckInService._get_max_streak(db, user_id)
        for day in sorted(MILESTONES):
            if day > max_streak:
                return MILESTONES[day] * 1024 * 1024
        return 0

    @staticmethod
    async def _get_next_milestone_day(db: AsyncSession, user_id: str) -> Optional[int]:
        """Return the day-number of the next unclaimed milestone, or None if all are claimed."""
        max_streak = await CheckInService._get_max_streak(db, user_id)
        for day in sorted(MILESTONES):
            if day > max_streak:
                return day
        return None

    @staticmethod
    async def get_today_check_in(db: AsyncSession, user_id: str) -> Optional[CheckIn]:
        today = date.today()
        result = await db.execute(
            select(CheckIn).where(
                CheckIn.user_id == user_id,
                CheckIn.check_in_date == today,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_last_check_in(db: AsyncSession, user_id: str) -> Optional[CheckIn]:
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

        reward = await CheckInService._get_milestone_reward(db, user_id, streak)

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

        next_reward = await CheckInService._get_next_milestone_reward(db, user_id)
        next_day = await CheckInService._get_next_milestone_day(db, user_id)

        return {
            "checked_in_today": today_check is not None,
            "streak_days": streak,
            "today_reward": 0 if today_check else next_reward,
            "checked_dates": checked_dates,
            "next_milestone_reward": next_reward,
            "next_milestone_day": next_day,
        }