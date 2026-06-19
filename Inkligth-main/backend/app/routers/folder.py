import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.folder import FolderCreate, FolderUpdate, FolderResponse, FolderListResponse
from app.services.folder_service import FolderService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["folders"])


def _to_response(d: dict) -> FolderResponse:
    return FolderResponse(
        id=d["id"],
        user_id=d["user_id"],
        name=d["name"],
        parent_id=d.get("parent_id"),
        literature_count=d.get("literature_count", 0),
        created_at=d["created_at"],
        updated_at=d["updated_at"],
    )


@router.get("", response_model=FolderListResponse)
async def list_folders(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items = await FolderService.get_user_folders(db, str(current_user.id))
    return FolderListResponse(items=[_to_response(item) for item in items])


@router.post("", response_model=FolderResponse, status_code=status.HTTP_201_CREATED)
async def create_folder(
    data: FolderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        folder = await FolderService.create_folder(db, str(current_user.id), data.name)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    items = await FolderService.get_user_folders(db, str(current_user.id))
    for item in items:
        if item["id"] == folder.id:
            return _to_response(item)
    return _to_response(
        {"id": folder.id, "user_id": folder.user_id, "name": folder.name, "parent_id": folder.parent_id, "literature_count": 0, "created_at": folder.created_at, "updated_at": folder.updated_at}
    )


@router.patch("/{folder_id}", response_model=FolderResponse)
async def update_folder(
    folder_id: str,
    data: FolderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    folder = await FolderService.get_folder_by_id(db, folder_id)
    if not folder or folder.user_id != str(current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件夹不存在")
    if not data.name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="文件夹名不能为空")
    try:
        updated = await FolderService.update_folder(db, folder, data.name)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    items = await FolderService.get_user_folders(db, str(current_user.id))
    for item in items:
        if item["id"] == updated.id:
            return _to_response(item)
    return _to_response(
        {"id": updated.id, "user_id": updated.user_id, "name": updated.name, "parent_id": updated.parent_id, "literature_count": 0, "created_at": updated.created_at, "updated_at": updated.updated_at}
    )


@router.delete("/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_folder(
    folder_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    folder = await FolderService.get_folder_by_id(db, folder_id)
    if not folder or folder.user_id != str(current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件夹不存在")
    await FolderService.delete_folder(db, folder)
