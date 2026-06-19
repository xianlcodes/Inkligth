"""
Redis 连接管理器

提供应用级 Redis 单例，启动时连接、关闭时断开。
所有操作都有优雅降级 —— Redis 不可用时自动降级为进程内内存缓存。
"""

import hashlib
import time
import logging
from typing import Optional

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisManager:
    """Redis 连接管理器（带内存兜底缓存）"""

    def __init__(self):
        self._redis: Optional[aioredis.Redis] = None
        self._available = False
        # 内存兜底缓存：{key: (expire_at, value)}
        self._memory_cache: dict[str, tuple[float, str]] = {}

    # ── 生命周期 ──

    async def initialize(self):
        """应用启动时初始化 Redis 连接"""
        if self._redis is not None:
            return
        try:
            url = settings.REDIS_URL_FINAL
            self._redis = aioredis.from_url(
                url,
                decode_responses=True,
                socket_connect_timeout=3,
                socket_timeout=3,
                retry_on_timeout=False,
            )
            await self._redis.ping()
            self._available = True
            logger.info("Redis connected: %s", url.split("@")[-1] if "@" in url else url)
        except Exception as e:
            logger.info("Redis unavailable (%s) — using in-memory fallback cache", e)
            self._redis = None
            self._available = False

    async def close(self):
        """应用关闭时断开 Redis 连接"""
        if self._redis:
            try:
                await self._redis.aclose()
            except Exception as e:
                logger.warning("Redis close error: %s", e)
            self._redis = None
            self._available = False
        self._memory_cache.clear()

    @property
    def available(self) -> bool:
        return self._available

    # ── 缓存操作 ──

    async def get(self, key: str) -> Optional[str]:
        if self._redis:
            try:
                return await self._redis.get(key)
            except Exception as e:
                logger.warning("Redis get(%s) failed: %s", key[:40], e)
                return None

        # 内存兜底
        now = time.monotonic()
        entry = self._memory_cache.get(key)
        if entry is None:
            return None
        expire_at, value = entry
        if now > expire_at:
            self._memory_cache.pop(key, None)
            return None
        return value

    async def setex(self, key: str, ttl: int, value: str):
        if self._redis:
            try:
                await self._redis.setex(key, ttl, value)
                return
            except Exception as e:
                logger.warning("Redis setex(%s) failed: %s", key[:40], e)

        # 内存兜底
        self._memory_cache[key] = (time.monotonic() + ttl, value)

    async def delete(self, key: str):
        if self._redis:
            try:
                await self._redis.delete(key)
            except Exception as e:
                logger.warning("Redis delete(%s) failed: %s", key[:40], e)
        self._memory_cache.pop(key, None)

    # ── Key 生成 ──

    @staticmethod
    def cache_key(*parts: str) -> str:
        """生成统一的缓存 key: sha256(parts)"""
        raw = "|".join(parts)
        return hashlib.sha256(raw.encode()).hexdigest()

    @staticmethod
    def cache_key_ai_response(user_id: str, message: str, context: str, *extra: str) -> str:
        """AI 响应缓存 key"""
        return "ai:" + RedisManager.cache_key(user_id, message.strip(), context.strip(), *extra)


redis_manager = RedisManager()
