import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import relationship
from app.db.database import AlibabaBase


class Conversation(AlibabaBase):
    __tablename__ = "conversations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(200), nullable=False, default="新对话")
    type = Column(String(20), nullable=False, default="writing")
    # literature_id 无 FK 约束（跨库引用 literatures.id）
    literature_id = Column(String, nullable=True, index=True)
    skill_names = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    messages = relationship("ConversationMessage", backref="conversation",
                            order_by="ConversationMessage.created_at",
                            cascade="all, delete-orphan")


class ConversationMessage(AlibabaBase):
    __tablename__ = "conversation_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    context_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
