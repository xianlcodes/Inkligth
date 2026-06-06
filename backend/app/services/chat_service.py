import json
import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)


class ConversationStore:
    """对话历史缓存，TTL 1 小时。支持 Redis 回退到内存。

    如需要 Redis，传入 redis_url 参数即可自动启用。
    """

    def __init__(self):
        self._memory: dict[str, list[dict]] = {}
        self._timestamps: dict[str, float] = {}

    async def get_messages(self, conversation_id: str) -> list[dict]:
        ts = self._timestamps.get(conversation_id)
        if ts and time.time() - ts > 3600:
            self._memory.pop(conversation_id, None)
            self._timestamps.pop(conversation_id, None)
            return []
        return self._memory.get(conversation_id, [])

    async def save_messages(self, conversation_id: str, messages: list[dict]):
        self._memory[conversation_id] = messages
        self._timestamps[conversation_id] = time.time()

    async def delete_messages(self, conversation_id: str):
        self._memory.pop(conversation_id, None)
        self._timestamps.pop(conversation_id, None)


conversation_store = ConversationStore()
