from pydantic import BaseModel
from datetime import date
from typing import Optional


class FeaturedPaperResponse(BaseModel):
    id: str
    arxiv_id: str
    title: str
    authors: str
    abstract: str
    arxiv_url: str
    published_date: date
    category: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class FeaturedPaperListResponse(BaseModel):
    items: list[FeaturedPaperResponse]
    total: int
