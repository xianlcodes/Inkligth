"""
Skills/Hooks Pydantic schemas
"""

from enum import Enum
from datetime import datetime
from typing import Optional, Any

from pydantic import BaseModel, Field


class Layer(str, Enum):
    SOUL = "soul"
    AGENTS = "agents"
    IDENTITY = "identity"


class Category(str, Enum):
    GENERAL = "general"
    SOCIAL_SCIENCE = "social-science"
    SCIENCE_ENGINEERING = "science-engineering"
    HUMANITIES = "humanities"


class HookPoint(str, Enum):
    PRE_TOOL_USE = "pre_tool_use"
    POST_TOOL_USE = "post_tool_use"
    ON_ERROR = "on_error"


class HookActionType(str, Enum):
    LOG = "log"
    THROTTLE = "throttle"
    FILTER = "filter"
    CUSTOM = "custom"


# --- Skill ---

class SkillCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z_][a-z0-9_]*$")
    description: str = Field(..., min_length=1)
    layer: Layer
    content: str = Field(..., min_length=1)
    is_active: bool = True
    match_topic: Optional[str] = None
    category: str = "general"
    priority: int = 0


class SkillUpdate(BaseModel):
    description: Optional[str] = None
    layer: Optional[Layer] = None
    content: Optional[str] = None
    is_active: Optional[bool] = None
    match_topic: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[int] = None


class SkillResponse(BaseModel):
    id: str
    name: str
    description: str
    layer: str
    content: str
    is_active: bool
    match_topic: Optional[str] = None
    category: str = "general"
    priority: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SkillListResponse(BaseModel):
    total: int
    items: list[SkillResponse]


# --- Hook ---

class HookCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z_][a-z0-9_]*$")
    description: str = Field(..., min_length=1)
    hook_point: HookPoint
    action_type: HookActionType
    config: Optional[dict[str, Any]] = None
    priority: int = 0
    is_active: bool = True


class HookUpdate(BaseModel):
    description: Optional[str] = None
    hook_point: Optional[HookPoint] = None
    action_type: Optional[HookActionType] = None
    config: Optional[dict[str, Any]] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None


class HookResponse(BaseModel):
    id: str
    name: str
    description: str
    hook_point: str
    action_type: str
    config: Optional[dict] = None
    priority: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class HookListResponse(BaseModel):
    total: int
    items: list[HookResponse]


# --- Chat with Skills (paper chat) ---

class SkillChatRequest(BaseModel):
    message: str
    context_text: str = ""
    conversation_id: Optional[str] = None


class SkillChatResponse(BaseModel):
    reply: str
    conversation_id: str
    title: str


# --- Writing Assistant ---

class WritingChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    conversation_id: Optional[str] = None
    skill_names: list[str] = []
    context_text: str = ""


class WritingChatResponse(BaseModel):
    reply: str
    conversation_id: str
    title: str
    skills_applied: list[str] = []


# --- Conversation ---

class ConversationSummary(BaseModel):
    id: str
    title: str
    type: str
    skill_names: list[str] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConversationListResponse(BaseModel):
    total: int
    items: list[ConversationSummary]


class ConversationMessageItem(BaseModel):
    id: int
    role: str
    content: str
    context_text: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationMessagesResponse(BaseModel):
    conversation_id: str
    title: str
    skill_names: list[str] = []
    messages: list[ConversationMessageItem]


# --- Presets ---

class SkillPreset(BaseModel):
    name: str
    description: str
    layer: Layer
    match_topic: Optional[str] = None
    category: str = "general"
