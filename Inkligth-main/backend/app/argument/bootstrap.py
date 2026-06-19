"""
Argument Companion 启动注册

在主应用中注册路由、确保数据库表创建。
"""

import asyncio
import logging

from fastapi import FastAPI

logger = logging.getLogger(__name__)


def init_argument(app: FastAPI) -> None:
    """在 FastAPI 应用中注册 Argument Companion 模块

    调用方式:
        from app.argument.bootstrap import init_argument
        init_argument(app)
    """
    try:
        from app.argument.router import router as argument_router
        from app.db.database import TencentBase, tencent_engine

        # 注册路由
        app.include_router(argument_router, prefix="/api/v1")

        # 确保数据库表存在（异步引擎需用 run_sync）
        async def _create_tables():
            async with tencent_engine.begin() as conn:
                await conn.run_sync(TencentBase.metadata.create_all)

        asyncio.create_task(_create_tables())

        logger.info("Argument Companion module initialized (routes + tables)")

    except Exception as e:
        msg = "Argument Companion init failed (non-fatal): %s. Routes and tables may need manual setup."
        logger.warning(msg, e)
