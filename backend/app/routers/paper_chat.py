import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.core.deps import get_current_user
from app.core.ai_client import get_cached_user_ai_client_and_model
from app.services.chat_service import conversation_store

logger = logging.getLogger(__name__)
router = APIRouter(tags=["paper-chat"])


class ChatRequest(BaseModel):
    message: str
    context_text: str
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str
    conversation_id: str


@router.post("/papers/{literature_id}/chat")
async def chat_with_paper(
    literature_id: str,
    req: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="消息不能为空")
    if not req.context_text.strip():
        raise HTTPException(status_code=400, detail="请先选中论文中的文本作为上下文")

    client, model = await get_cached_user_ai_client_and_model(db, str(current_user.id))

    conversation_id = req.conversation_id or str(uuid.uuid4())

    # 读取历史（最多保留最近 5 轮 = 10 条）
    history = []
    if req.conversation_id:
        history = await conversation_store.get_messages(req.conversation_id)
        history = history[-10:]

    messages = [
        {
            "role": "system",
            "content": "你是一个学术文献助手，请根据提供的论文片段回答用户的问题。如果问题超出片段范围，请礼貌说明。",
        },
        *history,
        {"role": "user", "content": f"论文片段：{req.context_text}\n\n问题：{req.message}"},
    ]

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            timeout=30,
        )
        reply = response.choices[0].message.content or ""
    except Exception as e:
        logger.error("AI chat failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"AI 请求失败：{str(e)[:100]}")

    # 保存历史（保存完整 messages，方便后续扩展）
    history.append({"role": "user", "content": req.message})
    history.append({"role": "assistant", "content": reply})
    await conversation_store.save_messages(conversation_id, history)

    return {"reply": reply, "conversation_id": conversation_id}
