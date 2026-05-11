import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.tag import TagResponse, TagCloudResponse, LiteratureTagsResponse
from app.services.tag_service import TagService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["tags"])


@router.post("/literatures/{literature_id}/tags", response_model=TagResponse)
async def add_tag_to_literature(
    literature_id: str,
    tag_name: str = Query(..., min_length=1, max_length=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        tag = await TagService.add_tag_to_literature(db, str(current_user.id), literature_id, tag_name)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return TagResponse(id=tag.id, user_id=tag.user_id, name=tag.name, created_at=tag.created_at)


@router.delete("/literatures/{literature_id}/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_tag_from_literature(
    literature_id: str,
    tag_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        await TagService.remove_tag_from_literature(db, str(current_user.id), literature_id, tag_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/literatures/{literature_id}/tags", response_model=LiteratureTagsResponse)
async def get_literature_tags(
    literature_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tags = await TagService.get_literature_tags(db, str(current_user.id), literature_id)
    return LiteratureTagsResponse(
        literature_id=literature_id,
        tags=[TagResponse(id=t.id, user_id=t.user_id, name=t.name, created_at=t.created_at) for t in tags],
    )


@router.get("/tags/cloud", response_model=TagCloudResponse)
async def get_tag_cloud(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items = await TagService.get_user_tag_cloud(db, str(current_user.id))
    return TagCloudResponse(tags=items)