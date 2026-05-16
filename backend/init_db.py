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
from app.models.admin import OperationLog, SystemConfig, ConfigChangeLog  # noqa: F401
from app.models.password_reset import PasswordResetToken  # noqa: F401
from app.models.email_verification import EmailVerificationToken  # noqa: F401
from app.models.user_storage import UserStorage  # noqa: F401
from app.models.check_in import CheckIn  # noqa: F401
from app.models.invitation import Invitation  # noqa: F401

MIGRATIONS = [
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT false",
    "ALTER TABLE literatures ADD COLUMN IF NOT EXISTS folder_id VARCHAR",
    "ALTER TABLE literatures ADD COLUMN IF NOT EXISTS translated_at TIMESTAMP",
    "ALTER TABLE literatures ALTER COLUMN translated_text TYPE BYTEA USING NULL",
    "ALTER TABLE announcements ADD COLUMN IF NOT EXISTS scope VARCHAR DEFAULT 'authenticated'",
    "ALTER TABLE system_configs ADD COLUMN IF NOT EXISTS category VARCHAR DEFAULT 'general'",
    "ALTER TABLE system_configs ADD COLUMN IF NOT EXISTS config_type VARCHAR DEFAULT 'text'",
    "ALTER TABLE system_configs ADD COLUMN IF NOT EXISTS label VARCHAR",
    "ALTER TABLE system_configs ADD COLUMN IF NOT EXISTS default_value VARCHAR",
    "ALTER TABLE system_configs ADD COLUMN IF NOT EXISTS valid_values TEXT",
    "ALTER TABLE system_configs ADD COLUMN IF NOT EXISTS example VARCHAR",
    "ALTER TABLE system_configs ADD COLUMN IF NOT EXISTS is_critical BOOLEAN DEFAULT false",
    "ALTER TABLE system_configs ADD COLUMN IF NOT EXISTS requires_restart BOOLEAN DEFAULT false",
    "ALTER TABLE system_configs ADD COLUMN IF NOT EXISTS scope VARCHAR DEFAULT 'admin'",
    "ALTER TABLE system_configs ADD COLUMN IF NOT EXISTS sort_order INTEGER DEFAULT 0",
    "ALTER TABLE system_configs ALTER COLUMN description TYPE TEXT",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_style VARCHAR",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS agreed_terms_at TIMESTAMP",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS theme_color VARCHAR DEFAULT '#e8f2e2'",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS invite_code VARCHAR",
    "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_invite_code ON users (invite_code) WHERE invite_code IS NOT NULL",
    "ALTER TABLE literatures ADD COLUMN IF NOT EXISTS file_size BIGINT",
]


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        for migration_sql in MIGRATIONS:
            await conn.execute(text(migration_sql))
    print("Database tables and migrations applied successfully.")


if __name__ == "__main__":
    asyncio.run(init_db())
