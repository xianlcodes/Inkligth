"""
Argument Companion 数据模型

包含：承诺台账（Ledger/Promise）、评审（ReviewSession/ReviewPoint）、锚点（Anchor）
"""

import uuid
from datetime import datetime

from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import TencentBase


# ═══════════════════════════════════════════════════
#  承诺台账
# ═══════════════════════════════════════════════════

class Ledger(TencentBase):
    """承诺台账 - 一篇论文一次"""
    __tablename__ = "argument_ledgers"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    literature_id = Column(String, ForeignKey("literatures.id", ondelete="CASCADE"), nullable=False, index=True)
    # user_id 无 FK 约束（跨库引用 users.id）
    user_id = Column(String, nullable=False, index=True)
    title = Column(String)
    status = Column(String, default="draft")
    checksum = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    promises = relationship("Promise", back_populates="ledger", lazy="selectin", cascade="all, delete-orphan")


class Promise(TencentBase):
    """单个承诺"""
    __tablename__ = "argument_promises"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    ledger_id = Column(String, ForeignKey("argument_ledgers.id", ondelete="CASCADE"), nullable=False)
    # user_id 无 FK 约束（跨库引用 users.id）
    user_id = Column(String, nullable=False, index=True)

    claim_text = Column(Text, nullable=False)
    claim_anchor = Column(Text)
    claim_section = Column(String)

    status = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    discharge_text = Column(Text)
    discharge_anchor = Column(Text)

    user_overridden = Column(Boolean, default=False)
    user_status = Column(String)

    created_at = Column(DateTime, default=datetime.utcnow)

    ledger = relationship("Ledger", back_populates="promises")


# ═══════════════════════════════════════════════════
#  评审
# ═══════════════════════════════════════════════════

class ReviewSession(TencentBase):
    """评审会话 - 一次评审"""
    __tablename__ = "argument_review_sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    literature_id = Column(String, ForeignKey("literatures.id", ondelete="CASCADE"), nullable=False)
    # user_id 无 FK 约束（跨库引用 users.id）
    user_id = Column(String, nullable=False, index=True)
    mode = Column(String, default="parallel")
    status = Column(String, default="draft")
    overall_assessment = Column(String)
    strengths = Column(Text)
    top_issues = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    points = relationship("ReviewPoint", back_populates="session", lazy="selectin", cascade="all, delete-orphan")


class ReviewPoint(TencentBase):
    """评审要点"""
    __tablename__ = "argument_review_points"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("argument_review_sessions.id", ondelete="CASCADE"), nullable=False)
    category = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    suggestion = Column(Text)
    anchor_ref = Column(Text)

    rebuttal = Column(Text)
    rebuttal_status = Column(String)
    reviewer_response = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("ReviewSession", back_populates="points")


# ═══════════════════════════════════════════════════
#  锚点
# ═══════════════════════════════════════════════════

class Anchor(TencentBase):
    """文本锚点 - 将引文定位到原文"""
    __tablename__ = "argument_anchors"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    literature_id = Column(String, ForeignKey("literatures.id", ondelete="CASCADE"), nullable=False, index=True)
    quote = Column(Text, nullable=False)
    char_start = Column(String)
    char_end = Column(String)
    context_before = Column(Text)
    context_after = Column(Text)
    section_path = Column(String)
    status = Column(String, default="anchored")
    created_at = Column(DateTime, default=datetime.utcnow)
