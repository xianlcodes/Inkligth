#!/usr/bin/env python3
"""
InkLight 后端启动脚本（带导出系统）

本入口在现有 main.py 的基础上，自动加载导出系统路由。
使用方法：
    python run_with_export.py

与原始 main.py 的区别：
    - 自动注册 /api/v1/export/* 路由
    - 自动注册 /api/v1/skills 和 /api/v1/hooks 路由
    - 自动创建对应的数据库表
    - 自动创建导出文件目录
    - 自动安装预置技能
    - 定期清理过期导出文件

注意事项：
    - 需要 python-docx 库（已内置在 requirements.txt 之外）
    - LaTeX/PDF 导出需要额外安装 Pandoc + tectonic/latexmk
"""

import asyncio
import logging

logger = logging.getLogger(__name__)

# 1. 先导入并启动原始应用
from main import app  # noqa: E402  -- 从原始 main.py 获取 FastAPI 实例

# 2. 注册导出系统路由
from app.export.bootstrap import init_export  # noqa: E402
init_export(app)

# 3. 注册技能/钩子系统路由
from app.skills.bootstrap import init_skills  # noqa: E402
init_skills(app)

# 4. 注册论文评审系统路由
try:
    from app.argument.bootstrap import init_argument  # noqa: E402
    init_argument(app)
except Exception:
    logger.warning("Argument Companion init failed (non-critical)")

# 5. 启动清理定时任务
try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.interval import IntervalTrigger
    from app.export.exporter_service import ExportService
    from app.db.database import AsyncSessionLocal

    scheduler = AsyncIOScheduler()
    cleanup_trigger = IntervalTrigger(minutes=15)

    async def cleanup_job():
        try:
            async with AsyncSessionLocal() as db:
                count = await ExportService.cleanup_expired_files(db)
                if count:
                    logger.info("Export cleanup: removed %d expired files", count)
        except Exception:
            logger.exception("Export cleanup job failed")

    scheduler.add_job(
        cleanup_job,
        trigger=cleanup_trigger,
        id="export_cleanup",
        name="Clean expired export files",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Export cleanup scheduler started (interval: 15 min)")
except Exception:
    logger.warning("Export cleanup scheduler failed to start (non-critical)")

# 6. 使用原始的 main 模块入口点
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
