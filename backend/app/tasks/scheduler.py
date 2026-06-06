import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def fetch_featured_papers_job():
    """定时任务：从 arXiv 拉取最新论文并存储。"""
    from app.db.database import AsyncSessionLocal
    from app.services.featured_paper_service import fetch_and_store_featured_papers

    logger.info("[Scheduler] Starting daily featured papers fetch...")
    try:
        async with AsyncSessionLocal() as db:
            count = await fetch_and_store_featured_papers(db)
            logger.info("[Scheduler] Fetched and stored %d new featured papers", count)
    except Exception as e:
        logger.error("[Scheduler] Failed to fetch featured papers: %s", e, exc_info=True)


def start_scheduler():
    """启动 APScheduler，添加每天凌晨 2 点的定时任务。"""
    if scheduler.running:
        logger.warning("[Scheduler] already running, skipping")
        return

    trigger = CronTrigger(hour=2, minute=0)
    scheduler.add_job(
        fetch_featured_papers_job,
        trigger=trigger,
        id="fetch_featured_papers",
        name="Fetch daily featured papers from arXiv",
        replace_existing=True,
        misfire_grace_time=3600,  # 延迟 1 小时内仍执行
    )
    scheduler.start()
    logger.info("[Scheduler] started, next run at 02:00 daily")


def stop_scheduler():
    """停止调度器。"""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("[Scheduler] stopped")
