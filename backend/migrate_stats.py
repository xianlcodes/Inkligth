import asyncio
from sqlalchemy import text
from app.db.database import async_session_factory

async def migrate():
    async with async_session_factory() as db:
        conn = await db.connection()

        await conn.execute(text("""
            ALTER TABLE literatures
            ADD COLUMN IF NOT EXISTS total_pages INTEGER,
            ADD COLUMN IF NOT EXISTS last_read_page INTEGER,
            ADD COLUMN IF NOT EXISTS total_reading_time_seconds INTEGER DEFAULT 0
        """))

        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS reading_records (
                id VARCHAR PRIMARY KEY,
                user_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                literature_id VARCHAR NOT NULL REFERENCES literatures(id) ON DELETE CASCADE,
                record_date DATE NOT NULL,
                pages_read INTEGER DEFAULT 0,
                reading_time_seconds INTEGER DEFAULT 0,
                last_page INTEGER,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))

        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_reading_records_user_date
            ON reading_records(user_id, record_date)
        """))

        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_reading_records_literature
            ON reading_records(literature_id)
        """))

        await db.commit()
        print("Migration completed: added reading stats fields and reading_records table")

asyncio.run(migrate())