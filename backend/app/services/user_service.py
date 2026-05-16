from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from app.models import User
from app.schemas import UserCreate
from app.schemas.user import UserUpdate
from app.core.security import get_password_hash, verify_password


class UserService:
    @staticmethod
    async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: str) -> User | None:
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def create_user(db: AsyncSession, user_in: UserCreate) -> User:
        user = User(
            email=user_in.email,
            hashed_password=get_password_hash(user_in.password),
            username=user_in.username,
            agreed_terms_at=datetime.utcnow() if user_in.agreed_to_terms else None,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def authenticate(db: AsyncSession, email: str, password: str) -> User | None:
        user = await UserService.get_user_by_email(db, email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    @staticmethod
    async def update_user(db: AsyncSession, user_id: str, data: UserUpdate) -> User:
        user = await UserService.get_user_by_id(db, user_id)
        if not user:
            raise ValueError("User not found")
        if data.username is not None:
            user.username = data.username
        if data.avatar_style is not None:
            user.avatar_style = data.avatar_style
        if data.theme_color is not None:
            user.theme_color = data.theme_color
        await db.commit()
        await db.refresh(user)
        return user
