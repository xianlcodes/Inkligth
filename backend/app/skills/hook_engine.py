"""
钩子引擎 - 管理生命周期钩子的注册和执行
"""

import logging
import time
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.skills.models import Hook

logger = logging.getLogger(__name__)


class HookPoint(str, Enum):
    PRE_TOOL_USE = "pre_tool_use"
    POST_TOOL_USE = "post_tool_use"
    ON_ERROR = "on_error"


class HookResult(BaseModel):
    passed: bool = True
    blocked: bool = False
    reason: str = ""
    metadata: dict[str, Any] = {}


class _RateLimitState:
    """简单的内存速率限制状态"""
    def __init__(self):
        self.window_start: float = 0.0
        self.call_count: int = 0


class HookEngine:
    """钩子执行引擎"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._rate_limit_states: dict[str, _RateLimitState] = {}

    async def execute(
        self,
        point: HookPoint,
        context: dict[str, Any],
    ) -> HookResult:
        """执行指定钩子点的所有激活钩子

        Args:
            point: 钩子点
            context: 上下文信息（至少包含 user_id）

        Returns:
            HookResult - 包含是否通过检查等信息
        """
        hooks = await self._get_active_hooks(point)
        if not hooks:
            return HookResult()

        # 按优先级排序
        hooks.sort(key=lambda h: h.priority, reverse=False)

        result = HookResult()
        for hook in hooks:
            hook_result = await self._execute_single(hook, context)
            if hook_result.blocked:
                return hook_result
            if not hook_result.passed:
                result = hook_result
            # 合并元数据
            result.metadata[hook.name] = hook_result.metadata

        return result

    async def execute_pre(
        self,
        user_id: str,
        action: str = "ai_chat",
        context: Optional[dict[str, Any]] = None,
    ) -> HookResult:
        """PRE_TOOL_USE 快捷方法"""
        ctx = {
            "user_id": user_id,
            "action": action,
            "timestamp": time.time(),
            **(context or {}),
        }
        return await self.execute(HookPoint.PRE_TOOL_USE, ctx)

    async def execute_post(
        self,
        user_id: str,
        action: str = "ai_chat",
        context: Optional[dict[str, Any]] = None,
        result_data: Optional[dict[str, Any]] = None,
    ):
        """POST_TOOL_USE 快捷方法"""
        ctx = {
            "user_id": user_id,
            "action": action,
            "timestamp": time.time(),
            "result": result_data or {},
            **(context or {}),
        }
        await self.execute(HookPoint.POST_TOOL_USE, ctx)

    async def execute_error(
        self,
        user_id: str,
        action: str = "ai_chat",
        error: Optional[Exception] = None,
        context: Optional[dict[str, Any]] = None,
    ):
        """ON_ERROR 快捷方法"""
        ctx = {
            "user_id": user_id,
            "action": action,
            "timestamp": time.time(),
            "error": str(error) if error else "unknown",
            **(context or {}),
        }
        await self.execute(HookPoint.ON_ERROR, ctx)

    async def _get_active_hooks(self, point: HookPoint) -> list[Hook]:
        """获取指定钩子点的所有激活钩子"""
        result = await self.db.execute(
            select(Hook).where(
                Hook.is_active == True,
                Hook.hook_point == point.value,
            )
        )
        return list(result.scalars().all())

    async def _execute_single(self, hook: Hook, context: dict) -> HookResult:
        """执行单个钩子"""
        action_type = hook.action_type
        config = hook.config or {}

        try:
            if action_type == "log":
                return self._handle_log(hook, context, config)
            elif action_type == "throttle":
                return await self._handle_throttle(hook, context, config)
            elif action_type == "filter":
                return self._handle_filter(hook, context, config)
            elif action_type == "custom":
                return HookResult(passed=True, metadata={"note": "Custom hooks not implemented"})
            else:
                logger.warning("Unknown hook action_type: %s", action_type)
                return HookResult()
        except Exception as e:
            logger.error("Hook %s execution failed: %s", hook.name, e, exc_info=True)
            return HookResult(passed=True, metadata={"error": str(e)})

    def _handle_log(self, hook: Hook, context: dict, config: dict) -> HookResult:
        """日志记录钩子"""
        level = config.get("level", "info")
        fields = config.get("fields", ["user_id", "action"])
        log_data = {f: context.get(f) for f in fields}
        log_fn = {"info": logger.info, "warning": logger.warning, "error": logger.error}.get(
            level, logger.info
        )
        log_fn("[Hook:%s] %s", hook.name, log_data)
        return HookResult(metadata={"logged": True, "level": level})

    async def _handle_throttle(self, hook: Hook, context: dict, config: dict) -> HookResult:
        """速率限制钩子"""
        max_calls = config.get("max_calls", 100)
        window_seconds = config.get("window_seconds", 60)
        user_id = context.get("user_id", "global")

        state = self._rate_limit_states.setdefault(
            f"{hook.id}:{user_id}", _RateLimitState()
        )

        now = time.time()
        if now - state.window_start > window_seconds:
            state.window_start = now
            state.call_count = 0

        state.call_count += 1

        if state.call_count > max_calls:
            logger.warning(
                "[Hook:%s] Rate limit exceeded for user %s: %d calls in %.0fs",
                hook.name, user_id, state.call_count, window_seconds,
            )
            return HookResult(
                passed=False,
                blocked=True,
                reason=f"Rate limit exceeded: {max_calls} calls per {window_seconds}s",
                metadata={"call_count": state.call_count, "limit": max_calls},
            )

        return HookResult(
            metadata={"call_count": state.call_count, "limit": max_calls}
        )

    def _handle_filter(self, hook: Hook, context: dict, config: dict) -> HookResult:
        """内容过滤钩子"""
        blocked_keywords = config.get("blocked_keywords", [])
        user_id = context.get("user_id", "")
        action = context.get("action", "")

        # 检查 user_id 是否包含关键词
        for keyword in blocked_keywords:
            if keyword in user_id or keyword in action:
                logger.warning(
                    "[Hook:%s] Blocked by keyword '%s' for user %s",
                    hook.name, keyword, user_id,
                )
                return HookResult(
                    passed=False,
                    blocked=True,
                    reason=f"Blocked by keyword filter: {keyword}",
                )

        return HookResult()
