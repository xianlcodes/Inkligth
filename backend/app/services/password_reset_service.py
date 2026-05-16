import hashlib
import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.password_reset import PasswordResetToken
from app.services.email_service import send_reset_code_email

logger = logging.getLogger(__name__)

RESET_CODE_LENGTH = 6
RESET_CODE_TTL_MINUTES = 15

_rate_limit_store: dict[str, list[float]] = {}


def _check_rate_limit(key: str, max_requests: int = 5, window_seconds: int = 3600) -> bool:
    now = datetime.utcnow().timestamp()
    timestamps = _rate_limit_store.get(key, [])
    timestamps = [t for t in timestamps if now - t < window_seconds]
    _rate_limit_store[key] = timestamps
    if len(timestamps) >= max_requests:
        return False
    timestamps.append(now)
    return True


def generate_reset_code() -> str:
    return "".join(secrets.choice("0123456789") for _ in range(RESET_CODE_LENGTH))


def hash_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


class PasswordResetService:

    @staticmethod
    async def create_reset_token(db: AsyncSession, email: str, ip_address: str) -> tuple[bool, str]:
        ip_key = f"ip:{ip_address}"
        email_key = f"email:{email.lower()}"

        if not _check_rate_limit(ip_key) or not _check_rate_limit(email_key):
            logger.warning(f"Rate limit hit for password reset: email={email}, ip={ip_address}")
            return False, "请求过于频繁，请1小时后再试"

        code = generate_reset_code()
        hashed = hash_code(code)
        expires_at = datetime.utcnow() + timedelta(minutes=RESET_CODE_TTL_MINUTES)

        token_record = PasswordResetToken(
            email=email.lower(),
            token=hashed,
            expires_at=expires_at,
        )
        db.add(token_record)
        await db.commit()
        await db.refresh(token_record)

        success, error_msg = send_reset_code_email(email, code)
        if not success:
            logger.error(f"Failed to send reset email to {email}: {error_msg}")
            return False, error_msg or "邮件发送失败，请稍后重试"

        logger.info(f"Password reset code sent to {email}")
        return True, "验证码已发送至您的邮箱"

    @staticmethod
    async def verify_reset_code(db: AsyncSession, email: str, code: str) -> Optional[str]:
        hashed = hash_code(code)
        now = datetime.utcnow()

        q = (
            select(PasswordResetToken)
            .where(
                PasswordResetToken.email == email.lower(),
                PasswordResetToken.token == hashed,
                PasswordResetToken.used == False,
                PasswordResetToken.expires_at > now,
            )
            .order_by(PasswordResetToken.created_at.desc())
            .limit(1)
        )
        result = await db.execute(q)
        token_record = result.scalar_one_or_none()

        if not token_record:
            return None

        token_record.used = True
        await db.commit()
        await db.refresh(token_record)

        verification_id = hashlib.sha256(
            (token_record.id + token_record.email).encode()
        ).hexdigest()
        return verification_id

    @staticmethod
    async def verify_reset_session(db: AsyncSession, email: str, verification_id: str) -> bool:
        valid_until = datetime.utcnow() - timedelta(minutes=RESET_CODE_TTL_MINUTES + 5)

        q = (
            select(PasswordResetToken)
            .where(
                PasswordResetToken.email == email.lower(),
                PasswordResetToken.used == True,
                PasswordResetToken.created_at > valid_until,
            )
            .order_by(PasswordResetToken.created_at.desc())
            .limit(1)
        )
        result = await db.execute(q)
        token_record = result.scalar_one_or_none()

        if not token_record:
            return False

        expected = hashlib.sha256(
            (token_record.id + token_record.email).encode()
        ).hexdigest()
        return verification_id == expected
