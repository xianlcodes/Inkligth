from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.presentation import (
    PresentationCreate,
    PresentationResponse,
    PresentationListResponse,
)
from app.services.presentation_service import PresentationService

router = APIRouter(prefix="/presentations", tags=["presentations"])


@router.post("", response_model=dict)
async def create_presentation(
    data: PresentationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    presentation = await PresentationService.create_presentation(
        db, str(current_user.id), data
    )
    return {
        "code": 200,
        "msg": "success",
        "data": PresentationResponse.model_validate(presentation).model_dump(mode="json"),
    }


@router.get("", response_model=dict)
async def list_presentations(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await PresentationService.get_presentations(
        db, str(current_user.id), limit=limit, offset=offset
    )
    items = [
        PresentationResponse.model_validate(p).model_dump(mode="json")
        for p in result["items"]
    ]
    return {
        "code": 200,
        "msg": "success",
        "data": {"total": result["total"], "items": items},
    }


@router.get("/{presentation_id}", response_model=dict)
async def get_presentation(
    presentation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    presentation = await PresentationService.get_presentation(
        db, presentation_id, str(current_user.id)
    )
    if not presentation:
        raise HTTPException(status_code=404, detail="汇报记录不存在")
    return {
        "code": 200,
        "msg": "success",
        "data": PresentationResponse.model_validate(presentation).model_dump(mode="json"),
    }


@router.delete("/{presentation_id}", response_model=dict)
async def delete_presentation(
    presentation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    deleted = await PresentationService.delete_presentation(
        db, presentation_id, str(current_user.id)
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="汇报记录不存在")
    return {"code": 200, "msg": "success", "data": None}