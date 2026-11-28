"""平台免费翻译额度服务。

额度规则（2026-11 定稿，每日额度版）：
- platform_free_translations > 0：每人每天 N 次「PDF 文献翻译」免费额度，
  按北京时间日界每天自动重置（daily_date != 今天即懒重置，无需定时任务）；
- 每日次数用完后，回退消耗 free_translations 赠送余额（签到里程碑等
  运营场景发放），两者都为 0 才判定额度不足；
- platform_free_translations = -1：不限量模式，不扣减任何余额，
  仅记录 used_count 供运营统计；
- 仅 PDF 原位翻译任务消耗额度；用户自配 AI 引擎时不消耗（无限量）；
- 扣减用 UPDATE ... WHERE 余额充足 + RETURNING 校验，保证并发下不会超发；
- 任务因 AI 失败而中止时返还额度；用户主动取消不返还（已发生的调用无法撤回）。
"""
import asyncio
import logging
from datetime import datetime

from sqlalchemy import text, update
from sqlalchemy.exc import IntegrityError

from app.db.database import AlibabaSessionLocal
from app.models.user_quota import UserQuota
from app.utils.timezone import now_bjt

logger = logging.getLogger(__name__)

# 单 worker 部署（uvicorn --workers 1）：进程内锁让扣减完全串行化。
# RETURNING 校验是第二层保险：即使未来扩多实例，也能通过
# 「返回值必须 >= 0」拦截任何快照语义差异导致的超发。
_consume_lock = asyncio.Lock()


_table_ready = False


async def _ensure_quota_table() -> None:
    """确保 user_quotas 表与 prefer_free 列存在（幂等，仅首次或检测到缺失时执行）。"""
    global _table_ready
    if _table_ready:
        return
    from app.db.database import alibaba_engine, AlibabaBase
    async with alibaba_engine.begin() as conn:
        await conn.run_sync(
            AlibabaBase.metadata.create_all, tables=[UserQuota.__table__]
        )
        # 列自愈：create_all 不会给已存在的表加新列，这里补 ALTER。
        # 「列已存在」的错误（重复执行/旧库已手工加过列）直接忽略。
        heals = [
            ("prefer_free", "BOOLEAN NOT NULL DEFAULT FALSE"),
            ("daily_used", "INTEGER NOT NULL DEFAULT 0"),
            ("daily_date", "VARCHAR(10)"),
        ]
        for column, ddl in heals:
            try:
                await conn.execute(text(
                    f"ALTER TABLE user_quotas ADD COLUMN {column} {ddl}"
                ))
            except Exception as e:
                if 'duplicate column' not in str(e).lower() and 'already exists' not in str(e).lower():
                    raise
    _table_ready = True
    logger.warning("user_quotas 表/列已自动补建（建议补跑 migrations/006、007、008）")


