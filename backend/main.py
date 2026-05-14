from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.routers import health, auth, users, literature, ai_engine, translate, tasks, note, tag, search, stats, presentation, announcement, folder, upload

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)


@app.on_event("startup")
async def startup_event():
    from app.core.ai_providers.provider_registry import AIProviderRegistry
    AIProviderRegistry.bootstrap()


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


@app.get("/")
async def root():
    return {"message": "Welcome to InkLight API"}
