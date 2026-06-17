import asyncio
import json
import logging
import os
import re
import shutil
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status, UploadFile, File, Form, Query
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
    background_tasks: BackgroundTasks,
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

    # ---------------------------------------------------------------
    # 1. Check storage space
    # ---------------------------------------------------------------
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

    # ---------------------------------------------------------------
    # 2. Extract first 3 pages text for fast metadata
    #    Priority: AI > raw_filename > heuristic (last resort)
    # ---------------------------------------------------------------
    first_pages_text = LiteratureService.extract_text_from_pdf(output_path, max_pages=3)
    title = raw_filename
    authors = None
    abstract = None

    if first_pages_text:
        # ---------------------------------------------------------------
        # 3a. Heuristic abstract extraction (fallback)
        # ---------------------------------------------------------------
        heuristic_abstract = LiteratureService.extract_abstract_from_text(first_pages_text, file_path=output_path)

        # ---------------------------------------------------------------
        # 3b. AI extraction (primary method, short 8s timeout)
        #     Extracts title + authors + abstract in one call
        # ---------------------------------------------------------------
        ai_title = None
        ai_authors = None
        ai_abstract = None
        try:
            from app.core.ai_client import has_user_ai_engine
            has_engine = await has_user_ai_engine(str(current_user.id))
        except Exception:
            has_engine = False

        if has_engine:
            try:
                from app.core.ai_client import get_cached_user_ai_client_and_model
                ai_client, model = await get_cached_user_ai_client_and_model(None, str(current_user.id))
                if ai_client:
                    snippet = first_pages_text[:3000]
                    response = await asyncio.wait_for(
                        ai_client.chat.completions.create(
                            model=model,
                            messages=[{"role": "user", "content":
                                "Extract the title, authors, and abstract from this academic paper text.\n"
                                "Respond with exactly three lines:\n"
                                "Title: <the exact paper title>\n"
                                "Authors: <all author names, comma-separated>\n"
                                "Abstract: <the complete abstract text>\n\n"
                                f"Paper text:\n{snippet}"}],
                            temperature=0.1,
                            max_tokens=1000,
                        ),
                        timeout=8,
                    )
                    content = response.choices[0].message.content or ""
                    if content:
                        m = re.search(r"Title[:\s]+(.+)", content, re.IGNORECASE | re.DOTALL)
                        if m:
                            ai_title = m.group(1).strip().strip('"\'*\n ')
                            ai_title = ai_title.split("\n")[0].strip()[:300]
                        m = re.search(r"Authors[:\s]+(.+)", content, re.IGNORECASE | re.DOTALL)
                        if m:
                            ai_authors = m.group(1).strip().strip('"\'*\n ')[:300]
                        m = re.search(r"Abstract[:\s]+(.+)", content, re.IGNORECASE | re.DOTALL)
                        if m:
                            ai_abstract = m.group(1).strip().strip('"\'*\n ')
                            ai_abstract = re.split(r"\n\s*(?:Keywords|Index\s+Terms|CCS\s+Concepts)\s*[:：]", ai_abstract, maxsplit=1, flags=re.IGNORECASE)[0].strip()[:5000]
            except asyncio.TimeoutError:
                logger.warning(f"AI extraction timed out (8s), using filename as title")
            except Exception as e:
                logger.warning(f"AI extraction failed: {e}")

        if ai_title and len(ai_title) > 5:
            title = ai_title
            authors = ai_authors
        # else: title stays as raw_filename (recognizable)

        # AI abstract takes priority, fall back to heuristic
        if ai_abstract and len(ai_abstract) > 20:
            abstract = ai_abstract
        elif heuristic_abstract:
            abstract = heuristic_abstract

        # ---------------------------------------------------------------
        # 3c. Font-size-aware heuristic title extraction
        #     Uses font size as primary signal: the paper title is almost
        #     always the largest text on the first page. No API key needed.
        #     Only fires when AI didn't give a good title.
        # ---------------------------------------------------------------
        if (not ai_title or len(ai_title) <= 5):
            font_text, font_sizes = LiteratureService._extract_first_page_font_sizes(output_path)
            if font_text:
                h_title = LiteratureService.extract_title_from_text(font_text, font_sizes=font_sizes)
                if h_title:
                    title = h_title
                    h_authors = LiteratureService.extract_authors_from_text(font_text, h_title)
                    if h_authors:
                        authors = h_authors
                    if not abstract:
                        h_abstract = LiteratureService.extract_abstract_from_text(font_text)
                        if h_abstract:
                            abstract = h_abstract
                    if not abstract:
                        # Some journals have no "Abstract" header — text between
                        # author lines and "1. Introduction" is the abstract
                        flines = font_text.split('\n')
                        intro_idx = -1
                        for i, line in enumerate(flines):
                            if re.match(
                                r'^(?:\d+\.\s|INTRODUCTION|KEYWORDS)',
                                line.strip(), re.IGNORECASE
                            ):
                                intro_idx = i
                                break
                        if intro_idx > 4:
                            collected = []
                            for i in range(3, intro_idx):
                                ln = flines[i].strip()
                                if ln and len(ln) > 15:
                                    collected.append(ln)
                            if collected:
                                abstract = ' '.join(collected)[:2000].replace('\x00', '')

        # ---------------------------------------------------------------
        # 3d. DOI/arXiv API lookup (free, no API key needed)
        #     Fills gaps when AI unavailable or failed
        # ---------------------------------------------------------------
        if (not ai_title or len(ai_title) <= 5) and not (title == raw_filename and len(raw_filename) >= 3):
            try:
                ids = LiteratureService.extract_identifiers(first_pages_text)
                api_meta = {}
                if ids.get("doi"):
                    api_meta = await LiteratureService.fetch_crossref_metadata(ids["doi"])
                elif ids.get("arxiv"):
                    api_meta = await LiteratureService.fetch_arxiv_metadata(ids["arxiv"])
                if api_meta and api_meta.get("title"):
                    title = api_meta["title"]
                    authors = api_meta.get("authors")
                    if not abstract and api_meta.get("abstract"):
                        abstract = api_meta["abstract"]
                    logger.info(f"DOI/arXiv lookup filled metadata: {ids.get('doi') or ids.get('arxiv')}")
            except Exception as e:
                logger.warning(f"DOI/arXiv lookup failed: {e}")

        # ---------------------------------------------------------------
        # 3d. Heuristic title/authors (last resort only if raw_filename is empty)
        # ---------------------------------------------------------------
        if title == raw_filename and (not raw_filename or len(raw_filename) < 3):
            h_title = LiteratureService.extract_title_from_text(first_pages_text)
            if h_title:
                title = h_title
                h_authors = LiteratureService.extract_authors_from_text(first_pages_text, h_title)
                if h_authors:
                    authors = h_authors

    # ---------------------------------------------------------------
    # 3e. Dead-simple abstract text search (last resort)
    #     Simple string search works when regex fails on messy PDF text
    # ---------------------------------------------------------------
    if not abstract and first_pages_text:
        idx = first_pages_text.lower().find("abstract")
        if idx >= 0:
            start = idx + 8  # skip past "abstract"
            while start < len(first_pages_text) and first_pages_text[start] in ' :\n\r\t–—':
                start += 1
            snippet = first_pages_text[start:start + 2000]
            m = re.search(
                r'\n\s*(?:INTRODUCTION|KEYWORDS|REFERENCES?|BACKGROUND|METHOD|DISCUSSION|CONCLUSION)\b',
                snippet, re.IGNORECASE
            )
            if m:
                snippet = snippet[:m.start()]
            abstract_text = snippet.strip().replace('\x00', '')
            if len(abstract_text) > 20:
                words = abstract_text.split()
                if len(words) > 250:
                    abstract_text = " ".join(words[:250]) + "..."
                abstract = abstract_text[:2000]

    # ---------------------------------------------------------------
    # 4. Create Literature record with best available metadata
    # ---------------------------------------------------------------
    from app.schemas.literature import LiteratureCreate

    literature = await LiteratureService.create_literature(
        db=db,
        user_id=str(current_user.id),
        file=None,
        literature_in=LiteratureCreate(
            title=title,
            authors=authors,
            abstract=abstract,
            raw_text=first_pages_text or "",
            file_path=output_path,
            file_size=file_size,
            folder_id=meta.get("folder_id"),
        ),
    )

    # ---------------------------------------------------------------
    # 5. Background: AI refinement (longer timeout) + full-text + indexing
    # ---------------------------------------------------------------
    background_tasks.add_task(
        _post_process_upload,
        literature_id=str(literature.id),
        user_id=str(current_user.id),
        file_path=output_path,
        first_pages_text=first_pages_text or "",
    )

    # ---------------------------------------------------------------
    # 6. Finalize storage + commit
    # ---------------------------------------------------------------
    await StorageService.add_used_space(user_db, str(current_user.id), file_size)
    await db.commit()
    await user_db.commit()

    logger.info(f"Chunks merged: {upload_id} -> {output_filename}, literature: {literature.id}")
    return ChunkMergeResponse(
        literature_id=literature.id,
        task_id=None,
        message="文件上传完成",
    )


