import asyncio
import logging

# 日志必须在其他 app 模块导入前配置完成（stdout + 按天轮转文件，见 logging_config.py）
from app.core.logging_config import mask_db_url, setup_logging

setup_logging()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.request_context import register as register_request_context
from app.routers import health, auth, users, literature, ai_engine, translate, tasks, note, tag, search, stats, presentation, announcement, folder, upload, admin, storage, check_in, invitation, tutorial, layout_analysis, feedback, featured_paper
from app.routers.client_logs import router as client_logs_router
from app.argument.router import router as argument_router
from app.skills.router import router as skills_router
from app.export.router import router as export_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

# 请求追踪（request_id 贯穿日志 + access 日志 + 全局 500 兜底）
register_request_context(app)


@app.on_event("startup")
async def startup_event():
    # 打印数据库连接地址（密码脱敏），方便与定时脚本日志对比
    from app.core.config import settings as app_settings
    logging.getLogger(__name__).info(
        "[Startup] 腾讯云数据库地址: %s", mask_db_url(app_settings.DATABASE_URL_FINAL)
    )
    logging.getLogger(__name__).info(
        "[Startup] 阿里云数据库地址: %s", mask_db_url(app_settings.LOCAL_DATABASE_URL_FINAL)
    )

    from app.core.ai_providers.provider_registry import AIProviderRegistry
    AIProviderRegistry.bootstrap()

    try:
        from app.services.layout_analysis_service import layout_analysis_service
        _logger = logging.getLogger(__name__)
        _logger.info("Preloading ONNX layout model...")
        layout_analysis_service.load_model()
        _logger.info("ONNX layout model preloaded (backend=%s)", layout_analysis_service.backend)
    except FileNotFoundError:
        pass
    except Exception:
        logging.getLogger(__name__).warning("ONNX layout model preload skipped", exc_info=True)

    # 启动每日精选论文定时任务 + 立即拉取一次
    try:
        from app.tasks.scheduler import start_scheduler, run_initial_fetch
        start_scheduler()
        # 后台立即拉取一次（不阻塞启动）
        asyncio.create_task(run_initial_fetch())
    except Exception:
        logging.getLogger(__name__).warning("Featured papers scheduler failed to start", exc_info=True)

    # 确保翻译文件记录表存在（新部署时 init_db.py 可能未运行）
    try:
        from app.db.database import tencent_engine, TencentBase
        async with tencent_engine.begin() as conn:
            await conn.run_sync(TencentBase.metadata.create_all)
    except Exception:
        logging.getLogger(__name__).warning("TencentBase create_all failed", exc_info=True)

    # 确保免费额度/召回邮件等新表存在（用户库）。
    # 生产若忘记跑 init_db.py / 迁移 006，这里会自动补建，避免线上 500
    try:
        from app.db.database import alibaba_engine, AlibabaBase
        from app.models.user_quota import UserQuota
        from app.models.recall_email_log import RecallEmailLog
        from sqlalchemy import text as _sa_text
        async with alibaba_engine.begin() as conn:
            await conn.run_sync(
                AlibabaBase.metadata.create_all,
                tables=[UserQuota.__table__, RecallEmailLog.__table__],
            )
            # 列自愈：create_all 不给已存在的表加新列
            await conn.execute(_sa_text(
                "ALTER TABLE user_quotas "
                "ADD COLUMN IF NOT EXISTS prefer_free BOOLEAN NOT NULL DEFAULT FALSE"
            ))
    except Exception:
        logging.getLogger(__name__).warning("Alibaba new tables create_all failed", exc_info=True)

    # 平台 AI 配置种子（幂等：后台「系统配置」出现 platform_* 四项，管理员可视化修改）
    try:
        from app.services.platform_config_service import PlatformConfigService
        await PlatformConfigService.ensure_seeded()
    except Exception:
        logging.getLogger(__name__).warning("Platform config seed failed", exc_info=True)

    # 内置教程种子（幂等：写入「免费获取 AI Key」指南，教程页不再是空壳）
    try:
        from app.tasks.tutorial_seed import ensure_seed_tutorials
        await ensure_seed_tutorials()
    except Exception:
        logging.getLogger(__name__).warning("Tutorial seed failed", exc_info=True)

    # 清理重启后遗留的 stale task（跨进程/重启）
    try:
        from app.utils.task_store import task_store
        await task_store.cleanup_stale_tasks()
    except Exception:
        logging.getLogger(__name__).warning("Task cleanup failed", exc_info=True)

    # 初始化 Redis 连接
    try:
        from app.core.redis import redis_manager
        await redis_manager.initialize()
    except Exception:
        logging.getLogger(__name__).warning("Redis init failed", exc_info=True)


@app.on_event("shutdown")
async def shutdown_event():
    try:
        from app.core.redis import redis_manager
        await redis_manager.close()
    except Exception:
        logging.getLogger(__name__).warning("Redis shutdown failed", exc_info=True)


# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health.router, prefix=settings.API_V1_STR)
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(users.router, prefix=f"{settings.API_V1_STR}/users", tags=["users"])
app.include_router(literature.router, prefix=f"{settings.API_V1_STR}/literatures", tags=["literatures"])
app.include_router(upload.router, prefix=settings.API_V1_STR, tags=["upload"])
app.include_router(ai_engine.router, prefix=f"{settings.API_V1_STR}/ai-engines", tags=["ai-engines"])
app.include_router(translate.router, prefix=f"{settings.API_V1_STR}/translate", tags=["translate"])
app.include_router(tasks.router, prefix=settings.API_V1_STR, tags=["tasks"])
app.include_router(note.router, prefix=f"{settings.API_V1_STR}/notes", tags=["notes"])
app.include_router(tag.router, prefix=settings.API_V1_STR, tags=["tags"])
app.include_router(search.router, prefix=settings.API_V1_STR, tags=["search"])
app.include_router(stats.router, prefix=settings.API_V1_STR, tags=["stats"])
app.include_router(presentation.router, prefix=settings.API_V1_STR, tags=["presentations"])
app.include_router(announcement.router, prefix=settings.API_V1_STR, tags=["announcements"])
app.include_router(folder.router, prefix=f"{settings.API_V1_STR}/folders", tags=["folders"])
app.include_router(admin.router, prefix=settings.API_V1_STR, tags=["admin"])
app.include_router(storage.router, prefix=f"{settings.API_V1_STR}/storage", tags=["storage"])
app.include_router(check_in.router, prefix=f"{settings.API_V1_STR}/check-in", tags=["check-in"])
app.include_router(invitation.router, prefix=f"{settings.API_V1_STR}/invitations", tags=["invitations"])
app.include_router(tutorial.router, prefix=settings.API_V1_STR, tags=["tutorials"])
app.include_router(layout_analysis.router, prefix=f"{settings.API_V1_STR}/layout-analysis", tags=["layout-analysis"])
app.include_router(feedback.router, prefix=f"{settings.API_V1_STR}/feedback", tags=["feedback"])
app.include_router(featured_paper.router, prefix=settings.API_V1_STR, tags=["featured"])
app.include_router(client_logs_router, prefix=settings.API_V1_STR)
app.include_router(argument_router, prefix=settings.API_V1_STR)
app.include_router(skills_router, prefix=settings.API_V1_STR)
app.include_router(export_router, prefix=settings.API_V1_STR)


@app.get("/")
async def root():
    return {"message": "Welcome to InkLight API"}
