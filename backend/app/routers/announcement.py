import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.announcement import (
    AnnouncementCreate,
    AnnouncementUpdate,
    AnnouncementResponse,
    AnnouncementListResponse,
)
from app.services.announcement_service import AnnouncementService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/announcements", tags=["announcements"])


def _check_admin(current_user: User):
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅管理员可执行此操作")


def _to_response(a) -> AnnouncementResponse:
    return AnnouncementResponse(
        id=a.id,
        title=a.title,
        content=a.content,
        level=a.level,
        scope=a.scope,
        is_pinned=a.is_pinned,
        is_published=a.is_published,
        published_at=a.published_at,
        expires_at=a.expires_at,
        created_at=a.created_at,
        updated_at=a.updated_at,
    )


@router.get("/public", response_model=AnnouncementListResponse)
async def get_public_announcements(
    db: AsyncSession = Depends(get_db),
):
    items = await AnnouncementService.get_public_announcements(db)
    return AnnouncementListResponse(items=[_to_response(a) for a in items])


@router.get("/active", response_model=AnnouncementListResponse)
async def get_active_announcements(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items = await AnnouncementService.get_active_announcements(db)
    return AnnouncementListResponse(items=[_to_response(a) for a in items])


@router.get("", response_model=AnnouncementListResponse)
async def list_announcements(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    total, items = await AnnouncementService.get_all_announcements(db, skip=skip, limit=limit)
    return AnnouncementListResponse(items=[_to_response(a) for a in items])


@router.get("/{announcement_id}", response_model=AnnouncementResponse)
async def get_announcement(
    announcement_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    announcement = await AnnouncementService.get_announcement_by_id(db, announcement_id)
    if not announcement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="公告不存在")
    return _to_response(announcement)


@router.post("", response_model=AnnouncementResponse, status_code=status.HTTP_201_CREATED)
async def create_announcement(
    data: AnnouncementCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_admin(current_user)
    announcement = await AnnouncementService.create_announcement(db, data.model_dump())
    return _to_response(announcement)


@router.patch("/{announcement_id}", response_model=AnnouncementResponse)
async def update_announcement(
    announcement_id: str,
    data: AnnouncementUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_admin(current_user)
    announcement = await AnnouncementService.get_announcement_by_id(db, announcement_id)
    if not announcement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="公告不存在")
    update_data = data.model_dump(exclude_unset=True)
    updated = await AnnouncementService.update_announcement(db, announcement, update_data)
    return _to_response(updated)


@router.delete("/{announcement_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_announcement(
    announcement_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_admin(current_user)
    announcement = await AnnouncementService.get_announcement_by_id(db, announcement_id)
    if not announcement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="公告不存在")
    await AnnouncementService.delete_announcement(db, announcement)
