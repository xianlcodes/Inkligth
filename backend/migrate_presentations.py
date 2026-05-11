import asyncio
from app.db.database import async_session_factory
from sqlalchemy import text


async def migrate():
    async with async_session_factory() as db:
        conn = await db.connection()
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS presentations (
                id VARCHAR PRIMARY KEY,
                user_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                literature_id VARCHAR REFERENCES literatures(id) ON DELETE SET NULL,
                literature_title VARCHAR(500),
                slides JSONB NOT NULL DEFAULT '[]',
                slide_count VARCHAR,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_presentations_user_id
            ON presentations(user_id)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_presentations_literature_id
            ON presentations(literature_id)
        """))
        await db.commit()
        print("Migration completed: presentations table created")


if __name__ == "__main__":
    asyncio.run(migrate())