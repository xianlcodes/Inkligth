"""
导出系统引导模块

在不修改 main.py 的情况下注册导出路由。
提供 init_export() 函数，由 run_with_export.py 在启动时调用。
"""

import logging

from fastapi import FastAPI

logger = logging.getLogger(__name__)


def init_export(app: FastAPI) -> None:
    """注册导出路由并确保数据库表存在。

    在 FastAPI 应用上挂载 /api/v1/export/* 路由。

    Args:
        app: FastAPI 应用实例（由现有 main.py 创建）
    """
    from app.export.router import router
    from app.export.models import ExportRecord  # noqa: F401 - 确保 SQLAlchemy 发现模型

    app.include_router(router, prefix="/api/v1")

    # 确保导出文件目录存在
    from app.export.exporter_service import _ensure_export_dir
    _ensure_export_dir()

    # 确保数据库表存在（create_all 是幂等的，仅创建不存在的表）
    from app.db.database import Base, engine
    import asyncio

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(_ensure_tables())
        else:
            loop.run_until_complete(_ensure_tables())
    except RuntimeError:
        # 没有事件循环时同步执行
        import asyncio
        asyncio.run(_ensure_tables())

    logger.info("Export system initialized: routes registered, tables ensured")


async def _ensure_tables():
    """创建导出相关数据库表（如果不存在）"""
    from app.db.database import Base, engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Export tables ensured")
