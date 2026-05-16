import asyncio
import logging
import os
import re
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status, UploadFile, File, Query
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.core.deps import get_current_user
from app.core.ai_client import get_user_ai_client, get_user_default_model
from app.core.ai_providers.translator import OpenAITranslator, beautify_translation_error
from app.core.ai_providers.analyzer import OpenAIAnalyzer
from app.core.ai_providers.outline_generator import OutlineGenerator
from app.services.literature_service import LiteratureService
from app.services.analysis_service import AnalysisService
from app.services.search_service import SearchService
from app.services.translation_service import TranslationService
from app.services.storage_service import StorageService
from app.schemas.literature import LiteratureResponse, LiteratureCreate, LiteratureUpdate, LiteratureListResponse
from app.schemas.analysis import AnalysisResponse, AnalyzeResponse
from app.utils.task_store import task_store, TaskStatus
from app.utils.compression import compress_json

logger = logging.getLogger(__name__)
router = APIRouter(tags=["literatures"])


@router.post("", response_model=LiteratureResponse)
async def upload_literature(
    file: UploadFile = File(...),
    folder_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    background_tasks: BackgroundTasks = None,
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only PDF files are allowed")

    file_content = await file.read()
    file_size = len(file_content)
    await file.seek(0)

    has_space = await StorageService.check_space_available(db, current_user.id, file_size)
    if not has_space:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="存储空间不足")

    file_path = LiteratureService.save_upload_file(file)
    raw_filename = file.filename.rsplit(".", 1)[0]

    literature = await LiteratureService.create_literature(
        db=db,
        user_id=current_user.id,
        file=file,
        literature_in=LiteratureCreate(
            title=raw_filename,
            file_path=file_path,
            raw_text=None,
            folder_id=folder_id,
        ),
    )

    literature.file_size = file_size
    await StorageService.add_used_space(db, current_user.id, file_size)
    await db.commit()

    if background_tasks:
        background_tasks.add_task(
            _process_uploaded_literature,
            literature_id=literature.id,
            file_path=file_path,
            raw_filename=raw_filename,
            folder_id=folder_id,
            user_id=str(current_user.id),
        )

    return literature


