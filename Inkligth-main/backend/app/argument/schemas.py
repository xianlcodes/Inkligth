"""
Argument Companion Pydantic schemas
"""

from enum import Enum
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Enums ──

class PromiseStatus(str, Enum):
    PAID = "paid"
    PARTIAL = "partial"
    UNPAID = "unpaid"
    MISMATCH = "mismatch"


class PromiseSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class ReviewCategory(str, Enum):
    METHODOLOGY = "methodology"
    EXPERIMENT = "experiment"
    WRITING = "writing"
    DEVILS_ADVOCATE = "devils_advocate"


class ReviewSeverity(str, Enum):
    MAJOR = "major"
    MINOR = "minor"
    CRITICAL = "critical"


class RebuttalStatus(str, Enum):
    PENDING = "pending"
    ADDRESSED = "addressed"
    DISPUTED = "disputed"


class AnchorStatus(str, Enum):
    ANCHORED = "anchored"
    DRIFTED = "drifted"
    LOST = "lost"


# ── Ledger ──

class PromiseResponse(BaseModel):
    id: str
    claim_text: str
    claim_anchor: Optional[str] = None
    claim_section: Optional[str] = None
    status: str
    severity: str
    discharge_text: Optional[str] = None
    discharge_anchor: Optional[str] = None
    user_overridden: bool = False
    user_status: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class LedgerResponse(BaseModel):
    id: str
    literature_id: str
    title: Optional[str] = None
    status: str
    checksum: Optional[str] = None
    promises: list[PromiseResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BuildLedgerRequest(BaseModel):
    literature_id: str
    mode: str = Field(default="full", pattern="^(full|incremental)$")


class PromiseUpdateRequest(BaseModel):
    user_status: str = Field(..., pattern="^(paid|partial|unpaid|mismatch)$")
    user_overridden: bool = True


# ── Review ──

class ReviewPointResponse(BaseModel):
    id: str
    category: str
    severity: str
    title: str
    description: str
    suggestion: Optional[str] = None
    anchor_ref: Optional[str] = None
    rebuttal: Optional[str] = None
    rebuttal_status: Optional[str] = None
    reviewer_response: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ReviewSessionResponse(BaseModel):
    id: str
    literature_id: str
    mode: str
    status: str
    overall_assessment: Optional[str] = None
    strengths: Optional[str] = None
    top_issues: Optional[str] = None
    points: list[ReviewPointResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RunReviewRequest(BaseModel):
    literature_id: str
    mode: str = Field(default="parallel", pattern="^(serial|parallel)$")
    perspectives: list[str] = Field(
        default=["methodology", "experiment", "writing", "devils_advocate"],
        min_length=1,
        max_length=4,
    )


# ── Rebuttal ──

class RebuttalRequest(BaseModel):
    session_id: str
    point_id: str
    message: str = Field(..., min_length=1)


class RebuttalResponse(BaseModel):
    point_id: str
    session_id: str
    rebuttal_status: str
    reviewer_response: Optional[str] = None


# ── SSE Events ──

class SSEEvent(BaseModel):
    event: str                                          # promise | review_point | progress | complete | error
    data: dict = {}


# ── Literature Content (for internal use) ──

class LiteratureContent(BaseModel):
    id: str
    title: str
    full_text: str
