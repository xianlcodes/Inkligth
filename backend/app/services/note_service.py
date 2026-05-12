import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from sqlalchemy.orm import joinedload

from app.models.note import Note
from app.models.literature import Literature
from app.schemas.note import NoteCreate, NoteUpdate

logger = logging.getLogger(__name__)


class NoteService:

    @staticmethod
    async def create_note(db: AsyncSession, user_id: str, data: NoteCreate) -> Note:
        note = Note(
            user_id=user_id,
            literature_id=data.literature_id,
            page_number=data.page_number,
            rect_coords=data.rect_coords.model_dump(),
            quoted_text=data.quoted_text,
            content=data.content,
            note_type=data.note_type,
        )
        db.add(note)
        await db.commit()
        await db.refresh(note)
        logger.info(f"Note created: {note.id}, user: {user_id}, literature: {data.literature_id}")
        return note

    @staticmethod
    async def get_notes_by_literature(
        db: AsyncSession,
        user_id: str,
        literature_id: str,
        note_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[int, list[Note]]:
        conditions = [
            Note.user_id == user_id,
            Note.literature_id == literature_id,
        ]
        if note_type:
            conditions.append(Note.note_type == note_type)

        count_q = select(func.count()).select_from(Note).where(*conditions)
        total_result = await db.execute(count_q)
        total = total_result.scalar() or 0

        q = select(Note).options(joinedload(Note.literature)).where(*conditions).order_by(Note.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(q)
        items = list(result.unique().scalars().all())
        return total, items

    @staticmethod
    async def get_note_by_id(db: AsyncSession, note_id: str, user_id: str) -> Optional[Note]:
        q = select(Note).options(joinedload(Note.literature)).where(Note.id == note_id, Note.user_id == user_id)
        result = await db.execute(q)
        return result.unique().scalar_one_or_none()

    @staticmethod
    async def update_note(db: AsyncSession, note: Note, data: NoteUpdate) -> Note:
        if data.content is not None:
            note.content = data.content
        if data.note_type is not None:
            note.note_type = data.note_type
        await db.commit()
        await db.refresh(note, attribute_names=["content", "note_type", "created_at"])
        logger.info(f"Note updated: {note.id}")
        return note

    @staticmethod
    async def delete_note(db: AsyncSession, note: Note) -> None:
        await db.delete(note)
        await db.commit()
        logger.info(f"Note deleted: {note.id}")

    @staticmethod
    async def get_all_notes(
        db: AsyncSession,
        user_id: str,
        note_type: Optional[str] = None,
        literature_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[int, list[Note]]:
        conditions = [Note.user_id == user_id]
        if note_type:
            conditions.append(Note.note_type == note_type)
        if literature_id:
            conditions.append(Note.literature_id == literature_id)

        count_q = select(func.count()).select_from(Note).where(*conditions)
        total_result = await db.execute(count_q)
        total = total_result.scalar() or 0

        q = (
            select(Note)
            .options(joinedload(Note.literature))
            .where(*conditions)
            .order_by(Note.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(q)
        items = list(result.unique().scalars().all())
        return total, items