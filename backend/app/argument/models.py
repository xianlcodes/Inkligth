"""
Argument Companion 数据模型

包含：承诺台账（Ledger/Promise）、评审（ReviewSession/ReviewPoint）、锚点（Anchor）
"""

import uuid
from datetime import datetime

from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base


# ═══════════════════════════════════════════════════
#  承诺台账
# ═══════════════════════════════════════════════════

class Ledger(Base):
    """承诺台账 - 一篇论文一次"""
    __tablename__ = "argument_ledgers"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    literature_id = Column(String, ForeignKey("literatures.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String)
    status = Column(String, default="draft")        # draft | completed | archived
    checksum = Column(String)                       # content hash for change detection
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    promises = relationship("Promise", back_populates="ledger", lazy="selectin", cascade="all, delete-orphan")


class Promise(Base):
    """单个承诺"""
    __tablename__ = "argument_promises"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    ledger_id = Column(String, ForeignKey("argument_ledgers.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    claim_text = Column(Text, nullable=False)           # promise text
    claim_anchor = Column(Text)                         # anchor JSON: {char_start, char_end, section}
    claim_section = Column(String)                      # source section

    status = Column(String, nullable=False)              # paid | partial | unpaid | mismatch
    severity = Column(String, nullable=False)            # info | warning | error
    discharge_text = Column(Text)                        # discharge evidence
    discharge_anchor = Column(Text)                      # discharge anchor JSON

    user_overridden = Column(Boolean, default=False)
    user_status = Column(String)

    created_at = Column(DateTime, default=datetime.utcnow)

    ledger = relationship("Ledger", back_populates="promises")


# ═══════════════════════════════════════════════════
#  评审
# ═══════════════════════════════════════════════════

class ReviewSession(Base):
    """评审会话 - 一次评审"""
    __tablename__ = "argument_review_sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    literature_id = Column(String, ForeignKey("literatures.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    mode = Column(String, default="parallel")            # serial | parallel
    status = Column(String, default="draft")             # draft | completed
    overall_assessment = Column(String)                  # accept | minor | major | reject
    strengths = Column(Text)                             # consensus strengths
    top_issues = Column(Text)                            # top issues (JSON array)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    points = relationship("ReviewPoint", back_populates="session", lazy="selectin", cascade="all, delete-orphan")


class ReviewPoint(Base):
    """评审要点"""
    __tablename__ = "argument_review_points"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("argument_review_sessions.id", ondelete="CASCADE"), nullable=False)
    category = Column(String, nullable=False)             # methodology | experiment | writing | devils_advocate
    severity = Column(String, nullable=False)             # major | minor | critical
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    suggestion = Column(Text)
    anchor_ref = Column(Text)                             # reference location

    # 答辩追踪
    rebuttal = Column(Text)                               # author response
    rebuttal_status = Column(String)                      # pending | addressed | disputed
    reviewer_response = Column(Text)                      # reviewer reply

    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("ReviewSession", back_populates="points")


# ═══════════════════════════════════════════════════
#  锚点
# ═══════════════════════════════════════════════════

class Anchor(Base):
    """文本锚点 - 将引文定位到原文"""
    __tablename__ = "argument_anchors"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    literature_id = Column(String, ForeignKey("literatures.id", ondelete="CASCADE"), nullable=False, index=True)
    quote = Column(Text, nullable=False)                  # quoted text
    char_start = Column(String)                           # start position (string for flexibility)
    char_end = Column(String)                             # end position
    context_before = Column(Text)                         # preceding context
    context_after = Column(Text)                          # following context
    section_path = Column(String)                         # section path
    status = Column(String, default="anchored")           # anchored | drifted | lost
    created_at = Column(DateTime, default=datetime.utcnow)
