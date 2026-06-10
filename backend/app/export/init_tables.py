"""
独立数据库表初始化脚本

在现有数据库上创建导出系统所需的表（export_records）。

用法：
    python -m app.export.init_tables

说明：
    - 本脚本是幂等的，可重复运行
    - 如果使用 run_with_export.py，表会在启动时自动创建
    - 仅当需要手动创建表或迁移数据库时才需运行本脚本
"""

import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def init_export_tables():
    """创建导出系统所需的数据库表"""
    from app.db.database import Base, engine
    from app.export.models import ExportRecord  # noqa: F401 - 注册模型

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Export tables created successfully (if not existed)")


if __name__ == "__main__":
    asyncio.run(init_export_tables())