@router.get("", response_model=LiteratureListResponse)
async def list_literatures(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    title: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    sort_by_year: Optional[str] = Query(None),
    folder_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    total, items = await LiteratureService.get_literatures_by_user(
        db, current_user.id, skip=skip, limit=limit, title=title, status=status, sort_by_year=sort_by_year, folder_id=folder_id
    )
    return LiteratureListResponse(total=total, items=items)


@router.get("/{literature_id}", response_model=LiteratureResponse)
async def get_literature(
    literature_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    literature = await LiteratureService.get_literature_by_id(db, literature_id, current_user.id)
    if not literature:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文献不存在")
    return literature


@router.patch("/{literature_id}", response_model=LiteratureResponse)
async def update_literature(
    literature_id: str,
    literature_in: LiteratureUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    literature = await LiteratureService.get_literature_by_id(db, literature_id, current_user.id)
    if not literature:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文献不存在")
    updated = await LiteratureService.update_literature(db, literature, literature_in)
    return updated


class DeleteResponse(BaseModel):
    message: str


@router.delete("/{literature_id}", response_model=DeleteResponse)
async def delete_literature(
    literature_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    literature = await LiteratureService.get_literature_by_id(db, literature_id, current_user.id)
    if not literature:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文献不存在")
    file_size = literature.file_size or 0
    await LiteratureService.delete_literature(db, literature)
    if file_size > 0:
        await StorageService.release_used_space(db, current_user.id, file_size)
    logger.info(f"Literature deleted: {literature_id} by user {current_user.id}")
    return DeleteResponse(message="文献已删除")


@router.get("/{literature_id}/file")
async def get_literature_file(
    literature_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    literature = await LiteratureService.get_literature_by_id(db, literature_id, current_user.id)
    if not literature:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文献不存在")
    if not os.path.exists(literature.file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件不存在")
    return FileResponse(
        path=literature.file_path,
        media_type="application/pdf",
        filename=os.path.basename(literature.file_path),
    )


PER_PARAGRAPH_TIMEOUT = 60.0
MAX_CONCURRENT = 5
MAX_RETRIES = 2
RETRY_BACKOFF_BASE = 2.0
DB_COMMIT_INTERVAL = 3

_active_translations: dict[str, str] = {}
_active_translations_lock = asyncio.Lock()
_cancellation_flags: set[str] = set()


def request_cancellation(task_id: str):
    _cancellation_flags.add(task_id)


def _is_cancelled(task_id: str) -> bool:
    return task_id in _cancellation_flags


def _cleanup_active(literature_id: str):
    return _active_translations.pop(literature_id, None)


class FullTranslateResponse(BaseModel):
    task_id: str
    message: str


@router.post("/{literature_id}/translate/full", response_model=FullTranslateResponse)
async def start_full_translate(
    literature_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    literature = await LiteratureService.get_literature_by_id(db, literature_id, current_user.id)
    if not literature:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文献不存在")

    if not literature.raw_text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该文献暂无文本内容，无法翻译")

    async with _active_translations_lock:
        existing_task_id = _active_translations.get(literature_id)
        if existing_task_id:
            existing_task = await task_store.get_task(existing_task_id)
            if existing_task and existing_task.status in (TaskStatus.PENDING, TaskStatus.RUNNING):
                return FullTranslateResponse(
                    task_id=existing_task_id,
                    message="翻译任务正在进行中，请查看进度",
                )
            else:
                _cleanup_active(literature_id)

        if literature.translated_text:
            return FullTranslateResponse(
                task_id="cached",
                message="已有缓存译文",
            )

        task = await task_store.create_task("full_translate")
        await task_store.update_task(
            task.task_id,
            status=TaskStatus.RUNNING,
            progress=0,
            total=0,
        )
        _active_translations[literature_id] = task.task_id

    background_tasks.add_task(
        _run_full_translate,
        task_id=task.task_id,
        literature_id=literature_id,
        user_id=current_user.id,
    )

    logger.info(f"Full translate task started: {task.task_id}, literature: {literature_id}")
    return FullTranslateResponse(
        task_id=task.task_id,
        message="全文翻译任务已启动",
    )


class DeleteTranslationResponse(BaseModel):
    message: str


@router.delete("/{literature_id}/translate/full", response_model=DeleteTranslationResponse)
async def delete_full_translate(
    literature_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    literature = await LiteratureService.get_literature_by_id(db, literature_id, current_user.id)
    if not literature:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文献不存在")

    async with _active_translations_lock:
        _cleanup_active(literature_id)

    literature.translated_text = None
    literature.translated_at = None
    await db.commit()
    await TranslationService.delete_translations_by_literature(db, literature_id)
    await db.commit()
    logger.info(f"Full translation cleared for literature: {literature_id}")
    return DeleteTranslationResponse(message="翻译结果已删除")


async def _translate_one(
    translator: OpenAITranslator,
    index: int,
    text: str,
    sem: asyncio.Semaphore,
    progress_lock: asyncio.Lock,
    progress_counter: dict,
    task_id: str,
    total: int,
) -> dict:
    async with sem:
        if _is_cancelled(task_id):
            return {"paragraph_index": index, "original": text, "translated": "[已取消]"}
        if not text.strip():
            return {"paragraph_index": index, "original": text, "translated": ""}

        last_error = ""
        for attempt in range(MAX_RETRIES + 1):
            try:
                translated = await translator.translate(
                    text=text,
                    source_lang="en",
                    target_lang="zh",
                    timeout=PER_PARAGRAPH_TIMEOUT,
                )
                break
            except Exception as e:
                last_error = str(e)
                err_lower = last_error.lower()
                is_retryable = any(k in err_lower for k in ("429", "rate limit", "timeout", "connection", "reset"))
                if is_retryable and attempt < MAX_RETRIES:
                    delay = RETRY_BACKOFF_BASE ** attempt
                    logger.warning(
                        "Paragraph %s attempt %s/%s failed: %s, retrying in %.1fs",
                        index, attempt + 1, MAX_RETRIES + 1, e, delay,
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        "Paragraph %s translation failed after %s attempts: %s",
                        index, attempt + 1, e,
                    )
                    break
        else:
            translated = f"[翻译失败: {beautify_translation_error(last_error)}]"

    async with progress_lock:
        progress_counter["done"] += 1
        await task_store.update_task(task_id, progress=progress_counter["done"])

    return {"paragraph_index": index, "original": text, "translated": translated}


async def _run_full_translate(task_id: str, literature_id: str, user_id: str):
    from app.db.database import async_session_factory

    t_start = asyncio.get_event_loop().time()

    try:
        async with async_session_factory() as db:
            literature = await LiteratureService.get_literature_by_id(db, literature_id, user_id)
            if not literature or not literature.raw_text:
                await task_store.update_task(task_id, status=TaskStatus.FAILED, error="文献不存在或无文本内容")
                _cleanup_active(literature_id)
                return

            raw_text = literature.raw_text
            paragraphs = _split_paragraphs(raw_text)
            total = len(paragraphs)

            await task_store.update_task(task_id, total=total, progress=0)

            await TranslationService.cleanup_expired_translations(db)

            ai_client = await get_user_ai_client(db, user_id)
            model = await get_user_default_model(db, user_id)
            translator = OpenAITranslator(client=ai_client, model=model)

            sem = asyncio.Semaphore(MAX_CONCURRENT)
            progress_lock = asyncio.Lock()
            progress_counter = {"done": 0}

            coros = [
                _translate_one(
                    translator=translator,
                    index=i,
                    text=para,
                    sem=sem,
                    progress_lock=progress_lock,
                    progress_counter=progress_counter,
                    task_id=task_id,
                    total=total,
                )
                for i, para in enumerate(paragraphs)
            ]

            translated_paragraphs: list[dict] = [{}] * total
            last_commit_count = 0

            for coro in asyncio.as_completed(coros):
                result = await coro
                idx = result["paragraph_index"]
                translated_paragraphs[idx] = result

                if _is_cancelled(task_id):
                    logger.info(f"Full translate task cancelled by user: {task_id}")
                    if progress_counter["done"] > last_commit_count:
                        valid = [p for p in translated_paragraphs if p and p.get("translated")]
                        literature.translated_text = compress_json(valid)
                        literature.translated_at = datetime.utcnow()
                        await db.commit()
                        await TranslationService.save_translation(
                            db, literature_id, user_id, valid,
                            engine_version=model,
                        )
                        await db.commit()
                    await task_store.update_task(
                        task_id,
                        status=TaskStatus.CANCELLED,
                        progress=progress_counter["done"],
                        error="用户取消翻译",
                    )
                    return

                if progress_counter["done"] - last_commit_count >= DB_COMMIT_INTERVAL:
                    valid = [p for p in translated_paragraphs if p and p.get("translated")]
                    literature.translated_text = compress_json(valid)
                    literature.translated_at = datetime.utcnow()
                    await db.commit()
                    last_commit_count = progress_counter["done"]
                    logger.debug(
                        "Batch commit: %s/%s paragraphs saved for task %s",
                        len(valid), total, task_id,
                    )

            literature.translated_text = compress_json(translated_paragraphs)
            literature.translated_at = datetime.utcnow()
            await db.commit()
            await TranslationService.save_translation(
                db, literature_id, user_id, translated_paragraphs,
                engine_version=model,
            )
            await db.commit()

            await task_store.update_task(
                task_id,
                status=TaskStatus.COMPLETED,
                result={"literature_id": literature_id, "paragraph_count": total},
            )
            logger.info(f"Full translate task completed: {task_id}, paragraphs: {total}")
            logger.info(
                "Full translate task %s finished in %.1fs (%d paragraphs)",
                task_id, asyncio.get_event_loop().time() - t_start, total,
            )

    except Exception as e:
        logger.error(f"Full translate task failed: {task_id}, error: {e}", exc_info=True)
        await task_store.update_task(task_id, status=TaskStatus.FAILED, error=str(e))
    finally:
        _cleanup_active(literature_id)
        _cancellation_flags.discard(task_id)


def _strip_references_section(text: str) -> str:
    ref_patterns = [
        r"\n\s*REFERENCES\s*\n",
        r"\n\s*Bibliography\s*\n",
        r"\n\s*References\s+and\s+Notes\s*\n",
        r"\n\s*Literature\s+Cited\s*\n",
        r"\n\s*Works\s+Cited\s*\n",
    ]
    for pattern in ref_patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return text[:m.start()]
    return text


async def _process_uploaded_literature(
    literature_id: str,
    file_path: str,
    raw_filename: str,
    folder_id: Optional[str],
    user_id: str,
):
    """
    Background task: extract text, run multi-tier metadata extraction,
    update literature record, and trigger chunk indexing.
    """
    from app.db.database import async_session_factory
    from app.schemas.literature import LiteratureUpdate

    logger.info(f"_process_uploaded_literature started for {literature_id}")
    try:
        # 1. Extract text from PDF
        raw_text = LiteratureService.extract_text_from_pdf(file_path)
        if not raw_text:
            logger.error(f"Failed to extract text from PDF: {file_path}")
            return

        # 2. Get AI client if available
        ai_client = None
        model = None
        try:
            async with async_session_factory() as db:
                from app.services.ai_engine_service import AIEngineService, decrypt_api_key
                from app.core.ai_providers.provider_registry import AIProviderRegistry

                engine = await AIEngineService.get_default_engine(db, user_id)
                if engine:
                    api_key = decrypt_api_key(engine.api_key)
                    registry = AIProviderRegistry()
                    adapter = registry.get_or_default(engine.provider)
                    base_url = adapter.get_openai_base_url(engine.api_base)
                    from openai import AsyncOpenAI
                    ai_client = AsyncOpenAI(base_url=base_url, api_key=api_key, timeout=300.0)
                    model = engine.default_model
        except Exception as e:
            logger.warning(f"Failed to initialize AI client for metadata extraction: {e}")

        # 3. Multi-tier metadata extraction
        metadata = await LiteratureService.extract_metadata(raw_text, ai_client=ai_client, model=model)

        # 4. Check if title is still the fallback (raw_filename) and log
        if metadata.get("title") == raw_filename or not metadata.get("title"):
            logger.warning(f"Metadata extraction yielded no better title than filename for {literature_id}")

        # 5. Update literature record
        async with async_session_factory() as db:
            existing = await LiteratureService.get_literature_by_id(db, literature_id, user_id)
            if not existing:
                logger.error(f"Literature {literature_id} not found in DB during async processing")
                return

            await LiteratureService.update_literature(
                db, existing,
                LiteratureUpdate(
                    title=metadata.get("title") or raw_filename,
                    authors=metadata.get("authors"),
                    abstract=metadata.get("abstract"),
                    year=metadata.get("year"),
                    journal=metadata.get("journal"),
                    doi=metadata.get("doi"),
                    raw_text=raw_text,
                ),
            )
            logger.info(f"Literature {literature_id} metadata updated: title='{metadata.get('title')}'")

        # 6. Trigger chunk indexing
        paragraphs = _split_paragraphs(raw_text)
        await _index_chunks(literature_id, paragraphs)
        logger.info(f"_process_uploaded_literature completed for {literature_id}")

    except Exception as e:
        logger.error(f"_process_uploaded_literature failed for {literature_id}: {e}", exc_info=True)


def _split_paragraphs(text: str) -> list[str]:
    MAX_CHARS = 4000

    text = _strip_references_section(text)

    paragraphs = []
    for block in text.split("\n\n"):
        block = block.strip()
        if not block:
            continue
        sub_blocks = [s.strip() for s in block.split("\n") if s.strip()]
        if len(sub_blocks) <= 3:
            for sb in sub_blocks:
                if len(sb) <= MAX_CHARS:
                    paragraphs.append(sb)
                else:
                    paragraphs.extend(_chunk_text(sb, MAX_CHARS))
        else:
            if len(block) <= MAX_CHARS:
                paragraphs.append(block)
            else:
                paragraphs.extend(_chunk_text(block, MAX_CHARS))

    if len(paragraphs) <= 1:
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        paragraphs = []
        current = ""
        for line in lines:
            if len(current) + len(line) > MAX_CHARS and current:
                paragraphs.append(current.strip())
                current = line
            else:
                current = current + "\n" + line if current else line
        if current.strip():
            paragraphs.append(current.strip())

    paragraphs = _merge_small_paragraphs(paragraphs)

    return paragraphs


MERGE_MIN_CHARS = 500
MERGE_TARGET_CHARS = 4000


def _merge_small_paragraphs(paragraphs: list[str]) -> list[str]:
    if len(paragraphs) <= 1:
        return paragraphs
    merged = []
    buffer = ""
    for para in paragraphs:
        if not buffer:
            buffer = para
            continue
        if len(buffer) < MERGE_MIN_CHARS or (len(buffer) + len(para) + 1) <= MERGE_TARGET_CHARS:
            buffer = buffer + "\n" + para
        else:
            merged.append(buffer)
            buffer = para
    if buffer:
        merged.append(buffer)
    return merged


def _chunk_text(text: str, max_chars: int) -> list[str]:
    chunks = []
    current = ""
    for sentence in re.split(r'(?<=[.!?])\s+(?=[A-Z])', text):
        sentence = sentence.strip()
        if not sentence:
            continue
        if len(sentence) > max_chars:
            if current:
                chunks.append(current.strip())
                current = ""
            if len(sentence) <= max_chars * 2:
                chunks.append(sentence)
            else:
                pos = 0
                while pos < len(sentence):
                    chunks.append(sentence[pos:pos + max_chars])
                    pos += max_chars
        elif len(current) + len(sentence) + 1 > max_chars and current:
            chunks.append(current.strip())
            current = sentence
        else:
            current = current + " " + sentence if current else sentence
    if current.strip():
        chunks.append(current.strip())
    if not chunks:
        chunks = [text[:max_chars]]
    return chunks


async def _index_chunks(literature_id: str, paragraphs: list[str]):
    from app.db.database import async_session_factory
    from app.services.search_service import SearchService

    async with async_session_factory() as db:
        try:
            para_dicts = [{"text": p, "page": None} for p in paragraphs if p.strip()]
            await SearchService.index_literature(db, literature_id, para_dicts)
        except Exception as e:
            logger.error("Chunk indexing failed for literature %s: %s", literature_id, e)


@router.post("/{literature_id}/analyze", response_model=AnalyzeResponse)
async def start_analyze(
    literature_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    literature = await LiteratureService.get_literature_by_id(db, literature_id, current_user.id)
    if not literature:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文献不存在")

    if not literature.raw_text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该文献暂无文本内容，无法分析")

    existing = await AnalysisService.get_analysis_by_literature(db, current_user.id, literature_id)
    if existing:
        return AnalyzeResponse(
            task_id="cached",
            message="已有缓存分析结果",
        )

    task = await task_store.create_task("analyze")
    await task_store.update_task(
        task.task_id,
        status=TaskStatus.RUNNING,
        progress=0,
        total=1,
    )

    background_tasks.add_task(
        _run_analyze,
        task_id=task.task_id,
        literature_id=literature_id,
        user_id=current_user.id,
    )

    logger.info(f"Analyze task started: {task.task_id}, literature: {literature_id}")
    return AnalyzeResponse(
        task_id=task.task_id,
        message="AI 分析任务已启动",
    )


@router.get("/{literature_id}/analysis", response_model=AnalysisResponse)
async def get_analysis(
    literature_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    analysis = await AnalysisService.get_analysis_by_literature(db, current_user.id, literature_id)
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="暂无分析结果，请先点击 AI 解析")
    return AnalysisResponse(
        id=analysis.id,
        user_id=analysis.user_id,
        literature_id=analysis.literature_id,
        summary=analysis.summary,
        innovations=analysis.innovations,
        methods=analysis.methods,
        created_at=analysis.created_at,
        updated_at=analysis.updated_at,
    )


async def _run_analyze(task_id: str, literature_id: str, user_id: str):
    from app.db.database import async_session_factory

    try:
        async with async_session_factory() as db:
            literature = await LiteratureService.get_literature_by_id(db, literature_id, user_id)
            if not literature or not literature.raw_text:
                await task_store.update_task(task_id, status=TaskStatus.FAILED, error="文献不存在或无文本内容")
                return

            ai_client = await get_user_ai_client(db, user_id)
            model = await get_user_default_model(db, user_id)
            analyzer = OpenAIAnalyzer(client=ai_client, model=model)

            result = await analyzer.analyze(literature.raw_text)

            await AnalysisService.create_or_update_analysis(
                db,
                user_id=user_id,
                literature_id=literature_id,
                summary=result.get("summary", {}),
                innovations=result.get("innovations", []),
                methods=result.get("methods", ""),
            )

            await task_store.update_task(
                task_id,
                status=TaskStatus.COMPLETED,
                progress=1,
                total=1,
                result={"literature_id": literature_id},
            )
            logger.info(f"Analyze task completed: {task_id}")

    except Exception as e:
        logger.error(f"Analyze task failed: {task_id}, error: {e}", exc_info=True)
        await task_store.update_task(task_id, status=TaskStatus.FAILED, error=str(e))


@router.post("/{literature_id}/presentation-outline")
async def generate_outline(
    literature_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    from app.services.presentation_service import PresentationService
    from app.schemas.presentation import PresentationCreate, SlideData

    literature = await LiteratureService.get_literature_by_id(db, literature_id, current_user.id)
    if not literature:
        raise HTTPException(status_code=404, detail="文献不存在")

    if not literature.raw_text:
        raise HTTPException(status_code=400, detail="该文献暂无文本内容，无法生成大纲")

    ai_client = await get_user_ai_client(db, current_user.id)
    model = await get_user_default_model(db, current_user.id)
    generator = OutlineGenerator(client=ai_client, model=model)

    outline = await generator.generate(
        text=literature.raw_text,
        title=literature.title or "",
        authors=literature.authors or "",
        year=str(literature.year) if literature.year else "",
        journal=literature.journal or "",
    )

    slides_data = [SlideData(**s) for s in outline.get("slides", [])]
    await PresentationService.create_presentation(
        db,
        str(current_user.id),
        PresentationCreate(
            literature_id=literature_id,
            literature_title=literature.title,
            slides=slides_data,
        ),
    )

    return {"code": 200, "msg": "success", "data": outline}


@router.get("/{literature_id}/presentation-outline/pptx")
async def download_outline_pptx(
    literature_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    from app.services.pptx_service import generate_pptx

    literature = await LiteratureService.get_literature_by_id(db, literature_id, current_user.id)
    if not literature:
        raise HTTPException(status_code=404, detail="文献不存在")

    if not literature.raw_text:
        raise HTTPException(status_code=400, detail="该文献暂无文本内容，无法生成PPT")

    ai_client = await get_user_ai_client(db, current_user.id)
    model = await get_user_default_model(db, current_user.id)
    generator = OutlineGenerator(client=ai_client, model=model)

    outline = await generator.generate(
        text=literature.raw_text,
        title=literature.title or "",
        authors=literature.authors or "",
        year=str(literature.year) if literature.year else "",
        journal=literature.journal or "",
    )

    pptx_bytes = generate_pptx(outline, paper_title=literature.title or "")

    filename = f"{literature.title or 'presentation'}_outline.pptx"
    safe_filename = "".join(c for c in filename if c.isalnum() or c in "._- ").strip()

    return StreamingResponse(
        iter([pptx_bytes]),
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={"Content-Disposition": f'attachment; filename="{safe_filename}"'},
    )
