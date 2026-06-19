"""
双数据库初始化脚本

初始化两家云数据库的表结构并执行增量迁移 SQL。
- TencentBase: 腾讯云远程 PostgreSQL（文献相关数据）
- AlibabaBase: 阿里云本地 PostgreSQL（用户相关数据）
"""

import asyncio
from sqlalchemy import text

from app.db.database import (
    tencent_engine, TencentBase,
    alibaba_engine, AlibabaBase,
)

# ═══════════════════════════════════════════════════════════
#  腾讯云数据库模型（文献相关）
# ═══════════════════════════════════════════════════════════

from app.models.literature import Literature  # noqa: F401
from app.models.literature_chunk import LiteratureChunk  # noqa: F401
from app.models.tag import Tag  # noqa: F401
from app.models.note import Note  # noqa: F401
from app.models.reading_record import ReadingRecord  # noqa: F401
from app.models.presentation import Presentation  # noqa: F401
from app.models.folder import Folder  # noqa: F401
from app.models.translation import Translation  # noqa: F401
from app.models.pdf_translation import PdfTranslation  # noqa: F401
from app.models.translation_cache import TranslationCache  # noqa: F401
from app.models.featured_paper import FeaturedPaper  # noqa: F401
from app.models.ai_analysis import AIAnalysis  # noqa: F401

# Argument Companion 模型
from app.argument.models import Ledger, Promise, ReviewSession, ReviewPoint, Anchor  # noqa: F401


# ═══════════════════════════════════════════════════════════
#  阿里云数据库模型（用户相关）
# ═══════════════════════════════════════════════════════════

from app.models.user import User  # noqa: F401
from app.models.refresh_token import RefreshToken  # noqa: F401
from app.models.user_storage import UserStorage  # noqa: F401
from app.models.announcement import Announcement  # noqa: F401
from app.models.check_in import CheckIn  # noqa: F401
from app.models.invitation import Invitation  # noqa: F401
from app.models.password_reset import PasswordResetToken  # noqa: F401
from app.models.email_verification import EmailVerificationToken  # noqa: F401
from app.models.feedback import Feedback  # noqa: F401
from app.models.admin import OperationLog, SystemConfig, ConfigChangeLog  # noqa: F401
from app.models.ai_engine import AIEngine  # noqa: F401
from app.models.conversation import Conversation, ConversationMessage  # noqa: F401
from app.models.tutorial import Tutorial, TutorialVersion  # noqa: F401
from app.skills.models import Skill, Hook  # noqa: F401
from app.export.models import ExportRecord  # noqa: F401


# ═══════════════════════════════════════════════════════════
#  增量迁移 SQL（按数据库拆分）
# ═══════════════════════════════════════════════════════════

TENCENT_MIGRATIONS = [
    # literatures 表
    "ALTER TABLE literatures ADD COLUMN IF NOT EXISTS folder_id VARCHAR",
    "ALTER TABLE literatures ADD COLUMN IF NOT EXISTS translated_at TIMESTAMP",
    "ALTER TABLE literatures ALTER COLUMN translated_text TYPE BYTEA USING NULL",
    "ALTER TABLE literatures ADD COLUMN IF NOT EXISTS file_size BIGINT",
    # 删除跨库外键（用户在阿里云，文献在腾讯云，FK 不跨库）
    "ALTER TABLE literatures DROP CONSTRAINT IF EXISTS literatures_user_id_fkey",
    "ALTER TABLE folders DROP CONSTRAINT IF EXISTS folders_user_id_fkey",
    "ALTER TABLE presentations DROP CONSTRAINT IF EXISTS presentations_user_id_fkey",
    "ALTER TABLE reading_records DROP CONSTRAINT IF EXISTS reading_records_user_id_fkey",
    "ALTER TABLE notes DROP CONSTRAINT IF EXISTS notes_user_id_fkey",
    "ALTER TABLE pdf_translations DROP CONSTRAINT IF EXISTS pdf_translations_user_id_fkey",

    # pdf_translations 表（user_id 无 FK 约束 — 跨库引用 users.id）
    "CREATE TABLE IF NOT EXISTS pdf_translations ("
    "id VARCHAR PRIMARY KEY, "
    "literature_id VARCHAR NOT NULL REFERENCES literatures(id) ON DELETE CASCADE, "
    "user_id VARCHAR NOT NULL, "
    "task_id VARCHAR NOT NULL, "
    "source_lang VARCHAR DEFAULT 'en', "
    "target_lang VARCHAR DEFAULT 'zh', "
    "output_mode VARCHAR DEFAULT 'mono', "
    "file_path VARCHAR NOT NULL, "
    "file_size BIGINT, "
    "created_at TIMESTAMP DEFAULT NOW(), "
    "expires_at TIMESTAMP NOT NULL"
    ")",
    "CREATE INDEX IF NOT EXISTS ix_pdf_translations_literature_user "
    "ON pdf_translations (literature_id, user_id)",

    # presentations 表 — ppt_file_path 持久化
    "ALTER TABLE presentations ADD COLUMN IF NOT EXISTS ppt_file_path VARCHAR(1024)",
]

