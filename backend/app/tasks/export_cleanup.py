"""
定时任务：清理过期的导出文件和记录

此模块可被 scheduler 引用，也可单独运行：
    python -m app.tasks.export_cleanup

如果使用 run_with_export.py，清理任务会自动注册（15 分钟间隔）。
"""

import asyncio
import logging

logger = logging.getLogger(__name__)


async def cleanup_expired_exports():
    """清理所有过期导出文件（供 APScheduler 调用）"""
    from app.db.database import AsyncSessionLocal
    from app.export.exporter_service import ExportService

    logger.info("[Export Cleanup] Starting cleanup of expired exports...")
    try:
        async with AsyncSessionLocal() as db:
            count = await ExportService.cleanup_expired_files(db)
            if count:
                logger.warning("[Export Cleanup] Removed %d expired export files", count)
            else:
                logger.info("[Export Cleanup] No expired files to clean")
    except Exception as e:
        logger.error("[Export Cleanup] Failed: %s", e, exc_info=True)


def run_cleanup_sync():
    """同步入口（用于命令行调用）"""
    asyncio.run(cleanup_expired_exports())


if __name__ == "__main__":
    run_cleanup_sync()
