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

from app.db.database import get_tencent_db as get_db, get_user_db, TencentSessionLocal, AlibabaSessionLocal
from app.core.deps import get_current_user
from app.core.ai_client import get_user_ai_client, get_user_default_model
from app.core.ai_providers.translator import OpenAITranslator, beautify_translation_error
from app.core.ai_providers.analyzer import OpenAIAnalyzer
from app.core.ai_providers.outline_generator import OutlineGenerator
from app.services.formula_protection_service import (
    FormulaProtectionService,
    detect_formula_features,
    has_pdf_math_indicators,
)
from app.services.layout_text_filter import extract_filtered_text
from app.core.config import settings
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


def _resolve_file_path(file_path: str) -> str:
    if not file_path:
        return ""

    if os.path.isabs(file_path) and os.path.isfile(file_path):
        return file_path

    upload_dir = os.path.abspath(settings.UPLOAD_DIR)

    if not os.path.isabs(file_path):
        candidate = os.path.join(upload_dir, os.path.basename(file_path))
        if os.path.isfile(candidate):
            return candidate

        candidate = os.path.join(upload_dir, file_path)
        if os.path.isfile(candidate):
            return candidate

    legacy_path = os.path.join("/app", file_path)
    if os.path.isfile(legacy_path):
        return legacy_path

    return ""


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
        storage = await StorageService.get_storage(db, current_user.id)
        remaining = storage.total_space - storage.used_space
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

    file_path = LiteratureService.save_upload_file(file)
    raw_filename = file.filename.rsplit(".", 1)[0]

    literature = await LiteratureService.create_literature(
        db=db,
        user_id=current_user.id,
        file=file,
        literature_in=LiteratureCreate(
            title=raw_filename,
            file_path=file_path,
            file_size=file_size,
            raw_text=None,
            folder_id=folder_id,
        ),
    )

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


class ImportByDoiRequest(BaseModel):
    doi: str

class ImportByArxivRequest(BaseModel):
    arxiv_id: str


