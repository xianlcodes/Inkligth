"""
对话记录数据库存取服务

替代内存 ConversationStore，提供基于 PostgreSQL 的对话持久化。
"""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.models.conversation import Conversation, ConversationMessage

logger = logging.getLogger(__name__)

MAX_HISTORY = 20  # 保留最近 20 轮对话


class ConversationService:

    @staticmethod
    async def get_conversation(db: AsyncSession, conversation_id: str) -> Optional[Conversation]:
        result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def list_conversations(
        db: AsyncSession,
        user_id: str,
        type: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[int, list[Conversation]]:
        conditions = [Conversation.user_id == user_id]
        if type:
            conditions.append(Conversation.type == type)

        count_q = select(func.count()).select_from(Conversation).where(*conditions)
        total = (await db.execute(count_q)).scalar() or 0

        q = (
            select(Conversation)
            .where(*conditions)
            .order_by(desc(Conversation.updated_at))
            .offset(skip)
            .limit(limit)
        )
        items = list((await db.execute(q)).scalars().all())
        return total, items

    @staticmethod
    async def create_conversation(
        db: AsyncSession,
        user_id: str,
        title: str = "新对话",
        type: str = "writing",
        literature_id: Optional[str] = None,
    ) -> Conversation:
        conv = Conversation(
            user_id=user_id,
            title=title,
            type=type,
            literature_id=literature_id,
        )
        db.add(conv)
        await db.commit()
        await db.refresh(conv)
        logger.info("Conversation created: %s (type=%s)", conv.id, type)
        return conv

    @staticmethod
    async def update_title(db: AsyncSession, conversation_id: str, title: str) -> None:
        conv = await ConversationService.get_conversation(db, conversation_id)
        if conv:
            conv.title = title
            conv.updated_at = datetime.utcnow()
            await db.commit()

    @staticmethod
    async def delete_conversation(db: AsyncSession, conversation_id: str) -> bool:
        conv = await ConversationService.get_conversation(db, conversation_id)
        if not conv:
            return False
        await db.delete(conv)
        await db.commit()
        logger.info("Conversation deleted: %s", conversation_id)
        return True

    @staticmethod
    async def get_messages(
        db: AsyncSession,
        conversation_id: str,
        limit: int = MAX_HISTORY,
    ) -> list[ConversationMessage]:
        q = (
            select(ConversationMessage)
            .where(ConversationMessage.conversation_id == conversation_id)
            .order_by(ConversationMessage.created_at)
            .limit(limit)
        )
        result = await db.execute(q)
        return list(result.scalars().all())

    @staticmethod
    async def add_message(
        db: AsyncSession,
        conversation_id: str,
        role: str,
        content: str,
        context_text: Optional[str] = None,
    ) -> ConversationMessage:
        msg = ConversationMessage(
            conversation_id=conversation_id,
            role=role,
            content=content,
            context_text=context_text,
        )
        db.add(msg)

        # 更新对话的 updated_at 时间戳
        conv = await ConversationService.get_conversation(db, conversation_id)
        if conv:
            conv.updated_at = datetime.utcnow()

        await db.commit()
        await db.refresh(msg)
        return msg

    @staticmethod
    async def history_to_dicts(messages: list[ConversationMessage]) -> list[dict]:
        """将 ConversationMessage 对象转为 OpenAI API 所需的 dict 列表"""
        result = []
        for m in messages:
            result.append({"role": m.role, "content": m.content})
        return result
