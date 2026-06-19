import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_user_db as get_db
from app.core.deps import get_current_user
from app.schemas.feedback import FeedbackCreate, FeedbackResponse, FeedbackListResponse
from app.services.feedback_service import FeedbackService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["feedback"])


@router.post("", response_model=FeedbackResponse)
async def submit_feedback(
    feedback_in: FeedbackCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    feedback = await FeedbackService.create_feedback(
        db=db,
        feedback_in=feedback_in,
        user_id=str(current_user.id),
        user_email=current_user.email,
        user_name=current_user.username,
    )
    return feedback


@router.get("", response_model=FeedbackListResponse)
async def list_feedback(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    resolved: bool | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not getattr(current_user, "is_admin", False):
        raise HTTPException(status_code=403, detail="Admin access required")
    total, items = await FeedbackService.list_feedback(
        db=db, skip=skip, limit=limit, resolved=resolved
    )
    return FeedbackListResponse(total=total, items=items)


@router.post("/{feedback_id}/resolve", response_model=FeedbackResponse)
async def resolve_feedback(
    feedback_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not getattr(current_user, "is_admin", False):
        raise HTTPException(status_code=403, detail="Admin access required")
    feedback = await FeedbackService.resolve_feedback(db=db, feedback_id=feedback_id)
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")
    return feedback
