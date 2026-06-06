import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.featured_paper import FeaturedPaperResponse, FeaturedPaperListResponse
from app.services.featured_paper_service import get_featured_papers

logger = logging.getLogger(__name__)

router = APIRouter(tags=["featured"])


@router.get("/featured", response_model=FeaturedPaperListResponse)
async def list_featured_papers(
    limit: int = Query(15, ge=1, le=50, description="返回论文数量"),
    db: AsyncSession = Depends(get_db),
):
    """获取每日精选论文列表。"""
    papers = await get_featured_papers(db, limit=limit)
    items = [
        FeaturedPaperResponse(
            id=p.id,
            arxiv_id=p.arxiv_id,
            title=p.title,
            authors=p.authors,
            abstract=p.abstract,
            arxiv_url=p.arxiv_url,
            published_date=p.published_date,
            category=p.category,
            created_at=p.created_at.isoformat() if p.created_at else None,
            updated_at=p.updated_at.isoformat() if p.updated_at else None,
        )
        for p in papers
    ]
    return FeaturedPaperListResponse(items=items, total=len(items))
