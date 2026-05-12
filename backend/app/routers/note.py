import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.note import NoteCreate, NoteUpdate, NoteResponse, NoteListResponse
from app.services.note_service import NoteService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["notes"])


def _note_to_response(note, literature_title: Optional[str] = None) -> NoteResponse:
    return NoteResponse(
        id=note.id,
        user_id=note.user_id,
        literature_id=note.literature_id,
        literature_title=literature_title,
        page_number=note.page_number,
        rect_coords=note.rect_coords,
        quoted_text=note.quoted_text,
        content=note.content,
        note_type=note.note_type,
        created_at=note.created_at,
    )


@router.post("", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
async def create_note(
    data: NoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note = await NoteService.create_note(db, str(current_user.id), data)
    return _note_to_response(note)


@router.get("", response_model=NoteListResponse)
async def list_notes(
    literature_id: Optional[str] = Query(None, description="文献 ID（可选，不传则查全部）"),
    note_type: Optional[str] = Query(None, description="笔记类型筛选"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    total, items = await NoteService.get_all_notes(
        db, str(current_user.id), note_type=note_type, literature_id=literature_id, skip=skip, limit=limit
    )
    return NoteListResponse(
        total=total,
        items=[_note_to_response(item, literature_title=item.literature.title if item.literature else None) for item in items],
    )


@router.get("/{note_id}", response_model=NoteResponse)
async def get_note(
    note_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note = await NoteService.get_note_by_id(db, note_id, str(current_user.id))
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="笔记不存在")
    return _note_to_response(note, literature_title=note.literature.title if note.literature else None)


@router.patch("/{note_id}", response_model=NoteResponse)
async def update_note(
    note_id: str,
    data: NoteUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note = await NoteService.get_note_by_id(db, note_id, str(current_user.id))
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="笔记不存在")
    updated = await NoteService.update_note(db, note, data)
    return _note_to_response(updated, literature_title=updated.literature.title if updated.literature else None)


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    note_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note = await NoteService.get_note_by_id(db, note_id, str(current_user.id))
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="笔记不存在")
    await NoteService.delete_note(db, note)