@router.post("/import-by-doi")
async def import_by_doi(
    body: ImportByDoiRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """通过 DOI 导入文献元数据（无 PDF，需用户后续上传）"""
    try:
        literature = await LiteratureService.import_by_doi(db, str(current_user.id), body.doi.strip())
        return literature
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/import-by-arxiv")
async def import_by_arxiv(
    body: ImportByArxivRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """通过 arXiv ID 导入文献（自动下载 PDF + 元数据）"""
    try:
        literature = await LiteratureService.import_by_arxiv(
            db, str(current_user.id), body.arxiv_id.strip(),
            upload_dir=settings.UPLOAD_DIR,
        )
        return literature
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{literature_id}/citation")
async def get_citation(
    literature_id: str,
    format: str = Query("bibtex", pattern="^(bibtex)$"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """获取文献引用（支持 BibTeX）"""
    from app.services.literature_service import LiteratureService
    lit = await LiteratureService.get_literature_by_id(db, literature_id, str(current_user.id))
    if not lit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文献不存在")
    bibtex = LiteratureService.to_bibtex(lit)
    return {"code": 200, "data": {"format": format, "citation": bibtex}}


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
    user_db: AsyncSession = Depends(get_user_db),
):
    literature = await LiteratureService.get_literature_by_id(db, literature_id, current_user.id)
    if not literature:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文献不存在")
    file_size = literature.file_size or 0
    # AIAnalysis 在阿里云用户数据库上，需要单独删除
    from app.models.ai_analysis import AIAnalysis
    from sqlalchemy import delete
    await user_db.execute(delete(AIAnalysis).where(AIAnalysis.literature_id == literature_id))
    await user_db.commit()
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

    file_path = literature.file_path
    absolute_path = _resolve_file_path(file_path)

    if not absolute_path or not os.path.exists(absolute_path):
        if not literature.file_path:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="该文献暂无 PDF 文件（通过 DOI 导入仅有元数据）")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件不存在")

    return FileResponse(
        path=absolute_path,
        media_type="application/pdf",
        filename=os.path.basename(file_path),
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

        task = await task_store.create_task("full_translate", user_id=str(current_user.id))
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

        translated = ""
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
        if not translated:
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

            # Use layout-aware text extraction to filter out figures, tables, formulas
            # (same approach as PDFMathTranslate — DocLayout-YOLO model)
            try:
                file_path = _resolve_file_path(literature.file_path)
                if os.path.exists(file_path):
                    filtered = await extract_filtered_text(file_path)
                    if filtered.strip():
                        raw_text = filtered
                        logger.info(
                            "Layout-aware filtering applied for literature %s: "
                            "%d chars (original %d chars)",
                            literature_id, len(filtered), len(literature.raw_text),
                        )
                    else:
                        logger.warning(
                            "Layout-aware filtering produced empty text for %s, "
                            "falling back to raw extracted text",
                            literature_id,
                        )
                else:
                    logger.warning(
                        "PDF file %s not found for layout filtering, "
                        "using raw extracted text",
                        file_path,
                    )
            except Exception as e:
                logger.warning(
                    "Layout-aware filtering failed for %s: %s, "
                    "falling back to raw extracted text",
                    literature_id, e,
                )
            paragraphs = _split_paragraphs(raw_text)
            total = len(paragraphs)

            await task_store.update_task(task_id, total=total, progress=0)

            await TranslationService.cleanup_expired_translations(db)

            ai_client = await get_user_ai_client(db, user_id)
            model = await get_user_default_model(db, user_id)
            translator = OpenAITranslator(
                client=ai_client,
                model=model,
                cancel_check=lambda: task_id in _cancellation_flags,
            )

            from app.core.ai_providers.translator import _get_max_concurrent_for_model
            sem = asyncio.Semaphore(_get_max_concurrent_for_model(model))
            progress_lock = asyncio.Lock()
            progress_counter = {"done": 0}

            has_formulas = has_pdf_math_indicators(raw_text)
            if has_formulas:
                logger.info("Formulas detected in literature %s, using protected translation", literature_id)
                formula_service = FormulaProtectionService()
                protected_paragraphs = formula_service.protect_paragraphs(paragraphs)
                para_map = list(zip(paragraphs, protected_paragraphs))

                async def _translate_protected(
                    translator: OpenAITranslator,
                    index: int,
                    original: str,
                    protected: str,
                ) -> dict:
                    async with sem:
                        if _is_cancelled(task_id):
                            return {"paragraph_index": index, "original": original, "translated": "[已取消]"}
                        if not original.strip():
                            return {"paragraph_index": index, "original": original, "translated": ""}

                        raw = ""
                        last_error = ""
                        for attempt in range(MAX_RETRIES + 1):
                            try:
                                raw = await translator._translate_with_formula_prompt(
                                    protected, "en", "zh", PER_PARAGRAPH_TIMEOUT
                                )
                                break
                            except Exception as e:
                                last_error = str(e)
                                err_lower = last_error.lower()
                                is_retryable = any(k in err_lower for k in ("429", "rate limit", "timeout", "connection", "reset"))
                                if is_retryable and attempt < MAX_RETRIES:
                                    delay = RETRY_BACKOFF_BASE ** attempt
                                    logger.warning(
                                        "Protected paragraph %s attempt %s/%s failed: %s, retrying in %.1fs",
                                        index, attempt + 1, MAX_RETRIES + 1, e, delay,
                                    )
                                    await asyncio.sleep(delay)
                                else:
                                    logger.error(
                                        "Protected paragraph %s translation failed after %s attempts: %s",
                                        index, attempt + 1, e,
                                    )
                                    break
                        if not raw:
                            raw = f"[翻译失败: {beautify_translation_error(last_error)}]"

                    translated = formula_service.restore_text(raw)
                    async with progress_lock:
                        progress_counter["done"] += 1
                        await task_store.update_task(task_id, progress=progress_counter["done"])

                    return {"paragraph_index": index, "original": original, "translated": translated}

                coros = [
                    _translate_protected(
                        translator=translator,
                        index=i,
                        original=orig,
                        protected=prot,
                    )
                    for i, (orig, prot) in enumerate(para_map)
                ]
            else:
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
            usage = translator.get_usage_summary()
            logger.warning(
                "FULL_TRANSLATE_TOKEN_SUMMARY | task=%s literature=%s paragraphs=%d | "
                "prompt_tokens=%d completion_tokens=%d total_tokens=%d",
                task_id, literature_id, total,
                usage["total_prompt_tokens"], usage["total_completion_tokens"], usage["total_tokens"],
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
    Background task: extract text, save text immediately, then
    run multi-tier metadata extraction (slow), and trigger chunk indexing.
    """
    from app.db.database import async_session_factory
    from app.schemas.literature import LiteratureUpdate

    logger.warning(f"_process_uploaded_literature started for {literature_id}")
    try:
        # 1. Extract text from PDF
        raw_text = LiteratureService.extract_text_from_pdf(file_path)
        if not raw_text:
            logger.error(f"Failed to extract text from PDF: {file_path}")
            return

        # ---------------------------------------------------------------
        # 2. Save raw_text FIRST, so the paper is immediately usable
        #    (metadata extraction below can be slow due to Crossref API)
        # ---------------------------------------------------------------
        async with async_session_factory() as db:
            existing = await LiteratureService.get_literature_by_id(db, literature_id, user_id)
            if not existing:
                logger.error(f"Literature {literature_id} not found in DB during async processing")
                return
            await LiteratureService.update_literature(
                db, existing,
                LiteratureUpdate(
                    raw_text=raw_text,
                ),
            )
            logger.warning(f"Literature {literature_id} raw_text saved ({len(raw_text)} chars)")

        # 3. Get AI client if available
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

        # 4. Multi-tier metadata extraction (may be slow — Crossref API calls)
        metadata = await LiteratureService.extract_metadata(raw_text, ai_client=ai_client, model=model)

        # 5. Update literature metadata (title, authors, etc.)
        async with async_session_factory() as db:
            existing = await LiteratureService.get_literature_by_id(db, literature_id, user_id)
            if not existing:
                logger.error(f"Literature {literature_id} not found in DB during metadata update")
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
                ),
            )
            logger.warning(f"Literature {literature_id} metadata updated: title='{metadata.get('title')}'")

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
    user_db: AsyncSession = Depends(get_user_db),
):
    literature = await LiteratureService.get_literature_by_id(db, literature_id, current_user.id)
    if not literature:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文献不存在")

    if not literature.raw_text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该文献暂无文本内容，无法分析")

    existing = await AnalysisService.get_analysis_by_literature(user_db, current_user.id, literature_id)
    if existing:
        return AnalyzeResponse(
            task_id="cached",
            message="已有缓存分析结果",
        )

    task = await task_store.create_task("analyze", user_id=str(current_user.id))
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
    db: AsyncSession = Depends(get_user_db),
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
    from app.db.database import TencentSessionLocal, AlibabaSessionLocal

    try:
        async with TencentSessionLocal() as tencent_db, AlibabaSessionLocal() as user_db:
            literature = await LiteratureService.get_literature_by_id(tencent_db, literature_id, user_id)
            if not literature or not literature.raw_text:
                await task_store.update_task(task_id, status=TaskStatus.FAILED, error="文献不存在或无文本内容")
                return

            ai_client = await get_user_ai_client(user_db, user_id)
            model = await get_user_default_model(user_db, user_id)
            analyzer = OpenAIAnalyzer(client=ai_client, model=model)

            result = await analyzer.analyze(literature.raw_text)

            await AnalysisService.create_or_update_analysis(
                user_db,
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


@router.post("/{literature_id}/generate-ppt")
async def generate_ppt(
    literature_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """一键生成汇报 PPT：后台做完 视觉提取 → LLM 大纲 → 构建 PPTX，返回 task_id。"""
    literature = await LiteratureService.get_literature_by_id(db, literature_id, current_user.id)
    if not literature:
        raise HTTPException(status_code=404, detail="文献不存在")
    if not literature.raw_text:
        raise HTTPException(status_code=400, detail="该文献暂无文本内容")

    task = await task_store.create_task("ppt_generation", user_id=str(current_user.id))
    await task_store.update_task(task.task_id, status=TaskStatus.RUNNING, progress=0, total=100)

    background_tasks.add_task(
        _run_ppt_generation,
        task_id=task.task_id,
        literature_id=literature_id,
        user_id=str(current_user.id),
    )

    logger.info("PPT generation task started: %s, literature: %s", task.task_id, literature_id)
    return {
        "code": 200,
        "msg": "success",
        "data": {"task_id": task.task_id},
    }


@router.get("/{literature_id}/generate-ppt/{task_id}")
async def get_ppt_task(
    literature_id: str,
    task_id: str,
    current_user=Depends(get_current_user),
):
    """获取 PPT 生成任务状态，completed 时返回 slides 数据。"""
    task_info = await task_store.get_task(task_id)
    if not task_info:
        raise HTTPException(status_code=404, detail="任务不存在")

    resp = task_info.to_dict()
    # 完成后附带 slides 数据，前端可直接预览
    if task_info.status == TaskStatus.COMPLETED and task_info.result:
        resp["slides"] = task_info.result.get("slides", [])
    return resp


@router.get("/{literature_id}/generate-ppt/{task_id}/download")
async def download_ppt(
    literature_id: str,
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """下载已生成的 PPTX 文件。"""
    literature = await LiteratureService.get_literature_by_id(db, literature_id, current_user.id)
    if not literature:
        raise HTTPException(status_code=404, detail="文献不存在")

    task_info = await task_store.get_task(task_id)
    if not task_info:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task_info.status != TaskStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="任务尚未完成")

    result = task_info.result or {}
    output_path = result.get("output_path")
    output_filename = result.get("output_filename")
    if not output_path or not os.path.exists(output_path):
        raise HTTPException(status_code=404, detail="PPT 文件不存在")

    return FileResponse(
        path=output_path,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename=output_filename,
        headers={"Content-Disposition": f'attachment; filename="{output_filename}"'},
    )


async def _run_ppt_generation(
    task_id: str,
    literature_id: str,
    user_id: str,
):
    """后台任务：视觉提取 → LLM 大纲 → auto-match → 存 DB → 构建 PPTX → 存磁盘"""
    from app.db.database import async_session_factory
    from app.services.presentation_service import PresentationService
    from app.schemas.presentation import PresentationCreate, SlideData
    from app.services.visual_extractor import VisualExtractor
    from app.core.ai_providers.outline_generator import auto_match_visual_refs
    from app.services.pptx_builder import PptxBuilder
    from app.services.ppt_theme import get_theme

    t_start = asyncio.get_event_loop().time()
    slides_data = []
    output_path = None

    async def set_progress(pct: int, msg: str = ""):
        await task_store.update_task(task_id, progress=pct, error=msg)

    try:
        await set_progress(5, "准备中...")

        async with async_session_factory() as db:
            literature = await LiteratureService.get_literature_by_id(db, literature_id, user_id)
            if not literature or not literature.raw_text:
                await task_store.update_task(task_id, status=TaskStatus.FAILED,
                                              error="文献不存在或无文本内容")
                return

            # 1. 提取视觉资产（第一次慢，后续走缓存）
            await set_progress(15, "提取图表...")
            pdf_path = _resolve_file_path(literature.file_path)
            visual_assets: dict | None = None
            if os.path.exists(pdf_path):
                try:
                    cache_dir = getattr(settings, "UPLOAD_DIR", "/tmp") + "/visual_assets"
                    extractor = VisualExtractor(cache_dir)
                    visual_assets = await extractor.extract(pdf_path)
                except Exception as e:
                    logger.warning("Visual extraction failed: %s", e)

            # 2. LLM 生成大纲
            await set_progress(40, "AI 生成大纲...")
            ai_client = await get_user_ai_client(db, user_id)
            model = await get_user_default_model(db, user_id)
            generator = OutlineGenerator(client=ai_client, model=model)
            visual_summary = (visual_assets or {}).get("summary", "")
            outline = await generator.generate(
                text=literature.raw_text,
                title=literature.title or "",
                authors=literature.authors or "",
                year=str(literature.year) if literature.year else "",
                journal=literature.journal or "",
                visual_summary=visual_summary,
            )
            slides_data = outline.get("slides", [])

            # 3. Auto-match 图/表引用
            await set_progress(75, "匹配图表...")
            if visual_assets:
                slides_data = auto_match_visual_refs(slides_data, visual_assets)

            # 4. 保存大纲到数据库（历史记录）
            slides_models = [SlideData(**s) for s in slides_data]
            await PresentationService.create_presentation(
                db, user_id,
                PresentationCreate(
                    literature_id=literature_id,
                    literature_title=literature.title,
                    slides=slides_models,
                ),
            )

            # 5. 构建 PPTX
            await set_progress(85, "渲染 PPT...")
            theme = get_theme("cs")
            builder = PptxBuilder(theme=theme)
            pptx_bytes = builder.build(
                slides_data,
                visual_assets=visual_assets,
                paper_title=literature.title or "",
            )

            # 6. 保存到磁盘
            await set_progress(95, "保存文件...")
            output_dir = os.path.join(os.path.abspath(settings.UPLOAD_DIR), "ppt_generated")
            os.makedirs(output_dir, exist_ok=True)
            safe_name = "".join(c for c in (literature.title or "presentation") if c.isalnum() or c in "._- ").strip()
            output_filename = f"{safe_name}.pptx"
            output_path = os.path.join(output_dir, f"{task_id}_{output_filename}")
            with open(output_path, "wb") as f:
                f.write(pptx_bytes)

        # 7. 标记完成
        await task_store.update_task(
            task_id,
            status=TaskStatus.COMPLETED,
            progress=100,
            error="",
            result={
                "output_path": output_path,
                "output_filename": output_filename,
                "slides": slides_data,
            },
        )
        logger.info("PPT task %s done in %.1fs (%d slides)",
                    task_id, asyncio.get_event_loop().time() - t_start, len(slides_data))

    except Exception as e:
        logger.error("PPT task %s failed: %s", task_id, e, exc_info=True)
        await task_store.update_task(
            task_id,
            status=TaskStatus.FAILED,
            error=f"PPT 生成失败: {str(e)[:200]}",
        )


@router.post("/{literature_id}/translate-pdf")
async def start_pdf_translate(
    literature_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    source_lang: str = Query("en"),
    target_lang: str = Query("zh"),
    output_mode: str = Query("mono"),
):
    from app.schemas.pdf_render import PdfTranslateDownloadResponse

    literature = await LiteratureService.get_literature_by_id(db, literature_id, current_user.id)
    if not literature:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文献不存在")

    file_path = _resolve_file_path(literature.file_path)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文献文件不存在")

    task = await task_store.create_task("pdf_translate", user_id=str(current_user.id))
    await task_store.update_task(task.task_id, status=TaskStatus.RUNNING, progress=0, total=100)

    background_tasks.add_task(
        _run_pdf_translate,
        task_id=task.task_id,
        literature_id=literature_id,
        user_id=str(current_user.id),
        file_path=file_path,
        source_lang=source_lang,
        target_lang=target_lang,
        output_mode=output_mode,
        original_filename=literature.title or "translated",
    )

    logger.info("PDF translate task created: %s for literature %s", task.task_id, literature_id)
    return PdfTranslateDownloadResponse(
        task_id=task.task_id,
        status="running",
        message="PDF 原位翻译任务已启动",
    )


@router.get("/{literature_id}/translate-pdf/check")
async def check_pdf_translation(
    literature_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """检查文献是否存在有效的原位翻译（未过期），返回下载/预览地址"""
    from datetime import datetime as dt
    from app.utils.timezone import utc_to_bjt
    from app.models.pdf_translation import PdfTranslation
    from sqlalchemy import select

    literature = await LiteratureService.get_literature_by_id(db, literature_id, current_user.id)
    if not literature:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文献不存在")

    result = await db.execute(
        select(PdfTranslation).where(
            PdfTranslation.literature_id == literature_id,
            PdfTranslation.user_id == str(current_user.id),
            PdfTranslation.expires_at > dt.utcnow(),
        ).order_by(PdfTranslation.created_at.desc()).limit(1)
    )
    record = result.scalar_one_or_none()

    if not record:
        return {"has_translation": False, "download_url": None, "preview_url": None, "expires_at": None}

    file_exists = record.file_path and os.path.exists(record.file_path)
    if not file_exists:
        return {"has_translation": False, "download_url": None, "preview_url": None, "expires_at": None}

    download_url = f"/literatures/{literature_id}/translate-pdf/{record.task_id}/download"
    preview_url = f"/literatures/{literature_id}/translate-pdf/{record.task_id}/preview"
    return {
        "has_translation": True,
        "download_url": download_url,
        "preview_url": preview_url,
        "expires_at": utc_to_bjt(record.expires_at).isoformat() if record.expires_at else None,
        "source_lang": record.source_lang,
        "target_lang": record.target_lang,
        "output_mode": record.output_mode,
    }


@router.get("/{literature_id}/translate-pdf/{task_id}")
async def get_pdf_translate_status(
    literature_id: str,
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    from app.schemas.pdf_render import PdfTranslateTaskStatus

    literature = await LiteratureService.get_literature_by_id(db, literature_id, current_user.id)
    if not literature:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文献不存在")

    task_info = await task_store.get_task(task_id)
    if not task_info:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")

    download_url = None
    preview_url = None
    expires_at = None
    if task_info.status == TaskStatus.COMPLETED and task_info.result:
        download_url = f"/literatures/{literature_id}/translate-pdf/{task_id}/download"
        preview_url = f"/literatures/{literature_id}/translate-pdf/{task_id}/preview"
        try:
            from sqlalchemy import select
            from app.utils.timezone import utc_to_bjt
            from app.models.pdf_translation import PdfTranslation
            result = await db.execute(
                select(PdfTranslation).where(
                    PdfTranslation.literature_id == literature_id,
                    PdfTranslation.user_id == current_user.id,
                ).order_by(PdfTranslation.created_at.desc()).limit(1)
            )
            record = result.scalar_one_or_none()
            if record and record.expires_at:
                expires_at = utc_to_bjt(record.expires_at).isoformat()
        except Exception:
            pass

    return PdfTranslateTaskStatus(
        task_id=task_id,
        status=task_info.status.value if hasattr(task_info.status, "value") else str(task_info.status),
        progress=task_info.progress or 0,
        message=task_info.error or "",
        download_url=download_url,
        preview_url=preview_url,
        expires_at=expires_at,
    )


@router.post("/{literature_id}/translate-pdf/{task_id}/cancel")
async def cancel_pdf_translate(
    literature_id: str,
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    literature = await LiteratureService.get_literature_by_id(db, literature_id, current_user.id)
    if not literature:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文献不存在")

    task_info = await task_store.get_task(task_id)
    if not task_info:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")

    cancelled = await task_store.cancel_task(task_id)
    if not cancelled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="任务无法取消（已完成或已失败）")

    logger.info("PDF translate task %s cancelled by user", task_id)
    return {"code": 200, "msg": "翻译任务已取消"}


async def _resolve_translate_file(db, task_id: str, literature_id: str, user_id: str, title: str = ""):
    """从 task_store 或 PdfTranslation 表解析翻译文件路径，返回 (path, filename) 或 None"""
    # 用论文标题构造文件名
    if title:
        safe = "".join(c for c in title if c.isalnum() or c in " _-").strip() or "translated"
        base_name = f"{safe} - 原位翻译.pdf"
    else:
        base_name = "translated.pdf"

    task_info = await task_store.get_task(task_id)
    if task_info and task_info.status == TaskStatus.COMPLETED:
        result = task_info.result or {}
        path = result.get("output_path")
        if path and os.path.isfile(path):
            return path, base_name

    # Fallback: 从数据库查找
    try:
        from datetime import datetime as dt
        from app.models.pdf_translation import PdfTranslation
        from sqlalchemy import select
        result = await db.execute(
            select(PdfTranslation).where(
                PdfTranslation.task_id == task_id,
                PdfTranslation.literature_id == literature_id,
                PdfTranslation.user_id == str(user_id),
                PdfTranslation.expires_at > dt.utcnow(),
            ).limit(1)
        )
        rec = result.scalar_one_or_none()
        if rec and rec.file_path and os.path.isfile(rec.file_path):
            return rec.file_path, base_name
    except Exception as e:
        logger.error("Failed to query PdfTranslation table: %s", e, exc_info=True)
    return None, None


@router.get("/{literature_id}/translate-pdf/{task_id}/download")
async def download_pdf_translate(
    literature_id: str,
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        literature = await LiteratureService.get_literature_by_id(db, literature_id, current_user.id)
        if not literature:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文献不存在")

        output_path, output_filename = await _resolve_translate_file(
            db, task_id, literature_id, str(current_user.id),
            title=literature.title or "",
        )
        if not output_path:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="翻译结果文件不存在或已过期")

        return FileResponse(
            path=output_path,
            media_type="application/pdf",
            filename=output_filename or "translated.pdf",
            headers={"Content-Disposition": f'attachment; filename="{output_filename or "translated.pdf"}"'},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Download PDF translate failed: literature=%s task=%s error=%s",
                      literature_id, task_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"下载翻译文件失败: {str(e)[:200]}")


@router.get("/{literature_id}/translate-pdf/{task_id}/preview")
async def preview_pdf_translate(
    literature_id: str,
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        literature = await LiteratureService.get_literature_by_id(db, literature_id, current_user.id)
        if not literature:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文献不存在")

        output_path, output_filename = await _resolve_translate_file(
            db, task_id, literature_id, str(current_user.id)
        )
        if not output_path:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="翻译结果文件不存在或已过期")

        safe_filename = "".join(c for c in (output_filename or "translated.pdf") if c.isalnum() or c in "._- ")
        return FileResponse(
            path=output_path,
            media_type="application/pdf",
            filename=safe_filename,
            headers={"Content-Disposition": f'inline; filename="{safe_filename}"'},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Preview PDF translate failed: literature=%s task=%s error=%s",
                      literature_id, task_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"预览翻译文件失败: {str(e)[:200]}")


async def _run_pdf_translate(
    task_id: str,
    literature_id: str,
    user_id: str,
    file_path: str,
    source_lang: str,
    target_lang: str,
    output_mode: str,
    original_filename: str,
):
    from app.db.database import async_session_factory
    from app.services.pdf_render_service import pdf_render_service

    class TaskCancelledException(Exception):
        pass

    cancel_event = await task_store.register_cancel_event(task_id)

    async def report_progress(progress: int, message: str):
        await task_store.update_task(task_id, progress=progress, error=message)

    def cancel_check() -> bool:
        return cancel_event.is_set()

    def raise_if_cancelled():
        if cancel_event.is_set():
            raise TaskCancelledException()

    try:
        await report_progress(10, "正在初始化 AI 客户端...")

        async with async_session_factory() as db:
            ai_client = await get_user_ai_client(db, user_id)
            model = await get_user_default_model(db, user_id)

        raise_if_cancelled()

        await report_progress(20, "准备翻译...")

        output_bytes = await pdf_render_service.build_translated_pdf(
            source_pdf_path=file_path,
            ai_client=ai_client,
            model=model,
            source_lang=source_lang,
            target_lang=target_lang,
            output_mode=output_mode,
            progress_callback=report_progress,
            cancel_check=cancel_check,
        )

        raise_if_cancelled()

        await report_progress(90, "正在保存翻译结果...")

        output_dir = os.path.join(os.path.abspath(settings.UPLOAD_DIR), "translated")
        os.makedirs(output_dir, exist_ok=True)

        suffix = "dual" if output_mode == "dual" else "mono"
        output_filename = f"{original_filename}_{target_lang}_{suffix}.pdf"
        output_path = os.path.join(output_dir, f"{task_id}_{output_filename}")

        with open(output_path, "wb") as f:
            f.write(output_bytes)

        await task_store.update_task(
            task_id,
            status=TaskStatus.COMPLETED,
            progress=100,
            error="PDF 原位翻译完成",
            result={"output_path": output_path, "output_filename": output_filename},
        )

        # 保存翻译记录到数据库（持久化）
        try:
            from app.models.pdf_translation import PdfTranslation
            async with async_session_factory() as save_db:
                record = PdfTranslation(
                    literature_id=literature_id,
                    user_id=user_id,
                    task_id=task_id,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    output_mode=output_mode,
                    file_path=output_path,
                    file_size=os.path.getsize(output_path) if os.path.exists(output_path) else None,
                    expires_at=PdfTranslation.compute_expiry(),
                )
                save_db.add(record)
                await save_db.commit()
        except Exception as save_err:
            logger.error("Failed to save PdfTranslation record: %s", save_err, exc_info=True)

        logger.info("PDF translate task completed: %s, output: %s", task_id, output_path)

    except TaskCancelledException:
        logger.info("PDF translate task cancelled: %s", task_id)
        await task_store.update_task(
            task_id,
            status=TaskStatus.CANCELLED,
            error="任务已被取消",
        )
    except Exception as e:
        if cancel_event.is_set():
            logger.info("PDF translate task cancelled after error: %s", task_id)
            await task_store.update_task(
                task_id,
                status=TaskStatus.CANCELLED,
                error="任务已被取消",
            )
        else:
            logger.error("PDF translate task failed: %s, error: %s", task_id, e, exc_info=True)
            await task_store.update_task(task_id, status=TaskStatus.FAILED, error=str(e))
    final