"""
Skills/Hooks 系统引导模块

在不修改 main.py 的情况下注册技能/钩子路由。
"""

import asyncio
import logging

from fastapi import FastAPI

logger = logging.getLogger(__name__)


def init_skills(app: FastAPI) -> None:
    """注册 Skills/Hooks 路由并确保数据库表存在。

    Args:
        app: FastAPI 应用实例
    """
    from app.skills.router import router
    from app.skills.models import Skill, Hook  # noqa: F401

    app.include_router(router, prefix="/api/v1")

    # 确保数据库表存在
    from app.db.database import AlibabaBase, alibaba_engine

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(_ensure_tables())
        else:
            loop.run_until_complete(_ensure_tables())
    except RuntimeError:
        asyncio.run(_ensure_tables())

    # 安装预置技能
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(_install_presets())
        else:
            loop.run_until_complete(_install_presets())
    except RuntimeError:
        asyncio.run(_install_presets())

    logger.info("Skills/Hooks system initialized: routes registered, presets installed")


async def _ensure_tables():
    """创建技能/钩子相关数据库表"""
    from app.db.database import AlibabaBase, alibaba_engine
    async with alibaba_engine.begin() as conn:
        await conn.run_sync(AlibabaBase.metadata.create_all)
    logger.info("Skills/Hooks tables ensured")


async def _install_presets():
    """安装预置技能"""
    from app.db.database import AlibabaSessionLocal
    from app.skills.services import SkillService

    async with AlibabaSessionLocal() as db:
        count = await SkillService.install_presets(db)
        if count:
            logger.info("Installed %d preset skills on startup", count)
