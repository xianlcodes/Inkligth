import logging
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_user_db as get_db
from app.core.deps import get_current_user
from app.schemas.storage import StorageResponse
from app.services.storage_service import StorageService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("", response_model=StorageResponse)
async def get_storage(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    storage = await StorageService.get_storage(db, current_user.id)
    return StorageResponse(
        total_space=storage.total_space,
        used_space=storage.used_space,
        remaining_space=storage.total_space - storage.used_space,
        base_space=storage.base_space,
        check_in_bonus=storage.check_in_bonus,
        invitation_bonus=storage.invitation_bonus,
    )