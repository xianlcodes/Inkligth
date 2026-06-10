"""
Skills/Hooks 数据模型
"""

import uuid
from datetime import datetime

from sqlalchemy import Column, String, Text, Boolean, Integer, DateTime, JSON
from app.db.database import Base


class Skill(Base):
    """技能 - 分层提示注入"""
    __tablename__ = "skills"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=False)
    layer = Column(String(20), nullable=False)          # soul | agents | identity
    content = Column(Text, nullable=False)               # Markdown prompt content
    is_active = Column(Boolean, default=True)
    match_topic = Column(String(100), nullable=True)     # e.g. paper-review
    category = Column(String(30), nullable=False, default="general")  # general | social-science | science-engineering | humanities
    priority = Column(Integer, default=0)                # higher = injected first
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Skill {self.name} ({self.layer})>"


class Hook(Base):
    """钩子 - 生命周期拦截器"""
    __tablename__ = "hooks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=False)
    hook_point = Column(String(30), nullable=False)      # pre_tool_use | post_tool_use | on_error
    action_type = Column(String(20), nullable=False)     # log | throttle | filter | custom
    config = Column(JSON, nullable=True)                 # Hook configuration
    priority = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Hook {self.name} ({self.hook_point})>"
