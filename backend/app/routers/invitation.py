import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.core.deps import get_current_user
from app.core.config import settings
from app.schemas.storage import InvitationListResponse, GenerateCodeResponse
from app.services.invitation_service import InvitationService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("", response_model=InvitationListResponse)
async def get_invitations(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await InvitationService.get_invitations(db, current_user.id)
    base_url = settings.BACKEND_CORS_ORIGINS[0] if settings.BACKEND_CORS_ORIGINS else "http://localhost:5173"
    return InvitationListResponse(
        codes=result["codes"],
        invited_users=result["invited_users"],
        invite_url=f"{base_url}/login?invite_code={result['codes'][0]['code']}" if result["codes"] else "",
    )


@router.post("/generate", response_model=GenerateCodeResponse)
async def generate_invitation_code(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        code = await InvitationService.generate_code(db, current_user.id)
        return GenerateCodeResponse(code=code)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))