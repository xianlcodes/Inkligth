"""
定时任务：清理过期的原位 PDF 翻译文件和数据库记录
"""

import logging
import os

logger = logging.getLogger(__name__)


async def cleanup_expired_pdf_translations():
    """清理所有过期的 PdfTranslation 记录和对应的磁盘文件（供 APScheduler 调用）"""
    from datetime import datetime as dt
    from app.db.database import AsyncSessionLocal
    from app.models.pdf_translation import PdfTranslation
    from sqlalchemy import select, delete

    logger.info("[PdfTranslation Cleanup] Starting cleanup of expired records...")
    try:
        async with AsyncSessionLocal() as db:
            # 查找过期记录
            result = await db.execute(
                select(PdfTranslation).where(PdfTranslation.expires_at <= dt.utcnow())
            )
            records = result.scalars().all()

            if not records:
                logger.info("[PdfTranslation Cleanup] No expired records to clean")
                return

            deleted_count = 0
            for rec in records:
                # 删除磁盘文件
                if rec.file_path and os.path.exists(rec.file_path):
                    try:
                        os.remove(rec.file_path)
                        logger.info("Deleted expired PDF translation file: %s", rec.file_path)
                    except OSError as e:
                        logger.warning("Failed to delete file %s: %s", rec.file_path, e)

            # 批量删除数据库记录
            result = await db.execute(
                delete(PdfTranslation).where(PdfTranslation.expires_at <= dt.utcnow())
            )
            deleted_count = result.rowcount
            await db.commit()

            logger.warning(
                "[PdfTranslation Cleanup] Removed %d expired PDF translation records",
                deleted_count,
            )
    except Exception as e:
        logger.error("[PdfTranslation Cleanup] Failed: %s", e, exc_info=True)


def run_cleanup_sync():
    """同步入口（用于命令行调用）"""
    import asyncio
    asyncio.run(cleanup_expired_pdf_translations())


if __name__ == "__main__":
    run_cleanup_sync()
