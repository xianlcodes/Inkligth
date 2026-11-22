"""平台免费翻译额度服务。

额度规则（2026-11 定稿）：
- 每个用户注册即送 settings.PLATFORM_FREE_TRANSLATIONS 次「PDF 文献翻译」额度
  （默认 1 次），懒创建：首次查询/扣减时自动发放，存量老用户同样覆盖；
- 仅 PDF 原位翻译任务消耗额度；用户自配 AI 引擎时不消耗（无限量）；
- 扣减用 UPDATE ... WHERE free_translations > 0 保证并发下不会超发；
- 任务因 AI 失败而中止时返还额度；用户主动取消不返还（已发生的调用无法撤回）。
"""
import asyncio
import logging
from datetime import datetime

from sqlalchemy import update
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.db.database import AlibabaSessionLocal
from app.models.user_quota import UserQuota

logger = logging.getLogger(__name__)

# 单 worker 部署（uvicorn --workers 1）：进程内锁让扣减完全串行化。
# RETURNING 校验是第二层保险：即使未来扩多实例，也能通过
# 「返回值必须 >= 0」拦截任何快照语义差异导致的超发。
_consume_lock = asyncio.Lock()


class QuotaService:
    @staticmethod
    async def _get_or_create(session, user_id: str) -> UserQuota:
        """取额度记录；不存在则按平台配置赠送额度懒创建（幂等，防并发重复插入）。"""
        quota = await session.get(UserQuota, user_id)
        if quota:
            return quota
        from app.services.platform_config_service import PlatformConfigService
        cfg = await PlatformConfigService.resolve()
        quota = UserQuota(
            user_id=user_id,
            free_translations=cfg["free_translations"],
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
        """返回 {remaining, used, total_granted}。"""
        async with AlibabaSessionLocal() as session:
            quota = await QuotaService._get_or_create(session, user_id)
            return {
                "remaining": max(quota.free_translations, 0),
                "used": quota.used_count,
                "total_granted": max(quota.free_translations, 0) + quota.used_count,
            }

    @staticmethod
    async def remaining(user_id: str) -> int:
        summary = await QuotaService.get_summary(user_id)
        return summary["remaining"]

    @staticmethod
    async def consume(user_id: str) -> bool:
        """原子扣减 1 次。返回 False 表示额度不足。

        双保险：
        1. 进程内 _consume_lock 串行化（生产为单 worker 部署）；
        2. UPDATE ... RETURNING free_translations，校验扣减后余额 >= 0——
           若任何数据库快照语义差异导致扣成负数，回滚并视为额度不足。
        """
        async with _consume_lock:
            async with AlibabaSessionLocal() as session:
                await QuotaService._get_or_create(session, user_id)
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
                if row is None or row[0] < 0:
                    # 额度不足（或防御性拦截负值）：回滚本次写操作
                    await session.rollback()
                    if row is not None and row[0] < 0:
                        await session.execute(
                            update(UserQuota)
                            .where(UserQuota.user_id == user_id)
                            .values(free_translations=0)
                        )
                        await session.commit()
                        logger.error("检测到额度负值并已钳制为 0: user=%s", user_id)
                    return False
                await session.commit()
                logger.info(
                    "平台额度扣减: user=%s 剩余=%d", user_id, row[0]
                )
                return True

    @staticmethod
    async def refund(user_id: str) -> None:
        """返还 1 次（任务因 AI 失败中止时调用）。"""
        async with AlibabaSessionLocal() as session:
            await QuotaService._get_or_create(session, user_id)
            await session.execute(
                update(UserQuota)
                .where(UserQuota.user_id == user_id)
                .values(
                    free_translations=UserQuota.free_translations + 1,
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
