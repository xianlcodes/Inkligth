from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class FeedbackCreate(BaseModel):
    content: str
    page_url: Optional[str] = None
    browser_info: Optional[str] = None


class FeedbackResponse(BaseModel):
    id: str
    user_id: str
    user_email: Optional[str] = None
    user_name: Optional[str] = None
    content: str
    page_url: Optional[str] = None
    browser_info: Optional[str] = None
    is_resolved: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class FeedbackListResponse(BaseModel):
    total: int
    items: list[FeedbackResponse]
