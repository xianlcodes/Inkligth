import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, extract

from app.models.user import User
from app.models.literature import Literature
from app.models.note import Note
from app.models.presentation import Presentation
from app.models.reading_record import ReadingRecord
from app.models.admin import OperationLog, SystemConfig, ConfigChangeLog

logger = logging.getLogger(__name__)


class AdminService:

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------
    @staticmethod
    async def get_overview(db: AsyncSession, tencent_db: AsyncSession = None) -> dict:
        """Statistics overview. db=Alibaba for User, tencent_db=Tencent for Literature/Note/Presentation."""
        if tencent_db is None:
            tencent_db = db

        total_users_q = select(func.count(User.id))
        total_lit_q = select(func.count(Literature.id))
        read_q = select(func.count(Literature.id)).where(Literature.status == "read")
        unread_q = select(func.count(Literature.id)).where(Literature.status == "unread")
        reading_q = select(func.count(Literature.id)).where(Literature.status == "reading")
        notes_q = select(func.count(Note.id))
        pres_q = select(func.count(Presentation.id))

        total_users_r = await db.execute(total_users_q)
        total_lit_r = await tencent_db.execute(total_lit_q)
        read_r = await tencent_db.execute(read_q)
        unread_r = await tencent_db.execute(unread_q)
        reading_r = await tencent_db.execute(reading_q)
        notes_r = await tencent_db.execute(notes_q)
        pres_r = await tencent_db.execute(pres_q)

        return {
            "total_users": total_users_r.scalar() or 0,
            "total_literatures": total_lit_r.scalar() or 0,
            "total_read_literatures": read_r.scalar() or 0,
            "total_unread_literatures": unread_r.scalar() or 0,
            "total_reading_literatures": reading_r.scalar() or 0,
            "total_notes": notes_r.scalar() or 0,
            "total_presentations": pres_r.scalar() or 0,
        }

    @staticmethod
    async def get_timeseries_stats(db: AsyncSession, period: str = "day", tencent_db: AsyncSession = None) -> dict:
        """Time-series stats. db=Alibaba for User, tencent_db=Tencent for Literature/ReadingRecord."""
        if tencent_db is None:
            tencent_db = db
        trunc_field_map = {
            "day": "day",
            "week": "week",
            "month": "month",
            "year": "year",
        }
        trunc_field = trunc_field_map.get(period, "day")

        now = datetime.utcnow()
        if period == "day":
            since = now - timedelta(days=30)
        elif period == "week":
            since = now - timedelta(weeks=12)
        elif period == "month":
            since = now - timedelta(days=365)
        else:
            since = now - timedelta(days=365 * 3)

        new_users = await AdminService._trend_query(db, User, User.created_at, trunc_field, since)
        new_lits = await AdminService._trend_query(tencent_db, Literature, Literature.created_at, trunc_field, since)
        reading_act = await AdminService._trend_query(tencent_db, ReadingRecord, ReadingRecord.created_at, trunc_field, since)

        return {
            "new_users": new_users,
            "new_literatures": new_lits,
            "reading_activity": reading_act,
        }

    @staticmethod
    async def _trend_query(db, model, date_col, trunc_field: str, since: datetime) -> list[dict]:
        q = (
            select(
                func.date_trunc(trunc_field, date_col).label("date"),
                func.count().label("value"),
            )
            .where(date_col >= since)
            .group_by("date")
            .order_by("date")
        )
        result = await db.execute(q)
        rows = result.all()
        return [{"date": str(r.date), "value": r.value} for r in rows]

    # ------------------------------------------------------------------
    # User management
    # ------------------------------------------------------------------
    @staticmethod
    async def list_users(db: AsyncSession, skip: int = 0, limit: int = 50, search: str = "", tencent_db: AsyncSession = None) -> tuple[int, list]:
        """List users with literature count. db=Alibaba for User, tencent_db=Tencent for Literature count."""
        if tencent_db is None:
            tencent_db = db

        # Query lit counts from TencentDB separately (cross-database)
        lit_count_q = select(Literature.user_id, func.count(Literature.id).label("lit_count")).group_by(Literature.user_id)
        lit_count_res = await tencent_db.execute(lit_count_q)
        lit_counts = {row.user_id: row.lit_count for row in lit_count_res.all()}

        # Query users from AlibabaDB
        count_q = select(func.count(User.id))

        if search:
            filter_clause = User.email.ilike(f"%{search}%")
            count_q = count_q.where(filter_clause)

        total_res = await db.execute(count_q)
        total = total_res.scalar() or 0

        # Get matching user IDs first
        ids_q = select(User.id).order_by(User.created_at.desc())
        if search:
            ids_q = ids_q.where(User.email.ilike(f"%{search}%"))
        ids_q = ids_q.offset(skip).limit(limit)
        ids_res = await db.execute(ids_q)
        user_ids = [row[0] for row in ids_res.all()]

        if not user_ids:
            return total, []

        user_q = select(
            User.id, User.email, User.username, User.is_admin,
            User.created_at, User.updated_at,
        ).where(User.id.in_(user_ids)).order_by(User.created_at.desc())
        user_res = await db.execute(user_q)
        items = []
        for row in user_res.all():
            items.append({
                "id": row.id,
                "email": row.email,
                "username": row.username,
                "is_admin": row.is_admin,
                "literature_count": lit_counts.get(row.id, 0),
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            })
        return total, items

    @staticmethod
    async def update_user(db: AsyncSession, user: User, data: dict) -> User:
        if "is_admin" in data and data["is_admin"] is not None:
            user.is_admin = data["is_admin"]
        if data.get("password"):
            from app.core.security import get_password_hash
            user.hashed_password = get_password_hash(data["password"])
        await db.commit()
        await db.refresh(user)
        return user

    # ------------------------------------------------------------------
    # Operation logs
    # ------------------------------------------------------------------
    @staticmethod
    async def create_log(
        db: AsyncSession,
        user_id: Optional[str],
        user_email: Optional[str],
        action: str,
        resource: Optional[str] = None,
        resource_id: Optional[str] = None,
        detail: Optional[str] = None,
        ip_address: Optional[str] = None,
        status: str = "success",
    ) -> OperationLog:
        log = OperationLog(
            user_id=user_id,
            user_email=user_email,
            action=action,
            resource=resource,
            resource_id=resource_id,
            detail=detail,
            ip_address=ip_address,
            status=status,
        )
        db.add(log)
        await db.commit()
        await db.refresh(log)
        return log

    @staticmethod
    async def list_logs(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 50,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
    ) -> tuple[int, list[OperationLog]]:
        q = select(OperationLog)
        count_q = select(func.count(OperationLog.id))

        if user_id:
            q = q.where(OperationLog.user_id == user_id)
            count_q = count_q.where(OperationLog.user_id == user_id)
        if action:
            q = q.where(OperationLog.action == action)
            count_q = count_q.where(OperationLog.action == action)

        total_res = await db.execute(count_q)
        total = total_res.scalar() or 0

        q = q.order_by(OperationLog.created_at.desc()).offset(skip).limit(limit)
        items_res = await db.execute(q)
        return total, list(items_res.scalars().all())

    # ------------------------------------------------------------------
    # System config
    # ------------------------------------------------------------------
    @staticmethod
    async def get_all_configs(db: AsyncSession) -> list[SystemConfig]:
        q = select(SystemConfig).order_by(SystemConfig.key)
        result = await db.execute(q)
        return list(result.scalars().all())

    @staticmethod
    async def get_config(db: AsyncSession, key: str) -> Optional[SystemConfig]:
        q = select(SystemConfig).where(SystemConfig.key == key)
        result = await db.execute(q)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_all_configs_by_category(db: AsyncSession) -> dict[str, list[SystemConfig]]:
        q = select(SystemConfig).order_by(SystemConfig.sort_order, SystemConfig.key)
        result = await db.execute(q)
        items = list(result.scalars().all())
        grouped: dict[str, list[SystemConfig]] = {}
        for item in items:
            grouped.setdefault(item.category or "general", []).append(item)
        return grouped

    @staticmethod
    async def upsert_config(
        db: AsyncSession,
        key: str,
        data: dict,
        updated_by: Optional[str] = None,
    ) -> SystemConfig:
        existing = await AdminService.get_config(db, key)
        if existing:
            for field, val in data.items():
                if val is not None:
                    setattr(existing, field, val)
            existing.updated_by = updated_by
            existing.updated_at = datetime.utcnow()
            await db.commit()
            await db.refresh(existing)
            return existing
        else:
            cfg = SystemConfig(key=key, updated_by=updated_by, **data)
            db.add(cfg)
            await db.commit()
            await db.refresh(cfg)
            return cfg

    @staticmethod
    async def delete_config(db: AsyncSession, key: str) -> bool:
        existing = await AdminService.get_config(db, key)
        if not existing:
            return False
        await db.delete(existing)
        await db.commit()
        return True

    @staticmethod
    async def create_change_log(
        db: AsyncSession,
        config_key: str,
        old_value: Optional[str],
        new_value: Optional[str],
        changed_by: Optional[str] = None,
    ) -> ConfigChangeLog:
        log = ConfigChangeLog(
            config_key=config_key,
            old_value=old_value,
            new_value=new_value,
            changed_by=changed_by,
        )
        db.add(log)
        await db.commit()
        await db.refresh(log)
        return log

    @staticmethod
    async def get_change_logs(db: AsyncSession, config_key: Optional[str] = None, limit: int = 100) -> list[ConfigChangeLog]:
        q = select(ConfigChangeLog)
        if config_key:
            q = q.where(ConfigChangeLog.config_key == config_key)
        q = q.order_by(ConfigChangeLog.changed_at.desc()).limit(limit)
        result = await db.execute(q)
        return list(result.scalars().all())

    @staticmethod
    async def set_config(db: AsyncSession, key: str, value: str, description: Optional[str] = None, updated_by: Optional[str] = None) -> SystemConfig:
        existing = await AdminService.get_config(db, key)
        if existing:
            existing.value = value
            if description is not None:
                existing.description = description
            existing.updated_by = updated_by
            existing.updated_at = datetime.utcnow()
            await db.commit()
            await db.refresh(existing)
            return existing
        else:
            cfg = SystemConfig(
                key=key,
                value=value,
                description=description,
                updated_by=updated_by,
            )
            db.add(cfg)
            await db.commit()
            await db.refresh(cfg)
            return cfg


