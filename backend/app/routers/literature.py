import json
import logging
import os
from typing import Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status, UploadFile, File, Query
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.core.deps import get_current_user
from app.core.ai_client import get_user_ai_client, get_user_default_model
from app.core.ai_providers.translator import OpenAITranslator
from app.core.ai_providers.analyzer import OpenAIAnalyzer
from app.core.ai_providers.outline_generator import OutlineGenerator
from app.services.literature_service import LiteratureService
from app.services.analysis_service import AnalysisService
from app.services.search_service import SearchService
from app.schemas.literature import LiteratureResponse, LiteratureCreate, LiteratureUpdate, LiteratureListResponse
from app.schemas.analysis import AnalysisResponse, AnalyzeResponse
from app.utils.task_store import task_store, TaskStatus

logger = logging.getLogger(__name__)
router = APIRouter(tags=["literatures"])


@router.post("", response_model=LiteratureResponse)
async def upload_literature(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    background_tasks: BackgroundTasks = None,
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only PDF files are allowed")

    file_path = LiteratureService.save_upload_file(file)
    raw_text = LiteratureService.extract_text_from_pdf(file_path)

    ai_client = await get_user_ai_client(db, current_user.id)
    model = await get_user_default_model(db, current_user.id)

    metadata = await LiteratureService.extract_metadata(raw_text, ai_client=ai_client, model=model)

    # Deduplication by DOI if available
    if metadata.get("doi"):
        existing = await LiteratureService.get_literature_by_doi_and_user(db, metadata["doi"], current_user.id)
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="文献已存在")

    # Final validation: title must not be empty
    if not metadata.get("title"):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="无法从文献中提取标题，请手动填写")

    literature = await LiteratureService.create_literature(
        db=db,
        user_id=current_user.id,
        file=file,
        literature_in=LiteratureCreate(
            title=metadata.get("title"),
            authors=metadata.get("authors"),
            abstract=metadata.get("abstract"),
            year=metadata.get("year"),
            journal=metadata.get("journal"),
            doi=metadata.get("doi"),
            file_path=file_path,
            raw_text=raw_text,
        ),
    )

    if raw_text and background_tasks:
        paragraphs = _split_paragraphs(raw_text)
        background_tasks.add_task(_index_chunks, literature.id, paragraphs)

    return literature


@router.get("", response_model=LiteratureListResponse)
async def list_literatures(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    title: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    sort_by_year: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    total, items = await LiteratureService.get_literatures_by_user(
        db, current_user.id, skip=skip, limit=limit, title=title, status=status, sort_by_year=sort_by_year
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


async def _run_full_translate(task_id: str, literature_id: str, user_id: str):
    from app.db.database import async_session_factory

    try:
        async with async_session_factory() as db:
            literature = await LiteratureService.get_literature_by_id(db, literature_id, user_id)
            if not literature or not literature.raw_text:
                await task_store.update_task(task_id, status=TaskStatus.FAILED, error="文献不存在或无文本内容")
                return

            raw_text = literature.raw_text
            paragraphs = _split_paragraphs(raw_text)
            total = len(paragraphs)

            await task_store.update_task(task_id, total=total, progress=0)

            ai_client = await get_user_ai_client(db, user_id)
            model = await get_user_default_model(db, user_id)
            translator = OpenAITranslator(client=ai_client, model=model)

            translated_paragraphs = []
            for i, para in enumerate(paragraphs):
                if not para.strip():
                    translated_paragraphs.append({"paragraph_index": i, "original": para, "translated": ""})
                    await task_store.update_task(task_id, progress=i + 1)
                    continue

                try:
                    translated = await translator.translate(text=para, source_lang="en", target_lang="zh")
                except Exception as e:
                    logger.error(f"Paragraph {i} translation failed: {e}")
                    translated = f"[翻译失败: {str(e)}]"

                translated_paragraphs.append({
                    "paragraph_index": i,
                    "original": para,
                    "translated": translated,
                })
                await task_store.update_task(task_id, progress=i + 1)

            result_json = json.dumps(translated_paragraphs, ensure_ascii=False)
            literature.translated_text = result_json
            await db.commit()

            await task_store.update_task(
                task_id,
                status=TaskStatus.COMPLETED,
                result={"literature_id": literature_id, "paragraph_count": total},
            )
            logger.info(f"Full translate task completed: {task_id}")

    except Exception as e:
        logger.error(f"Full translate task failed: {task_id}, error: {e}", exc_info=True)
        await task_store.update_task(task_id, status=TaskStatus.FAILED, error=str(e))


def _split_paragraphs(text: str) -> list[str]:
    paragraphs = []
    for block in text.split("\n\n"):
        block = block.strip()
        if not block:
            continue
        sub_blocks = [s.strip() for s in block.split("\n") if s.strip()]
        if len(sub_blocks) <= 3:
            paragraphs.extend(sub_blocks)
        else:
            paragraphs.append(block)

    if len(paragraphs) <= 1:
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        paragraphs = []
        current = ""
        for line in lines:
            if len(current) + len(line) > 2000 and current:
                paragraphs.append(current.strip())
                current = line
            else:
                current = current + "\n" + line if current else line
        if current.strip():
            paragraphs.append(current.strip())

    return paragraphs


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
