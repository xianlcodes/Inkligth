from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class AnnouncementCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    level: str = Field(default="info", pattern="^(info|warning|success)$")
    is_pinned: bool = False
    published_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class AnnouncementUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = None
    level: Optional[str] = Field(None, pattern="^(info|warning|success)$")
    is_pinned: Optional[bool] = None
    is_published: Optional[bool] = None
    published_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class AnnouncementResponse(BaseModel):
    id: str
    title: str
    content: str
    level: str
    is_pinned: bool
    is_published: bool
    published_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AnnouncementListResponse(BaseModel):
    items: list[AnnouncementResponse]
