from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class SlideData(BaseModel):
    title: str
    bullets: List[str] = []
    notes: Optional[str] = None


class PresentationCreate(BaseModel):
    literature_id: str
    literature_title: Optional[str] = None
    slides: List[SlideData] = []


class PresentationResponse(BaseModel):
    id: str
    literature_id: Optional[str] = None
    literature_title: Optional[str] = None
    slides: List[SlideData] = []
    slide_count: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PresentationListResponse(BaseModel):
    total: int
    items: List[PresentationResponse]