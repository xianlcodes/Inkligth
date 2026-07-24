import logging
import re
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from app.db.database import get_user_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas import (
    UserCreate,
    UserResponse,
    TokenRefreshRequest,
    TokenRefreshResponse,
    TokenWithRefresh,
)
from app.schemas.user import (
    ForgotPasswordRequest,
    VerifyResetCodeRequest,
    VerifyResetCodeResponse,
    ResetPasswordRequest,
    SendVerificationCodeRequest,
)
from app.services.user_service import UserService
from app.services.refresh_token_service import RefreshTokenService
from app.services.captcha_service import generate_captcha, verify_captcha
from app.services.password_reset_service import PasswordResetService
from app.services.email_verification_service import send_verification_code, verify_code
from app.services.invitation_service import InvitationService
from app.services.storage_service import StorageService
from app.core.security import create_access_token, get_password_hash

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


@router.post("/send-verification-code")
async def send_verification_code_endpoint(
    data: SendVerificationCodeRequest,
    request: Request,
    db: AsyncSession = Depends(get_user_db),
):
    ip = request.client.host if request.client else "127.0.0.1"
    success, msg = await send_verification_code(db, data.email, ip)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST if "已注册" in msg else status.HTTP_429_TOO_MANY_REQUESTS,
            detail=msg,
        )
    return {"message": msg}


@router.post("/register", response_model=UserResponse)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_user_db)):
    if not user_in.agreed_to_terms:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请先阅读并同意用户服务协议和隐私政策",
        )
    if not verify_captcha(user_in.captcha_id, user_in.captcha_answer):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="图形验证码错误或已过期",
        )
    if not await verify_code(db, user_in.email, user_in.email_verification_code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱验证码错误或已过期",
        )
    existing = await UserService.get_user_by_email(db, user_in.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    try:
        user = await UserService.create_user(db, user_in)
        await StorageService.get_or_create_storage(db, user.id)
        await InvitationService.ensure_user_invite_code(db, user)
        if user_in.invite_code:
            await InvitationService.process_invitation(db, user_in.invite_code, user.id, user.email)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    return user


@router.post("/token", response_model=TokenWithRefresh)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_user_db),
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
    user.last_login_at = datetime.utcnow()
    await db.commit()
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
    db: AsyncSession = Depends(get_user_db),
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
    db: AsyncSession = Depends(get_user_db),
    current_user: User = Depends(get_current_user),
):
    await RefreshTokenService.delete_refresh_token(db, data.refresh_token)
    logger.info(f"User logged out: {current_user.email}")


PASSWORD_PATTERN = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$")


@router.post("/forgot-password")
async def forgot_password(
    data: ForgotPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_user_db),
):
    existing = await UserService.get_user_by_email(db, data.email)
    if not existing:
        return {"message": "如果该邮箱已注册，验证码已发送"}
    ip = request.client.host if request.client else "127.0.0.1"
    success, msg = await PasswordResetService.create_reset_token(db, data.email, ip)
    if not success:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=msg)
    return {"message": msg}


@router.post("/verify-reset-code", response_model=VerifyResetCodeResponse)
async def verify_reset_code(
    data: VerifyResetCodeRequest,
    db: AsyncSession = Depends(get_user_db),
):
    verification_id = await PasswordResetService.verify_reset_code(db, data.email, data.code)
    if not verification_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="验证码错误或已过期",
        )
    logger.info(f"Reset code verified for {data.email}")
    return VerifyResetCodeResponse(verification_id=verification_id)


@router.post("/reset-password")
async def reset_password(
    data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_user_db),
):
    if not PASSWORD_PATTERN.match(data.new_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="密码至少8位，需包含大小写字母和数字",
        )

    valid = await PasswordResetService.verify_reset_session(db, data.email, data.verification_id)
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="验证会话已过期，请重新发起密码重置",
        )

    user = await UserService.get_user_by_email(db, data.email)
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户不存在")

    user.hashed_password = get_password_hash(data.new_password)
    await db.commit()
    logger.info(f"Password reset successful for {data.email}")
    return {"message": "密码重置成功，请返回登录"}
