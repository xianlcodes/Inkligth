import logging
import os
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.tutorial import (
    TutorialCreate,
    TutorialUpdate,
    TutorialResponse,
    TutorialListResponse,
    TutorialVersionResponse,
    TutorialVersionListResponse,
)
from app.services.tutorial_service import TutorialService
from app.models.tutorial import Tutorial, TutorialVersion
from app.schemas.tutorial import TutorialVersionResponse 

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tutorials", tags=["tutorials"])

TUTORIAL_IMAGE_DIR = os.path.join("uploads", "tutorial_images")
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024


def _check_admin(current_user: User):
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅管理员可执行此操作")


def _to_response(t: Tutorial) -> TutorialResponse:
    return TutorialResponse(
        id=t.id,
        title=t.title,
        content=t.content,
        summary=t.summary,
        is_published=t.is_published,
        published_at=t.published_at,
        created_by=t.created_by,
        created_at=t.created_at,
        updated_at=t.updated_at,
        version_count=len(t.versions) if t.versions else 0,
    )


def _to_version_response(v: TutorialVersion) -> TutorialVersionResponse:
    return TutorialVersionResponse(
        id=v.id,
        tutorial_id=v.tutorial_id,
        version_number=v.version_number,
        title=v.title,
        content=v.content,
        summary=v.summary,
        created_by=v.created_by,
        created_at=v.created_at,
    )


@router.post("/images/upload")
async def upload_tutorial_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    _check_admin(current_user)

    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail=f"不支持的图片格式: {file.content_type}，仅支持 JPG/PNG/GIF/WebP")

    content = await file.read()
    if len(content) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=400, detail="图片大小不能超过 5MB")

    os.makedirs(TUTORIAL_IMAGE_DIR, exist_ok=True)

    ext = file.filename.rsplit(".", 1)[-1].lower() if file.filename and "." in file.filename else "png"
    if ext not in ("jpg", "jpeg", "png", "gif", "webp"):
        ext = "png"
    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(TUTORIAL_IMAGE_DIR, filename)

    with open(filepath, "wb") as f:
        f.write(content)

    url = f"/api/v1/tutorials/images/{filename}"
    logger.info("Tutorial image uploaded: %s by user %s", filename, current_user.id)
    return {"code": 200, "msg": "success", "data": {"url": url, "filename": filename}}


@router.get("/images/{filename}")
async def get_tutorial_image(filename: str):
    filepath = os.path.join(TUTORIAL_IMAGE_DIR, filename)
    if not os.path.isfile(filepath):
        raise HTTPException(status_code=404, detail="图片不存在")

    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "png"
    media_type_map = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "gif": "image/gif", "webp": "image/webp"}
    media_type = media_type_map.get(ext, "image/png")
    return FileResponse(filepath, media_type=media_type)


@router.get("/published", response_model=TutorialListResponse)
async def list_published_tutorials(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    total, items = await TutorialService.get_published_tutorials(db, skip=skip, limit=limit)
    return TutorialListResponse(total=total, items=[_to_response(t) for t in items])


@router.get("/published/{tutorial_id}", response_model=TutorialResponse)
async def get_published_tutorial(
    tutorial_id: str,
    db: AsyncSession = Depends(get_db),
):
    tutorial = await TutorialService.get_published_tutorial_by_id(db, tutorial_id)
    if not tutorial:
        raise HTTPException(status_code=404, detail="教程不存在或未发布")
    return _to_response(tutorial)


@router.get("", response_model=TutorialListResponse)
async def list_tutorials(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_admin(current_user)
    total, items = await TutorialService.get_all_tutorials(db, skip=skip, limit=limit)
    return TutorialListResponse(total=total, items=[_to_response(t) for t in items])


@router.get("/{tutorial_id}", response_model=TutorialResponse)
async def get_tutorial(
    tutorial_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_admin(current_user)
    tutorial = await TutorialService.get_tutorial_by_id(db, tutorial_id)
    if not tutorial:
        raise HTTPException(status_code=404, detail="教程不存在")
    return _to_response(tutorial)


@router.post("", response_model=TutorialResponse, status_code=status.HTTP_201_CREATED)
async def create_tutorial(
    data: TutorialCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_admin(current_user)
    tutorial = await TutorialService.create_tutorial(db, data.model_dump(), str(current_user.id))
    return _to_response(tutorial)


@router.patch("/{tutorial_id}", response_model=TutorialResponse)
async def update_tutorial(
    tutorial_id: str,
    data: TutorialUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_admin(current_user)
    tutorial = await TutorialService.get_tutorial_by_id(db, tutorial_id)
    if not tutorial:
        raise HTTPException(status_code=404, detail="教程不存在")
    update_data = data.model_dump(exclude_unset=True)
    updated = await TutorialService.update_tutorial(db, tutorial, update_data, str(current_user.id))
    return _to_response(updated)


@router.delete("/{tutorial_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tutorial(
    tutorial_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_admin(current_user)
    tutorial = await TutorialService.get_tutorial_by_id(db, tutorial_id)
    if not tutorial:
        raise HTTPException(status_code=404, detail="教程不存在")
    await TutorialService.delete_tutorial(db, tutorial)


@router.get("/{tutorial_id}/versions", response_model=TutorialVersionListResponse)
async def list_versions(
    tutorial_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_admin(current_user)
    tutorial = await TutorialService.get_tutorial_by_id(db, tutorial_id)
    if not tutorial:
        raise HTTPException(status_code=404, detail="教程不存在")
    versions = await TutorialService.get_versions(db, tutorial_id)
    return TutorialVersionListResponse(items=[_to_version_response(v) for v in versions])


@router.post("/{tutorial_id}/versions/{version_id}/restore", response_model=TutorialResponse)
async def restore_version(
    tutorial_id: str,
    version_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_admin(current_user)
    tutorial = await TutorialService.get_tutorial_by_id(db, tutorial_id)
    if not tutorial:
        raise HTTPException(status_code=404, detail="教程不存在")
    version = await TutorialService.get_version_by_id(db, version_id)
    if not version or version.tutorial_id != tutorial_id:
        raise HTTPException(status_code=404, detail="版本不存在")
    restored = await TutorialService.restore_version(db, tutorial, version, str(current_user.id))
    return _to_response(restored)