import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

# 使用北京时区，确保"凌晨 2 点"是北京时间
SCHEDULER_TIMEZONE = "Asia/Shanghai"

scheduler = AsyncIOScheduler(timezone=SCHEDULER_TIMEZONE)


async def fetch_featured_papers_job():
    """定时任务：从 arXiv 拉取最新论文并存储。"""
    from app.db.database import AsyncSessionLocal
    from app.services.featured_paper_service import fetch_and_store_featured_papers

    logger.info("[Scheduler] Starting daily featured papers fetch...")
    try:
        async with AsyncSessionLocal() as db:
            count = await fetch_and_store_featured_papers(db)
            logger.warning("[Scheduler] Fetched and stored %d new featured papers", count)
    except Exception as e:
        logger.error("[Scheduler] Failed to fetch featured papers: %s", e, exc_info=True)


async def run_initial_fetch():
    """启动后立即执行一次拉取，避免重启后当天无数据。"""
    from app.db.database import AsyncSessionLocal
    from app.services.featured_paper_service import fetch_and_store_featured_papers

    logger.warning("[Scheduler] Running initial featured papers fetch on startup...")
    try:
        async with AsyncSessionLocal() as db:
            count = await fetch_and_store_featured_papers(db)
            logger.warning("[Scheduler] Initial fetch complete: %d papers stored", count)
    except Exception as e:
        logger.error("[Scheduler] Initial fetch failed: %s", e, exc_info=True)


def start_scheduler():
    """启动 APScheduler，添加每天北京时间凌晨 2 点的定时任务。

    注意：第一次触发要等到下一个 02:00（北京时间），所以启动后应配合
    run_initial_fetch() 立即拉取一次，避免重启当天无数据。
    """
    if scheduler.running:
        logger.warning("[Scheduler] already running, skipping")
        return

    trigger = CronTrigger(hour=2, minute=0, timezone=SCHEDULER_TIMEZONE)
    scheduler.add_job(
        fetch_featured_papers_job,
        trigger=trigger,
        id="fetch_featured_papers",
        name="Fetch daily featured papers from arXiv",
        replace_existing=True,
        misfire_grace_time=3600,  # 延迟 1 小时内仍执行
    )
    # 每天凌晨 3 点清理过期的 PDF 翻译文件
    from app.tasks.pdf_translation_cleanup import cleanup_expired_pdf_translations
    cleanup_trigger = CronTrigger(hour=3, minute=0, timezone=SCHEDULER_TIMEZONE)
    scheduler.add_job(
        cleanup_expired_pdf_translations,
        trigger=cleanup_trigger,
        id="cleanup_expired_pdf_translations",
        name="Cleanup expired PDF translations",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    scheduler.start()
    logger.warning("[Scheduler] started, next run at 02:00 (Asia/Shanghai)")


def stop_scheduler():
    """停止调度器。"""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.warning("[Scheduler] stopped")
