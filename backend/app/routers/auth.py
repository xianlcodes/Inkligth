import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from app.db.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas import (
    UserCreate,
    UserResponse,
    TokenRefreshRequest,
    TokenRefreshResponse,
    TokenWithRefresh,
)
from app.services.user_service import UserService
from app.services.refresh_token_service import RefreshTokenService
from app.services.captcha_service import generate_captcha, verify_captcha
from app.core.security import create_access_token

logger = logging.getLogger(__name__)
router = APIRouter()


class CaptchaResponse(BaseModel):
    captcha_id: str
    image_base64: str


@router.get("/captcha", response_model=CaptchaResponse)
async def get_captcha():
    result = generate_captcha()
    return CaptchaResponse(
        captcha_id=result["captcha_id"],
        image_base64=result["image_base64"],
    )


@router.post("/register", response_model=UserResponse)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    if not verify_captcha(user_in.captcha_id, user_in.captcha_answer):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="验证码错误或已过期",
        )
    existing = await UserService.get_user_by_email(db, user_in.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    try:
        user = await UserService.create_user(db, user_in)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    return user


@router.post("/token", response_model=TokenWithRefresh)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    user = await UserService.authenticate(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(subject=user.id)
    refresh_token = await RefreshTokenService.create_refresh_token(db, str(user.id))
    logger.info(f"User logged in: {user.email}")
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "is_admin": user.is_admin,
    }


@router.post("/refresh", response_model=TokenRefreshResponse)
async def refresh_access_token(
    data: TokenRefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    rt = await RefreshTokenService.get_valid_refresh_token(db, data.refresh_token)
    if not rt:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    await RefreshTokenService.delete_refresh_token(db, data.refresh_token)

    new_access_token = create_access_token(subject=rt.user_id)
    new_refresh_token = await RefreshTokenService.create_refresh_token(db, rt.user_id)
    logger.info(f"Token refreshed for user {rt.user_id}")
    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
    }


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    data: TokenRefreshRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await RefreshTokenService.delete_refresh_token(db, data.refresh_token)
    logger.info(f"User logged out: {current_user.email}")
