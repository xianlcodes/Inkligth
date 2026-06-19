"""
双数据库连接配置

- TencentBase / tencent_session: 腾讯云远程 PostgreSQL（文献相关数据）
- AlibabaBase / alibaba_session: 阿里云本地 PostgreSQL（用户相关数据）
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import settings

# ── 腾讯云远程数据库（文献相关：literatures, notes, tags, ...） ──
tencent_engine = create_async_engine(
    settings.DATABASE_URL_FINAL,
    echo=False,
    future=True,
    pool_pre_ping=True,
    pool_recycle=3600,
)
TencentSessionLocal = async_sessionmaker(
    bind=tencent_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)
TencentBase = declarative_base()


# ── 阿里云本地数据库（用户相关：users, refresh_tokens, ai_engines, ...） ──
alibaba_engine = create_async_engine(
    settings.LOCAL_DATABASE_URL_FINAL,
    echo=False,
    future=True,
    pool_pre_ping=True,
    pool_recycle=3600,
)
AlibabaSessionLocal = async_sessionmaker(
    bind=alibaba_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)
AlibabaBase = declarative_base()


# ── 兼容旧代码：保持 Base / engine / get_db 指向腾讯云（默认行为） ──
Base = TencentBase
engine = tencent_engine
AsyncSessionLocal = TencentSessionLocal
async_session_factory = TencentSessionLocal


async def get_db():
    """(已废弃) 保留兼容别名，等价于 get_tencent_db()"""
    async with TencentSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_tencent_db():
    """获取腾讯云远程数据库会话（文献相关数据）"""
    async with TencentSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_user_db():
    """获取阿里云本地数据库会话（用户相关数据）"""
    async with AlibabaSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
