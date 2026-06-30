import asyncio
import logging
import sys

# 清除所有默认日志处理器，防止重复输出
root_logger = logging.getLogger()
for handler in root_logger.handlers[:]:
    root_logger.removeHandler(handler)

# 配置自定义日志格式（仅显示WARNING及以上）
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s %(levelname)s:%(name)s:%(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)]
)

# 全面抑制SQLAlchemy日志（所有子模块）
sqlalchemy_logger = logging.getLogger("sqlalchemy")
sqlalchemy_logger.setLevel(logging.WARNING)
sqlalchemy_logger.propagate = False

# 抑制uvicorn访问日志
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("uvicorn").setLevel(logging.WARNING)

# 抑制其他日志
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("app.core.ai_providers.provider_registry").setLevel(logging.WARNING)
logging.getLogger("app.services.layout_analysis_service").setLevel(logging.WARNING)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.routers import health, auth, users, literature, ai_engine, translate, tasks, note, tag, search, stats, presentation, announcement, folder, upload, admin, storage, check_in, invitation, tutorial, layout_analysis, feedback, featured_paper
from app.argument.router import router as argument_router
from app.skills.router import router as skills_router
from app.export.router import router as export_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)


@app.on_event("startup")
async def startup_event():
    # 打印数据库连接地址，方便与定时脚本日志对比
    from app.core.config import settings as app_settings
    logging.getLogger(__name__).warning(
        "[Startup] 腾讯云数据库地址: %s", app_settings.DATABASE_URL_FINAL
    )
    logging.getLogger(__name__).warning(
        "[Startup] 阿里云数据库地址: %s", app_settings.LOCAL_DATABASE_URL_FINAL
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
app.include_router(argument_router, prefix=settings.API_V1_STR)
app.include_router(skills_router, prefix=settings.API_V1_STR)
app.include_router(export_router, prefix=settings.API_V1_STR)


@app.get("/")
async def root():
    return {"message": "Welcome to InkLight API"}
