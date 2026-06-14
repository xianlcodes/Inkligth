import json
import logging
import os
import shutil
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db, get_user_db
from app.core.deps import get_current_user
from app.services.literature_service import LiteratureService, UPLOAD_DIR
from app.services.storage_service import StorageService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/upload", tags=["upload"])

CHUNK_DIR = "chunks"
CHUNK_CLEANUP_HOURS = 24


def _ensure_chunk_dir():
    os.makedirs(CHUNK_DIR, exist_ok=True)


def _session_dir(upload_id: str) -> str:
    return os.path.join(CHUNK_DIR, upload_id)


def _session_meta_path(upload_id: str) -> str:
    return os.path.join(_session_dir(upload_id), "meta.json")


class ChunkInitResponse(BaseModel):
    upload_id: str
    chunk_size: int


class ChunkUploadResponse(BaseModel):
    upload_id: str
    chunk_index: int
    received: int


class ChunkMergeResponse(BaseModel):
    literature_id: str
    task_id: Optional[str] = None
    message: str


@router.post("/chunks/init", response_model=ChunkInitResponse)
async def init_chunk_upload(
    filename: str = Form(...),
    file_size: int = Form(...),
    total_chunks: int = Form(..., ge=1, le=200),
    chunk_size: int = Form(...),
    folder_id: Optional[str] = Form(None),
    current_user=Depends(get_current_user),
):
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only PDF files are allowed")

    if file_size > 52_428_800:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="文件大小不能超过 50MB")

    _ensure_chunk_dir()
    upload_id = str(uuid.uuid4())
    session_path = _session_dir(upload_id)
    os.makedirs(session_path, exist_ok=True)

    meta = {
        "upload_id": upload_id,
        "filename": filename,
        "file_size": file_size,
        "total_chunks": total_chunks,
        "chunk_size": chunk_size,
        "folder_id": folder_id,
        "user_id": str(current_user.id),
        "created_at": datetime.utcnow().isoformat(),
        "received_chunks": [],
    }
    with open(_session_meta_path(upload_id), "w", encoding="utf-8") as f:
        json.dump(meta, f)

    logger.info(f"Chunk upload session init: {upload_id}, file: {filename}, chunks: {total_chunks}")
    return ChunkInitResponse(upload_id=upload_id, chunk_size=chunk_size)


@router.post("/chunks/{upload_id}", response_model=ChunkUploadResponse)
async def upload_chunk(
    upload_id: str,
    chunk_index: int = Form(..., ge=0),
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
):
    meta_path = _session_meta_path(upload_id)
    if not os.path.exists(meta_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="上传会话不存在或已过期")

    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    if str(current_user.id) != meta.get("user_id"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问此上传会话")

    if chunk_index >= meta["total_chunks"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"chunk_index {chunk_index} 超出范围")

    session_path = _session_dir(upload_id)
    chunk_path = os.path.join(session_path, f"chunk_{chunk_index:05d}")

    content = await file.read()
    with open(chunk_path, "wb") as f:
        f.write(content)

    if chunk_index not in meta["received_chunks"]:
        meta["received_chunks"].append(chunk_index)
        meta["received_chunks"].sort()

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f)

    received_count = len(meta["received_chunks"])
    logger.info(f"Chunk received: {upload_id}, index: {chunk_index}, progress: {received_count}/{meta['total_chunks']}")
    return ChunkUploadResponse(upload_id=upload_id, chunk_index=chunk_index, received=received_count)


@router.post("/chunks/{upload_id}/merge", response_model=ChunkMergeResponse)
async def merge_chunks(
    upload_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    user_db: AsyncSession = Depends(get_user_db),
):
    meta_path = _session_meta_path(upload_id)
    if not os.path.exists(meta_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="上传会话不存在或已过期")

    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    if str(current_user.id) != meta.get("user_id"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问此上传会话")

    total = meta["total_chunks"]
    received = set(meta["received_chunks"])
    missing = [i for i in range(total) if i not in received]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"缺少 {len(missing)} 个分片: {missing[:10]}{'...' if len(missing) > 10 else ''}",
        )

    session_path = _session_dir(upload_id)
    LiteratureService.ensure_upload_dir()
    output_filename = f"{uuid.uuid4()}.pdf"
    output_path = os.path.join(UPLOAD_DIR, output_filename)

    with open(output_path, "wb") as out:
        for i in range(total):
            chunk_path = os.path.join(session_path, f"chunk_{i:05d}")
            if not os.path.exists(chunk_path):
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"分片 {i} 文件丢失")
            with open(chunk_path, "rb") as cin:
                out.write(cin.read())

    _cleanup_session(session_path)

    raw_filename = meta["filename"].rsplit(".", 1)[0]
    file_size = os.path.getsize(output_path)

    has_space = await StorageService.check_space_available(user_db, str(current_user.id), file_size)
    if not has_space:
        storage = await StorageService.get_storage(user_db, str(current_user.id))
        remaining = storage.total_space - storage.used_space
        os.remove(output_path)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INSUFFICIENT_STORAGE",
                "message": "存储空间不足",
                "remaining_bytes": remaining,
                "needed_bytes": file_size,
                "total_bytes": storage.total_space,
            },
        )

    from app.schemas.literature import LiteratureCreate

    literature = await LiteratureService.create_literature(
        db=db,
        user_id=str(current_user.id),
        file=None,
        literature_in=LiteratureCreate(
            title=raw_filename,
            file_path=output_path,
            file_size=file_size,
            raw_text=None,
            folder_id=meta.get("folder_id"),
        ),
    )

    await StorageService.add_used_space(user_db, str(current_user.id), file_size)
    await db.commit()
    await user_db.commit()

    import asyncio as _asyncio
    _asyncio.create_task(
        _dispatch_to_process_uploaded(
            literature_id=literature.id,
            file_path=output_path,
            raw_filename=raw_filename,
            folder_id=meta.get("folder_id"),
            user_id=str(current_user.id),
        )
    )

    logger.info(f"Chunks merged: {upload_id} -> {output_filename}, literature: {literature.id}")
    return ChunkMergeResponse(
        literature_id=literature.id,
        task_id=None,
        message="文件合并完成，正在后台提取元数据",
    )


async def _dispatch_to_process_uploaded(
    literature_id: str,
    file_path: str,
    raw_filename: str,
    folder_id: Optional[str],
    user_id: str,
):
    from app.routers.literature import _process_uploaded_literature
    await _process_uploaded_literature(
        literature_id=literature_id,
        file_path=file_path,
        raw_filename=raw_filename,
        folder_id=folder_id,
        user_id=user_id,
    )


def _cleanup_session(session_path: str):
    try:
        shutil.rmtree(session_path, ignore_errors=True)
    except Exception as e:
        logger.warning(f"Failed to cleanup session {session_path}: {e}")
