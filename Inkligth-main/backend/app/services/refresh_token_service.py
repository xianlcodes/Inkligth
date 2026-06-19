import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.refresh_token import RefreshToken
from app.core.config import settings
from app.core.security import generate_refresh_token

logger = logging.getLogger(__name__)


class RefreshTokenService:

    @staticmethod
    async def create_refresh_token(db: AsyncSession, user_id: str) -> str:
        await RefreshTokenService._cleanup_user_tokens(db, user_id)

        token_value = generate_refresh_token()
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        rt = RefreshToken(
            user_id=user_id,
            token=token_value,
            expires_at=expires_at,
        )
        db.add(rt)
        await db.commit()
        logger.info(f"Refresh token created for user {user_id}")
        return token_value

    @staticmethod
    async def get_valid_refresh_token(db: AsyncSession, token: str) -> RefreshToken | None:
        result = await db.execute(
            select(RefreshToken).where(
                RefreshToken.token == token,
                RefreshToken.expires_at > datetime.now(timezone.utc),
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def delete_refresh_token(db: AsyncSession, token: str) -> None:
        await db.execute(
            delete(RefreshToken).where(RefreshToken.token == token)
        )
        await db.commit()
        logger.info(f"Refresh token deleted: {token[:8]}...")

    @staticmethod
    async def _cleanup_user_tokens(db: AsyncSession, user_id: str) -> None:
        await db.execute(
            delete(RefreshToken).where(RefreshToken.user_id == user_id)
        )
        await db.commit()

    @staticmethod
    async def delete_all_user_tokens(db: AsyncSession, user_id: str) -> None:
        await RefreshTokenService._cleanup_user_tokens(db, user_id)
        logger.info(f"All refresh tokens deleted for user {user_id}")
