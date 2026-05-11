import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.ai_engine import (
    AIEngineCreate,
    AIEngineUpdate,
    AIEngineResponse,
    AIEngineListResponse,
    AIEngineTestResult,
)
from app.services.ai_engine_service import AIEngineService, mask_api_key

logger = logging.getLogger(__name__)
router = APIRouter(tags=["ai-engines"])


def _engine_to_response(engine) -> AIEngineResponse:
    return AIEngineResponse(
        id=engine.id,
        user_id=engine.user_id,
        provider=engine.provider,
        api_base=engine.api_base,
        api_key_mask=mask_api_key(engine.api_key),
        default_model=engine.default_model,
        fallback_models=engine.fallback_models,
        is_default=engine.is_default,
        created_at=engine.created_at,
        updated_at=engine.updated_at,
    )


@router.post("", response_model=AIEngineResponse)
async def create_ai_engine(
    data: AIEngineCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    engine = await AIEngineService.create_engine(db, str(current_user.id), data)
    return _engine_to_response(engine)


@router.get("", response_model=AIEngineListResponse)
async def list_ai_engines(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    engines = await AIEngineService.get_engines_by_user(db, str(current_user.id))
    return AIEngineListResponse(
        total=len(engines),
        items=[_engine_to_response(e) for e in engines],
    )


@router.get("/{engine_id}", response_model=AIEngineResponse)
async def get_ai_engine(
    engine_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    engine = await AIEngineService.get_engine_by_id(db, engine_id, str(current_user.id))
    if not engine:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="引擎不存在")
    return _engine_to_response(engine)


@router.patch("/{engine_id}", response_model=AIEngineResponse)
async def update_ai_engine(
    engine_id: str,
    data: AIEngineUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    engine = await AIEngineService.get_engine_by_id(db, engine_id, str(current_user.id))
    if not engine:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="引擎不存在")
    updated = await AIEngineService.update_engine(db, engine, data)
    return _engine_to_response(updated)


@router.delete("/{engine_id}")
async def delete_ai_engine(
    engine_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    engine = await AIEngineService.get_engine_by_id(db, engine_id, str(current_user.id))
    if not engine:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="引擎不存在")
    await AIEngineService.delete_engine(db, engine)
    return {"code": 200, "msg": "success", "data": None}


@router.post("/{engine_id}/test", response_model=AIEngineTestResult)
async def test_ai_engine(
    engine_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    engine = await AIEngineService.get_engine_by_id(db, engine_id, str(current_user.id))
    if not engine:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="引擎不存在")
    return await AIEngineService.test_engine_connection(engine)


@router.post("/{engine_id}/set-default")
async def set_default_ai_engine(
    engine_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    engine = await AIEngineService.get_engine_by_id(db, engine_id, str(current_user.id))
    if not engine:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="引擎不存在")
    await AIEngineService.set_default_engine(db, str(current_user.id), engine_id)
    return {"code": 200, "msg": "success", "data": None}
