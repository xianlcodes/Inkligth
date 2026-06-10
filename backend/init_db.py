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
from app.models.feedback import Feedback  # noqa: F401
from app.models.featured_paper import FeaturedPaper  # noqa: F401

# Skills & Hooks models
from app.skills.models import Skill, Hook  # noqa: F401

# Argument Companion models
from app.argument.models import Ledger, Promise, ReviewSession, ReviewPoint, Anchor  # noqa: F401

# Conversation models
from app.models.conversation import Conversation, ConversationMessage  # noqa: F401

# PdfTranslation model
from app.models.pdf_translation import PdfTranslation  # noqa: F401

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
    "ALTER TABLE ai_engines ADD COLUMN IF NOT EXISTS proxy_enabled BOOLEAN NOT NULL DEFAULT false",
    "ALTER TABLE skills ADD COLUMN IF NOT EXISTS category VARCHAR(30) DEFAULT 'general'",
    "ALTER TABLE conversations ADD COLUMN IF NOT EXISTS title VARCHAR(200) DEFAULT '新对话'",
    "ALTER TABLE conversations ADD COLUMN IF NOT EXISTS type VARCHAR(20) DEFAULT 'writing'",
    "ALTER TABLE conversations ADD COLUMN IF NOT EXISTS literature_id VARCHAR REFERENCES literatures(id) ON DELETE SET NULL",
    "ALTER TABLE conversation_messages ADD COLUMN IF NOT EXISTS context_text TEXT",
    "ALTER TABLE conversations ADD COLUMN IF NOT EXISTS skill_names JSON DEFAULT NULL",
    "CREATE TABLE IF NOT EXISTS pdf_translations (id VARCHAR PRIMARY KEY, literature_id VARCHAR NOT NULL REFERENCES literatures(id) ON DELETE CASCADE, user_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE, task_id VARCHAR NOT NULL, source_lang VARCHAR DEFAULT 'en', target_lang VARCHAR DEFAULT 'zh', output_mode VARCHAR DEFAULT 'mono', file_path VARCHAR NOT NULL, file_size BIGINT, created_at TIMESTAMP DEFAULT NOW(), expires_at TIMESTAMP NOT NULL)",
    "CREATE INDEX IF NOT EXISTS ix_pdf_translations_literature_user ON pdf_translations (literature_id, user_id)",
]


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        for migration_sql in MIGRATIONS:
            await conn.execute(text(migration_sql))
    print("Database tables and migrations applied successfully.")


if __name__ == "__main__":
    asyncio.run(init_db())
