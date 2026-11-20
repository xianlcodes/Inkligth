"""
双数据库连接配置

- TencentBase / tencent_session: 腾讯云远程 PostgreSQL（文献相关数据）
- AlibabaBase / alibaba_session: 阿里云本地 PostgreSQL（用户相关数据）
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import settings

# ── 腾讯云远程数据库（文献相关：literatures, notes, tags, ...） ──
# 池参数显式配置：默认 pool_size=5+overflow=10 在 SSE 流式 + 后台任务并发下
# 会被打满（2026-11-20 事故：QueuePool limit reached，全站登录 500）。
tencent_engine = create_async_engine(
    settings.DATABASE_URL_FINAL,
    echo=False,
    future=True,
    pool_pre_ping=True,
    pool_recycle=1800,   # 跨云链路缩短回收周期，防中间设备掐断空闲连接
    pool_size=10,        # 常驻连接数
    max_overflow=20,     # 峰值额外连接，合计上限 30
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
    pool_recycle=1800,
    pool_size=10,
    max_overflow=20,
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