ALIBABA_MIGRATIONS = [
    # users 表
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT false",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_style VARCHAR",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS agreed_terms_at TIMESTAMP",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS theme_color VARCHAR DEFAULT '#e8f2e2'",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS invite_code VARCHAR",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMP",
    "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_invite_code ON users (invite_code) WHERE invite_code IS NOT NULL",

    # announcements 表
    "ALTER TABLE announcements ADD COLUMN IF NOT EXISTS scope VARCHAR DEFAULT 'authenticated'",

    # system_configs 表
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

    # ai_engines 表
    "ALTER TABLE ai_engines ADD COLUMN IF NOT EXISTS proxy_enabled BOOLEAN NOT NULL DEFAULT false",

    # skills 表
    "ALTER TABLE skills ADD COLUMN IF NOT EXISTS category VARCHAR(30) DEFAULT 'general'",

    # conversations 表（literature_id 无 FK 约束 — 跨库引用 literatures.id）
    "ALTER TABLE conversations ADD COLUMN IF NOT EXISTS title VARCHAR(200) DEFAULT '新对话'",
    "ALTER TABLE conversations ADD COLUMN IF NOT EXISTS type VARCHAR(20) DEFAULT 'writing'",
    "ALTER TABLE conversations ADD COLUMN IF NOT EXISTS literature_id VARCHAR",
    "ALTER TABLE conversations ADD COLUMN IF NOT EXISTS skill_names JSON DEFAULT NULL",

    # conversation_messages 表
    "ALTER TABLE conversation_messages ADD COLUMN IF NOT EXISTS context_text TEXT",

    # ai_analyses 已迁移到腾讯云，删除阿里云上的跨库 FK 约束（如存在）
    "DO $$ BEGIN IF EXISTS (SELECT FROM pg_tables WHERE tablename='ai_analyses') THEN "
    "ALTER TABLE ai_analyses DROP CONSTRAINT IF EXISTS ai_analyses_literature_id_fkey; END IF; END $$",
]


async def init_tencent_db():
    """初始化腾讯云数据库（文献相关表）"""
    async with tencent_engine.begin() as conn:
        await conn.run_sync(TencentBase.metadata.create_all)
        for sql in TENCENT_MIGRATIONS:
            await conn.execute(text(sql))
    print("✓ 腾讯云数据库（文献相关）初始化完成")


async def init_alibaba_db():
    """初始化阿里云数据库（用户相关表）"""
    async with alibaba_engine.begin() as conn:
        await conn.run_sync(AlibabaBase.metadata.create_all)
        for sql in ALIBABA_MIGRATIONS:
            await conn.execute(text(sql))
    print("✓ 阿里云数据库（用户相关）初始化完成")


async def init_db():
    print("=" * 50)
    print("开始初始化双数据库...")
    print("=" * 50)
    await init_tencent_db()
    await init_alibaba_db()
    print("=" * 50)
    print("所有数据库表及迁移均已成功应用。")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(init_db())
