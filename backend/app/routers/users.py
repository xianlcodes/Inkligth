from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.core.deps import get_current_user
from app.db.database import get_user_db as get_db
from app.schemas import UserResponse
from app.schemas.user import UserUpdate, ChangePasswordRequest
from app.services.user_service import UserService
from app.services.password_reset_service import PasswordResetService
from app.core.security import get_password_hash
import re
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

PASSWORD_PATTERN = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$")


@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: dict = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_users_me(
    data: UserUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user = await UserService.update_user(db, current_user.id, data)
    return user


@router.post("/me/send-password-change-code")
async def send_password_change_code(
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ip = request.client.host if request.client else "127.0.0.1"
    success, msg = await PasswordResetService.create_reset_token(db, current_user.email, ip)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=msg,
        )
    return {"message": msg}


@router.post("/me/change-password")
async def change_password(
    data: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not PASSWORD_PATTERN.match(data.new_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="密码至少8位，需包含大小写字母和数字",
        )

    valid = await PasswordResetService.verify_reset_code(db, current_user.email, data.code)
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="验证码错误或已过期",
        )

    user = await UserService.get_user_by_id(db, current_user.id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    user.hashed_password = get_password_hash(data.new_password)
    await db.commit()
    logger.info(f"Password changed for user {current_user.email}")
    return {"message": "密码修改成功"}


class TutorialCompleteRequest(BaseModel):
    tutorial_completed: bool = True


@router.patch("/me/tutorial")
async def mark_tutorial_complete(
    data: TutorialCompleteRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user = await UserService.update_tutorial_complete(db, current_user.id, data.tutorial_completed)
    return {"tutorial_completed": user.tutorial_completed}
