import asyncio
from sqlalchemy import text
from app.db.database import engine, Base
from app.models.user import User  # noqa: F401
from app.models.literature import Literature  # noqa: F401
from app.models.tag import Tag  # noqa: F401
from app.models.note import Note  # noqa: F401
from app.models.ai_analysis import AIAnalysis  # noqa: F401
from app.models.ai_engine import AIEngine  # noqa: F401
from app.models.literature_chunk import LiteratureChunk  # noqa: F401
from app.models.reading_record import ReadingRecord  # noqa: F401
from app.models.presentation import Presentation  # noqa: F401
from app.models.announcement import Announcement  # noqa: F401
from app.models.folder import Folder  # noqa: F401
from app.models.refresh_token import RefreshToken  # noqa: F401
from app.models.translation import Translation  # noqa: F401

MIGRATIONS = [
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT false",
    "ALTER TABLE literatures ADD COLUMN IF NOT EXISTS folder_id VARCHAR",
    "ALTER TABLE literatures ADD COLUMN IF NOT EXISTS translated_at TIMESTAMP",
    "ALTER TABLE literatures ALTER COLUMN translated_text TYPE BYTEA USING NULL",
]


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        for migration_sql in MIGRATIONS:
            await conn.execute(text(migration_sql))
    print("Database tables and migrations applied successfully.")


if __name__ == "__main__":
    asyncio.run(init_db())