class QuotaService:
    @staticmethod
    async def _get_or_create(session, user_id: str) -> UserQuota:
        """取额度记录；不存在则按平台配置赠送额度懒创建（幂等，防并发重复插入）。

        表缺失（未跑迁移）时自动建表后重试一次，避免线上 500。
        """
        try:
            return await QuotaService._get_or_create_inner(session, user_id)
        except Exception as e:
            msg = str(e).lower()
            if 'does not exist' in msg or 'undefinedtable' in msg or 'no such table' in msg:
                await _ensure_quota_table()
                # 原会话可能已失效，换一个新会话重试
                from app.db.database import AlibabaSessionLocal as _factory
                async with _factory() as fresh:
                    return await QuotaService._get_or_create_inner(fresh, user_id)
            raise

    @staticmethod
    async def _get_or_create_inner(session, user_id: str) -> UserQuota:
        quota = await session.get(UserQuota, user_id)
        if quota:
            return quota
        # 新用户不预发赠送余额：每日额度按 platform_free_translations 配置
        # 逐日生效（懒创建 + 跨天懒重置），余额仅由运营场景（签到里程碑）累加
        quota = UserQuota(
            user_id=user_id,
            free_translations=0,
            used_count=0,
        )
        session.add(quota)
        try:
            await session.commit()
        except IntegrityError:
            # 并发下别的请求已创建：回滚后取已有记录
            await session.rollback()
            quota = await session.get(UserQuota, user_id)
            if quota is None:
                raise
        await session.refresh(quota)
        return quota

    @staticmethod
    async def get_summary(user_id: str) -> dict:
        """返回 {remaining, used, total_granted, prefer_free, unlimited, daily_limit}。

        remaining = 今日剩余次数 + 赠送余额，与 consume 的扣减顺序对应，
        前端展示与准入判断统一用这个口径。
        """
        from app.services.platform_config_service import PlatformConfigService
        daily_limit, unlimited = await PlatformConfigService.get_free_translations()
        today = now_bjt().strftime("%Y-%m-%d")
        async with AlibabaSessionLocal() as session:
            quota = await QuotaService._get_or_create(session, user_id)
            if quota.daily_date == today:
                daily_remaining = max(daily_limit - quota.daily_used, 0)
            else:
                # 计数日期不是今天：当日次数已随日界重置
                daily_remaining = daily_limit
            balance = max(quota.free_translations, 0)
            remaining = daily_remaining + balance
            return {
                "remaining": remaining,
                "used": quota.used_count,
                "total_granted": remaining + quota.used_count,
                "prefer_free": bool(quota.prefer_free),
                "unlimited": unlimited,
                "daily_limit": daily_limit,
            }

    @staticmethod
    async def set_preference(user_id: str, prefer_free: bool) -> None:
        """设置翻译通道偏好：True = 优先使用平台免费额度。"""
        async with AlibabaSessionLocal() as session:
            await QuotaService._get_or_create(session, user_id)
            await session.execute(
                update(UserQuota)
                .where(UserQuota.user_id == user_id)
                .values(
                    prefer_free=bool(prefer_free),
                    updated_at=datetime.utcnow(),
                )
            )
            await session.commit()
        logger.info("翻译通道偏好更新: user=%s prefer_free=%s", user_id, prefer_free)

    @staticmethod
    async def remaining(user_id: str) -> int:
        summary = await QuotaService.get_summary(user_id)
        return summary["remaining"]

    @staticmethod
    async def consume(user_id: str) -> bool:
        """原子扣减 1 次。返回 False 表示额度不足。

        扣减顺序与 get_summary 的 remaining 口径一致：
        1. 当日免费次数（每日额度模式，跨天懒重置）；
        2. 次数用完 → 赠送余额（签到里程碑等运营场景发放）。

        不限量模式（platform_free_translations = -1）：不扣减任何余额直接放行，
        仅 used_count +1 记账供运营统计；此时永远返回 True。

        并发双保险（生产为单 worker 部署）：
        1. 进程内 _consume_lock 串行化扣减；
        2. UPDATE ... WHERE 余额充足 + RETURNING 校验——若任何数据库
           快照语义差异导致超发，回滚并视为额度不足。
        """
        from app.services.platform_config_service import PlatformConfigService
        daily_limit, unlimited = await PlatformConfigService.get_free_translations()

        if unlimited:
            async with AlibabaSessionLocal() as session:
                await QuotaService._get_or_create(session, user_id)
                await session.execute(
                    update(UserQuota)
                    .where(UserQuota.user_id == user_id)
                    .values(
                        used_count=UserQuota.used_count + 1,
                        updated_at=datetime.utcnow(),
                    )
                )
                await session.commit()
            logger.info("平台额度不限量模式，仅记账不扣减: user=%s", user_id)
            return True

        async with _consume_lock:
            async with AlibabaSessionLocal() as session:
                quota = await QuotaService._get_or_create(session, user_id)
                today = now_bjt().strftime("%Y-%m-%d")

                # 跨天懒重置：计数日期不是今天 → 当日次数已随日界恢复
                if quota.daily_date != today:
                    await session.execute(
                        update(UserQuota)
                        .where(UserQuota.user_id == user_id)
                        .values(
                            daily_used=0,
                            daily_date=today,
                            updated_at=datetime.utcnow(),
                        )
                    )
                    quota.daily_used = 0

                # 1) 当日免费次数
                if quota.daily_used < daily_limit:
                    result = await session.execute(
                        update(UserQuota)
                        .where(
                            UserQuota.user_id == user_id,
                            UserQuota.daily_date == today,
                            UserQuota.daily_used < daily_limit,
                        )
                        .values(
                            daily_used=UserQuota.daily_used + 1,
                            used_count=UserQuota.used_count + 1,
                            updated_at=datetime.utcnow(),
                        )
                        .returning(UserQuota.daily_used)
                    )
                    row = result.first()
                    if row is not None and 0 < row[0] <= daily_limit:
                        await session.commit()
                        logger.info(
                            "每日免费额度扣减: user=%s 今日已用 %d/%d",
                            user_id, row[0], daily_limit,
                        )
                        return True
                    # 并发抢额失败（理论上单 worker + 锁不会发生）：回滚并视为不足
                    await session.rollback()
                    logger.warning("每日额度扣减校验失败，视为额度不足: user=%s", user_id)
                    return False

                # 2) 当日次数用完 → 赠送余额兜底
                result = await session.execute(
                    update(UserQuota)
                    .where(
                        UserQuota.user_id == user_id,
                        UserQuota.free_translations > 0,
                    )
                    .values(
                        free_translations=UserQuota.free_translations - 1,
                        used_count=UserQuota.used_count + 1,
                        updated_at=datetime.utcnow(),
                    )
                    .returning(UserQuota.free_translations)
                )
                row = result.first()
                if row is not None and row[0] >= 0:
                    await session.commit()
                    logger.info("赠送余额扣减: user=%s 剩余=%d", user_id, row[0])
                    return True
                # 额度不足（或防御性拦截负值）：回滚本次写操作
                await session.rollback()
                if row is not None and row[0] < 0:
                    await session.execute(
                        update(UserQuota)
                        .where(UserQuota.user_id == user_id)
                        .values(free_translations=0)
                    )
                    await session.commit()
                    logger.error("检测到赠送余额负值并已钳制为 0: user=%s", user_id)
                logger.info("今日免费额度与赠送余额均不足: user=%s", user_id)
                return False

    @staticmethod
    async def refund(user_id: str) -> None:
        """返还 1 次（任务因 AI 失败中止时调用）。

        返还与 consume 的扣减顺序对应：当日仍有计数记录 → 回退当日次数；
        否则回退赠送余额（跨天边界下两者对用户可用量的效果等价）。
        不限量模式下余额未扣减过，只回退 used_count 记账。
        """
        from app.services.platform_config_service import PlatformConfigService
        _, unlimited = await PlatformConfigService.get_free_translations()

        if unlimited:
            async with AlibabaSessionLocal() as session:
                await QuotaService._get_or_create(session, user_id)
                await session.execute(
                    update(UserQuota)
                    .where(
                        UserQuota.user_id == user_id,
                        UserQuota.used_count > 0,
                    )
                    .values(
                        used_count=UserQuota.used_count - 1,
                        updated_at=datetime.utcnow(),
                    )
                )
                await session.commit()
            logger.info("平台额度不限量模式，返还仅回退记账: user=%s", user_id)
            return

        async with AlibabaSessionLocal() as session:
            quota = await QuotaService._get_or_create(session, user_id)
            today = now_bjt().strftime("%Y-%m-%d")
            if quota.daily_date == today and quota.daily_used > 0:
                # 当日次数回退（used_count 已随扣减 +1，这里同步 -1）
                await session.execute(
                    update(UserQuota)
                    .where(
                        UserQuota.user_id == user_id,
                        UserQuota.daily_date == today,
                        UserQuota.daily_used > 0,
                    )
                    .values(
                        daily_used=UserQuota.daily_used - 1,
                        used_count=UserQuota.used_count - 1,
                        updated_at=datetime.utcnow(),
                    )
                )
            else:
                # 赠送余额回退（含跨天边界：昨日扣的当日次数按余额补回）
                await session.execute(
                    update(UserQuota)
                    .where(
                        UserQuota.user_id == user_id,
                        UserQuota.used_count > 0,
                    )
                    .values(
                        free_translations=UserQuota.free_translations + 1,
                        used_count=UserQuota.used_count - 1,
                        updated_at=datetime.utcnow(),
                    )
                )
            await session.commit()
        logger.info("平台额度返还: user=%s", user_id)

    @staticmethod
    async def add_free(user_id: str, amount: int, reason: str = "") -> None:
        """赠送额度（签到里程碑等运营场景），amount 必须 > 0。"""
        if amount <= 0:
            return
        async with AlibabaSessionLocal() as session:
            await QuotaService._get_or_create(session, user_id)
            await session.execute(
                update(UserQuota)
                .where(UserQuota.user_id == user_id)
                .values(
                    free_translations=UserQuota.free_translations + amount,
                    updated_at=datetime.utcnow(),
                )
            )
            await session.commit()
        logger.info("平台额度赠送: user=%s +%d（%s）", user_id, amount, reason)
