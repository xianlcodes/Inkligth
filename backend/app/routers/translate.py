import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.core.deps import get_current_user
from app.core.ai_client import get_user_ai_client, get_user_default_model
from app.core.ai_providers.translator import OpenAITranslator

logger = logging.getLogger(__name__)
router = APIRouter(tags=["translate"])


class TranslateRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=10000)
    source_lang: str = Field(default="en")
    target_lang: str = Field(default="zh")


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
    logger.info(f"Translate request received, user: {current_user.id}, text length: {len(req.text)}")
    try:
        logger.info("Getting AI client...")
        ai_client = await get_user_ai_client(db, current_user.id)
        logger.info("Getting default model...")
        model = await get_user_default_model(db, current_user.id)
        logger.info(f"Translating with model: {model}, user: {current_user.id}")
        translator = OpenAITranslator(client=ai_client, model=model)
        logger.info("Calling translator.translate()...")
        translated = await translator.translate(
            text=req.text,
            source_lang=req.source_lang,
            target_lang=req.target_lang,
        )
        logger.info(f"Translation successful, result length: {len(translated)}")
        return TranslateResponse(
            source_text=req.text,
            translated_text=translated,
            source_lang=req.source_lang,
            target_lang=req.target_lang,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Translation failed: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"翻译失败: {str(e)}")
