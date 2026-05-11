import asyncio
from app.db.database import engine, Base
from app.models.user import User  # noqa: F401
from app.models.literature import Literature  # noqa: F401


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables created successfully.")


if __name__ == "__main__":
    asyncio.run(init_db())
