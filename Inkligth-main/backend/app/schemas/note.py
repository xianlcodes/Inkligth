from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class RectCoords(BaseModel):
    x: float = Field(..., ge=0, le=1, description="左边距占页面宽度的百分比")
    y: float = Field(..., ge=0, le=1, description="上边距占页面高度的百分比")
    width: float = Field(..., ge=0, le=1, description="宽度占页面宽度的百分比")
    height: float = Field(..., ge=0, le=1, description="高度占页面高度的百分比")


class NoteCreate(BaseModel):
    literature_id: str
    page_number: str
    rect_coords: RectCoords
    quoted_text: Optional[str] = None
    content: Optional[str] = None
    note_type: str = Field(default="general", pattern="^(general|innovation|method|question)$")


class NoteUpdate(BaseModel):
    content: Optional[str] = None
    note_type: Optional[str] = Field(default=None, pattern="^(general|innovation|method|question)$")


class NoteResponse(BaseModel):
    id: str
    user_id: str
    literature_id: str
    literature_title: Optional[str] = None
    page_number: str
    rect_coords: dict
    quoted_text: Optional[str] = None
    content: Optional[str] = None
    note_type: str
    created_at: datetime

    class Config:
        from_attributes = True


class NoteListResponse(BaseModel):
    total: int
    items: list[NoteResponse]