import logging
import time

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.core.deps import get_current_user
from app.core.ai_client import get_cached_user_ai_client_and_model, invalidate_user_ai_cache
from app.core.ai_providers.translator import OpenAITranslator, beautify_translation_error

logger = logging.getLogger(__name__)
router = APIRouter(tags=["translate"])


class TranslateRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=10000)
    source_lang: str = Field(default="en")
    target_lang: str = Field(default="zh")
    split_paragraphs: bool = Field(default=True)


class TranslateResponse(BaseModel):
    source_text: str
    translated_text: str
    source_lang: str
    target_lang: str


@router.post("/text", response_model=TranslateResponse)
async def translate_text(
    req: TranslateRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    t_req_start = time.perf_counter()
    try:
        t_client_start = time.perf_counter()
        ai_client, model = await get_cached_user_ai_client_and_model(db, str(current_user.id))
        t_client_ms = (time.perf_counter() - t_client_start) * 1000

        translator = OpenAITranslator(client=ai_client, model=model)

        if req.split_paragraphs:
            translated, timing = await translator.translate_paragraphs(
                text=req.text,
                source_lang=req.source_lang,
                target_lang=req.target_lang,
            )
        else:
            translated = await translator.translate(
                text=req.text,
                source_lang=req.source_lang,
                target_lang=req.target_lang,
            )

        t_total_ms = (time.perf_counter() - t_req_start) * 1000
        logger.info(
            "User %s translate_text done: total=%.0fms client_init=%.0fms | %s",
            current_user.id, t_total_ms, t_client_ms,
            timing.summary() if req.split_paragraphs else ""
        )

        return TranslateResponse(
            source_text=req.text,
            translated_text=translated,
            source_lang=req.source_lang,
            target_lang=req.target_lang,
        )
    except HTTPException:
        raise
    except Exception as e:
        t_total_ms = (time.perf_counter() - t_req_start) * 1000
        logger.error(
            "Translation failed for user %s after %.0fms: %s",
            current_user.id, t_total_ms, e
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=beautify_translation_error(str(e)),
        )


@router.post("/text/stream")
async def translate_text_stream(
    req: TranslateRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    t_req_start = time.perf_counter()

    async def event_stream():
        t_stream_start = time.perf_counter()
        first_token_yielded = False
        first_token_ms = 0.0
        chunk_count = 0

        try:
            yield "data: [START]\n\n"

            t_client_start = time.perf_counter()
            try:
                ai_client, model = await get_cached_user_ai_client_and_model(db, str(current_user.id))
            except Exception as e:
                logger.error("Failed to get AI client for user %s: %s", current_user.id, e)
                yield f"data: [ERROR] {beautify_translation_error(str(e))}\n\n"
                return
            t_client_ms = (time.perf_counter() - t_client_start) * 1000

            translator = OpenAITranslator(client=ai_client, model=model)

            if req.split_paragraphs:
                async for chunk in translator.translate_stream_paragraphs(
                    text=req.text,
                    source_lang=req.source_lang,
                    target_lang=req.target_lang,
                ):
                    if not first_token_yielded:
                        first_token_ms = (time.perf_counter() - t_req_start) * 1000
                        first_token_yielded = True
                    chunk_count += 1
                    yield f"data: {chunk}\n\n"
            else:
                async for chunk in translator.translate_stream(
                    text=req.text,
                    source_lang=req.source_lang,
                    target_lang=req.target_lang,
                ):
                    if not first_token_yielded:
                        first_token_ms = (time.perf_counter() - t_req_start) * 1000
                        first_token_yielded = True
                    chunk_count += 1
                    yield f"data: {chunk}\n\n"

            t_stream_ms = (time.perf_counter() - t_stream_start) * 1000
            t_total_ms = (time.perf_counter() - t_req_start) * 1000

            timing_info = (
                f"total={t_total_ms:.0f}ms|client_init={t_client_ms:.0f}ms"
                f"|stream={t_stream_ms:.0f}ms|first_token={first_token_ms:.0f}ms"
                f"|chunks={chunk_count}|input={len(req.text)}chars"
            )
            logger.info("User %s stream_complete: %s", current_user.id, timing_info)
            yield f"data: [DONE]\n\n"
            yield f"data: [TIMING] {timing_info}\n\n"
        except Exception as e:
            t_total_ms = (time.perf_counter() - t_req_start) * 1000
            logger.error(
                "Stream translation failed for user %s after %.0fms: %s",
                current_user.id, t_total_ms, e
            )
            yield f"data: [ERROR] {beautify_translation_error(str(e))}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/cache/invalidate")
async def invalidate_translation_cache(
    current_user=Depends(get_current_user),
):
    invalidate_user_ai_cache(str(current_user.id))
    return {"code": 200, "msg": "AI client cache cleared", "data": None}