async def _post_process_upload(literature_id: str, user_id: str, file_path: str, first_pages_text: str):
    """Background enrichment: AI title/authors extraction + full-text chunk indexing.

    Runs after the upload response has been sent to the user.
    Uses its own DB sessions (request sessions are closed after response).
    """
    from app.db.database import TencentSessionLocal
    from app.routers.literature import _split_paragraphs, _index_chunks

    try:
        # ---------------------------------------------------------------
        # Phase A: AI metadata extraction (longer 30s timeout in background)
        # Only runs if user has a real AI engine configured.
        # ---------------------------------------------------------------
        ai_title = None
        ai_authors = None

        try:
            from app.core.ai_client import has_user_ai_engine
            has_engine = await has_user_ai_engine(user_id)
        except Exception:
            has_engine = False

        if has_engine and first_pages_text:
            from app.core.ai_client import get_cached_user_ai_client_and_model
            ai_client, model = await get_cached_user_ai_client_and_model(None, user_id)
            snippet = first_pages_text[:3000]
            try:
                response = await ai_client.chat.completions.create(
                    model=model,
                    messages=[{
                        "role": "user",
                        "content": (
                            "Extract the title and authors from this academic paper text.\n"
                            "Respond with exactly two lines:\n"
                            "Title: <the exact paper title>\n"
                            "Authors: <all author names, comma-separated>\n\n"
                            f"Paper text:\n{snippet}"
                        )
                    }],
                    temperature=0.1,
                    max_tokens=500,
                    timeout=30,
                )
                content = response.choices[0].message.content or ""
                if content:
                    m = re.search(r"Title[:\s]+(.+)", content, re.IGNORECASE | re.DOTALL)
                    if m:
                        ai_title = m.group(1).strip().strip('"\'*\n ')
                        ai_title = ai_title.split("\n")[0].strip()[:300]
                    m = re.search(r"Authors[:\s]+(.+)", content, re.IGNORECASE | re.DOTALL)
                    if m:
                        ai_authors = m.group(1).strip().strip('"\'*\n ')[:300]
            except Exception as e:
                logger.warning(f"[background] AI extraction failed: {e}")

        # ---------------------------------------------------------------
        # Phase B: Update literature with AI metadata + full text
        # ---------------------------------------------------------------
        async with TencentSessionLocal() as db:
            lit = await LiteratureService.get_literature_by_id(db, literature_id, user_id)
            if not lit:
                logger.warning(f"[background] Literature {literature_id} not found")
                return

            needs_update = False

            # AI title (only replace if current title looks like filename)
            if ai_title and len(ai_title) > 5:
                current_title = lit.title or ""
                looks_like_filename = (
                    not current_title
                    or current_title == current_title.split(".", 1)[0]  # raw filename (no extension in DB but still)
                    or current_title.count(" ") < 3
                    or current_title[0].islower()
                    or any(kw in current_title.lower() for kw in [".pdf", "untitled", "unknown"])
                )
                if looks_like_filename:
                    lit.title = ai_title
                    needs_update = True
                    logger.info(f"[background] Title updated via AI: {ai_title[:80]}")

            # AI authors (replace if current is empty)
            if ai_authors and (not lit.authors or len(ai_authors) > 5):
                lit.authors = ai_authors
                needs_update = True
                logger.info(f"[background] Authors updated via AI: {ai_authors[:80]}")

            # Extract full text for chunk indexing
            if not lit.raw_text or len(lit.raw_text) < 5000:
                full_text = LiteratureService.extract_text_from_pdf(file_path)
                if full_text:
                    lit.raw_text = full_text
                    needs_update = True
                    logger.info(f"[background] Full text extracted: {len(full_text)} chars")

            # Heuristic abstract extraction (fallback when AI is unavailable/failed)
            if not lit.abstract and lit.raw_text:
                h_abstract = LiteratureService.extract_abstract_from_text(lit.raw_text)
                if h_abstract:
                    lit.abstract = h_abstract
                    needs_update = True
                    logger.info(f"[background] Abstract extracted via heuristic: {len(h_abstract)} chars")
                else:
                    # Last resort: simple text search for "abstract"
                    idx = lit.raw_text.lower().find("abstract")
                    if idx >= 0:
                        start = idx + 8
                        text = lit.raw_text
                        while start < len(text) and text[start] in ' :\n\r\t–—':
                            start += 1
                        snippet = text[start:start + 2000]
                        m = re.search(
                            r'\n\s*(?:INTRODUCTION|KEYWORDS|REFERENCES?|BACKGROUND|METHOD|DISCUSSION|CONCLUSION)\b',
                            snippet, re.IGNORECASE
                        )
                        if m:
                            snippet = snippet[:m.start()]
                        abstract_text = snippet.strip().replace('\x00', '')
                        if len(abstract_text) > 20:
                            words = abstract_text.split()
                            if len(words) > 250:
                                abstract_text = " ".join(words[:250]) + "..."
                            lit.abstract = abstract_text[:2000]
                            needs_update = True
            if needs_update:
                await db.commit()
                await db.refresh(lit)

            # ---------------------------------------------------------------
            # Phase C: Index chunks from full text
            # ---------------------------------------------------------------
            if lit.raw_text:
                try:
                    paragraphs = _split_paragraphs(lit.raw_text)
                    await _index_chunks(literature_id, paragraphs)
                    logger.info(f"[background] Indexed {len(paragraphs)} chunks for {literature_id}")
                except Exception as e:
                    logger.warning(f"[background] Chunk indexing failed: {e}")

    except Exception as e:
        logger.error(f"[background] Post-process failed for {literature_id}: {e}", exc_info=True)


def _cleanup_session(session_path: str):
    try:
        shutil.rmtree(session_path, ignore_errors=True)
    except Exception as e:
        logger.warning(f"Failed to cleanup session {session_path}: {e}")
