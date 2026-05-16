import asyncio
import os
import sys
from sqlalchemy import select, update
from app.db.database import async_session_factory
from app.models.literature import Literature
from app.services.storage_service import StorageService


async def backfill():
    async with async_session_factory() as db:
        result = await db.execute(
            select(Literature).where(Literature.file_size.is_(None))
        )
        literatures = result.scalars().all()

        if not literatures:
            print("No literatures need backfill.")
            return

        print(f"Found {len(literatures)} literatures with NULL file_size")

        updated = 0
        missing_files = 0
        affected_users = set()

        for lit in literatures:
            if os.path.exists(lit.file_path):
                file_size = os.path.getsize(lit.file_path)
                lit.file_size = file_size
                affected_users.add(lit.user_id)
                updated += 1
                print(f"  [{lit.id[:8]}] {lit.title}: {file_size} bytes ({file_size / (1024*1024):.2f} MB)")
            else:
                missing_files += 1
                print(f"  [{lit.id[:8]}] {lit.title}: FILE NOT FOUND at {lit.file_path}")

        await db.commit()
        print(f"\nUpdated {updated} literatures, {missing_files} files missing.")

        for user_id in affected_users:
            await StorageService.recalculate_used_space(db, user_id)
            print(f"  Recalculated used_space for user {user_id}")


if __name__ == "__main__":
    asyncio.run(backfill())