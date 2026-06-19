import hashlib
import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.email_verification import EmailVerificationToken

logger = logging.getLogger(__name__)

CODE_LENGTH = 6
CODE_TTL_MINUTES = 15

_rate_limit_store: dict[str, list[float]] = {}


def _check_rate_limit(key: str, max_requests: int = 3, window_seconds: int = 3600) -> bool:
    now = datetime.utcnow().timestamp()
    timestamps = _rate_limit_store.get(key, [])
    timestamps = [t for t in timestamps if now - t < window_seconds]
    _rate_limit_store[key] = timestamps
    if len(timestamps) >= max_requests:
        return False
    timestamps.append(now)
    return True


def generate_code() -> str:
    return "".join(secrets.choice("0123456789") for _ in range(CODE_LENGTH))


def hash_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


async def send_verification_code(db: AsyncSession, email: str, ip_address: str) -> tuple[bool, str]:
    from app.services.user_service import UserService

    existing = await UserService.get_user_by_email(db, email)
    if existing:
        return False, "该邮箱已注册"

    ip_key = f"ip:{ip_address}"
    email_key = f"email:{email.lower()}"
    if not _check_rate_limit(ip_key) or not _check_rate_limit(email_key):
        logger.warning(f"Email verification rate limit hit: email={email}, ip={ip_address}")
        return False, "请求过于频繁，请1小时后再试"

    code = generate_code()
    hashed = hash_code(code)
    expires_at = datetime.utcnow() + timedelta(minutes=CODE_TTL_MINUTES)

    token_record = EmailVerificationToken(
        email=email.lower(),
        token=hashed,
        expires_at=expires_at,
    )
    db.add(token_record)
    await db.commit()
    await db.refresh(token_record)

    from app.services.email_service import send_verification_email

    success, error_msg = send_verification_email(email, code)
    if not success:
        logger.error(f"Failed to send verification email to {email}: {error_msg}")
        return False, error_msg or "邮件发送失败，请稍后重试"

    logger.info(f"Verification code sent to {email}")
    return True, "验证码已发送至您的邮箱"


async def verify_code(db: AsyncSession, email: str, code: str) -> bool:
    hashed = hash_code(code)
    now = datetime.utcnow()

    q = (
        select(EmailVerificationToken)
        .where(
            EmailVerificationToken.email == email.lower(),
            EmailVerificationToken.token == hashed,
            EmailVerificationToken.used == False,
            EmailVerificationToken.expires_at > now,
        )
        .order_by(EmailVerificationToken.created_at.desc())
        .limit(1)
    )
    result = await db.execute(q)
    token_record = result.scalar_one_or_none()

    if not token_record:
        return False

    token_record.used = True
    await db.commit()
    logger.info(f"Email verification code verified for {email}")
    return True
