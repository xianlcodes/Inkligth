import logging
from datetime import date, timedelta
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.literature import Literature
from app.models.reading_record import ReadingRecord

logger = logging.getLogger(__name__)


class StatsService:

    @staticmethod
    async def get_reading_stats(db: AsyncSession, user_id: str) -> dict:
        q = select(Literature).where(Literature.user_id == user_id)
        result = await db.execute(q)
        literatures = result.scalars().all()

        total = len(literatures)
        read_count = sum(1 for l in literatures if l.status == "read")
        reading_count = sum(1 for l in literatures if l.status == "reading")
        unread_count = sum(1 for l in literatures if l.status == "unread")
        read_progress = round(read_count / total * 100, 1) if total > 0 else 0.0

        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)

        week_q = (
            select(
                func.count(func.distinct(ReadingRecord.literature_id)),
                func.coalesce(func.sum(ReadingRecord.reading_time_seconds), 0),
            )
            .where(
                and_(
                    ReadingRecord.user_id == user_id,
                    ReadingRecord.record_date >= week_start,
                    ReadingRecord.record_date <= today,
                )
            )
        )
        week_result = await db.execute(week_q)
        week_count, week_time = week_result.one()

        month_q = (
            select(func.count(func.distinct(ReadingRecord.literature_id)))
            .where(
                and_(
                    ReadingRecord.user_id == user_id,
                    ReadingRecord.record_date >= month_start,
                    ReadingRecord.record_date <= today,
                )
            )
        )
        month_result = await db.execute(month_q)
        month_count = month_result.scalar() or 0

        days_with_records_q = (
            select(func.count(func.distinct(ReadingRecord.record_date)))
            .where(
                and_(
                    ReadingRecord.user_id == user_id,
                    ReadingRecord.record_date >= week_start,
                    ReadingRecord.record_date <= today,
                )
            )
        )
        days_result = await db.execute(days_with_records_q)
        active_days = days_result.scalar() or 0
        avg_daily = int(week_time / active_days) if active_days > 0 else 0

        return {
            "total_literatures": total,
            "read_count": read_count,
            "reading_count": reading_count,
            "unread_count": unread_count,
            "read_progress": read_progress,
            "week_count": int(week_count),
            "month_count": int(month_count),
            "week_reading_time_seconds": int(week_time),
            "avg_daily_time_seconds": avg_daily,
        }

    @staticmethod
    async def get_calendar(db: AsyncSession, user_id: str, days: int = 30) -> dict:
        today = date.today()
        start_date = today - timedelta(days=days - 1)

        q = (
            select(
                ReadingRecord.record_date,
                func.sum(ReadingRecord.pages_read).label("pages"),
                func.sum(ReadingRecord.reading_time_seconds).label("time_sec"),
            )
            .where(
                and_(
                    ReadingRecord.user_id == user_id,
                    ReadingRecord.record_date >= start_date,
                    ReadingRecord.record_date <= today,
                )
            )
            .group_by(ReadingRecord.record_date)
            .order_by(ReadingRecord.record_date)
        )
        result = await db.execute(q)
        rows = result.all()

        data_map = {}
        for row in rows:
            data_map[row.record_date] = {
                "pages_read": int(row.pages or 0),
                "time_seconds": int(row.time_sec or 0),
            }

        calendar_days = []
        for i in range(days):
            d = start_date + timedelta(days=i)
            entry = data_map.get(d, {"pages_read": 0, "time_seconds": 0})
            calendar_days.append({
                "date": d,
                "pages_read": entry["pages_read"],
                "time_seconds": entry["time_seconds"],
            })

        return {"days": calendar_days}

    @staticmethod
    async def record_reading(
        db: AsyncSession,
        user_id: str,
        literature_id: str,
        current_page: int,
        duration_seconds: int = 0,
    ) -> None:
        today = date.today()

        q = select(ReadingRecord).where(
            and_(
                ReadingRecord.user_id == user_id,
                ReadingRecord.literature_id == literature_id,
                ReadingRecord.record_date == today,
            )
        ).order_by(ReadingRecord.id.desc())
        result = await db.execute(q)
        records = result.scalars().all()

        if records:
            # 合并多条记录（处理历史重复数据）
            record = records[0]
            for dup in records[1:]:
                record.pages_read = max(record.pages_read, dup.pages_read)
                record.reading_time_seconds += dup.reading_time_seconds
                record.last_page = max(record.last_page, dup.last_page)
                await db.delete(dup)
            record.pages_read = max(record.pages_read, current_page)
            record.reading_time_seconds += duration_seconds
            record.last_page = current_page
            await db.flush()
        else:
            record = ReadingRecord(
                user_id=user_id,
                literature_id=literature_id,
                record_date=today,
                pages_read=current_page,
                reading_time_seconds=duration_seconds,
                last_page=current_page,
            )
            db.add(record)

        lit_q = select(Literature).where(Literature.id == literature_id)
        lit_result = await db.execute(lit_q)
        literature = lit_result.scalar_one_or_none()
        if literature:
            literature.last_read_page = current_page
            literature.total_reading_time_seconds = (literature.total_reading_time_seconds or 0) + duration_seconds
            if literature.status == "unread":
                literature.status = "reading"

        await db.commit()
        logger.info("Recorded reading: user=%s lit=%s page=%d time=%d", user_id, literature_id, current_page, duration_seconds)