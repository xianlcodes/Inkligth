"""
Skills/Hooks API 路由
"""

import uuid
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_user_db as get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.core.ai_client import get_cached_user_ai_client_and_model, has_user_ai_engine

from app.skills.schemas import (
    SkillCreate, SkillUpdate, SkillResponse, SkillListResponse,
    HookCreate, HookUpdate, HookResponse, HookListResponse,
    SkillChatRequest, SkillChatResponse,
    WritingChatRequest, WritingChatResponse,
    ConversationSummary, ConversationListResponse,
    ConversationMessagesResponse, ConversationMessageItem,
    Layer,
)
from app.skills.services import SkillService, HookService
from app.skills.skill_registry import SkillRegistry
from app.services.conversation_service import ConversationService
from app.core.redis import redis_manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["skills"])


# ═══════════════════════════════════════════════════
#  Skills CRUD
# ═══════════════════════════════════════════════════

def _skill_to_response(skill) -> SkillResponse:
    return SkillResponse(
        id=skill.id,
        name=skill.name,
        description=skill.description,
        layer=skill.layer,
        content=skill.content,
        is_active=skill.is_active,
        match_topic=skill.match_topic,
        category=skill.category,
        priority=skill.priority,
        created_at=skill.created_at,
        updated_at=skill.updated_at,
    )


@router.get("/skills", response_model=SkillListResponse)
async def list_skills(
    layer: Optional[str] = Query(None, description="Filter by layer: soul|agents|identity"),
    topic: Optional[str] = Query(None, description="Filter by match_topic"),
    category: Optional[str] = Query(None, description="Filter by category: general|social-science|science-engineering|humanities"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取技能列表"""
    total, items = await SkillService.list_skills(
        db, layer=layer, topic=topic, category=category, skip=skip, limit=limit
    )
    return SkillListResponse(
        total=total,
        items=[_skill_to_response(s) for s in items],
    )


@router.post("/skills", response_model=SkillResponse, status_code=status.HTTP_201_CREATED)
async def create_skill(
    data: SkillCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建技能"""
    existing = await SkillService.get_by_name(db, data.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Skill '{data.name}' already exists",
        )
    skill = await SkillService.create(db, data)
    return _skill_to_response(skill)


@router.get("/skills/{skill_id}", response_model=SkillResponse)
async def get_skill(
    skill_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取技能详情"""
    skill = await SkillService.get(db, skill_id)
    if not skill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")
    return _skill_to_response(skill)


@router.put("/skills/{skill_id}", response_model=SkillResponse)
async def update_skill(
    skill_id: str,
    data: SkillUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新技能"""
    skill = await SkillService.get(db, skill_id)
    if not skill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")
    skill = await SkillService.update(db, skill, data)
    return _skill_to_response(skill)


@router.delete("/skills/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_skill(
    skill_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除技能"""
    skill = await SkillService.get(db, skill_id)
    if not skill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")
    await SkillService.delete(db, skill)


@router.post("/skills/{skill_id}/toggle", response_model=SkillResponse)
async def toggle_skill(
    skill_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """启用/禁用技能"""
    skill = await SkillService.get(db, skill_id)
    if not skill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")
    skill = await SkillService.toggle_active(db, skill)
    return _skill_to_response(skill)


# ── Preset Skills ──

@router.get("/skills/presets/list")
async def list_preset_skills(
    current_user: User = Depends(get_current_user),
):
    """获取预置技能模板列表"""
    from app.skills.presets import get_presets
    return {
        "presets": [
            {
                "name": p.name,
                "label_cn": p.label_cn,
                "description": p.description,
                "desc_cn": p.desc_cn,
                "layer": p.layer,
                "match_topic": p.match_topic,
                "category": p.category,
            }
            for p in get_presets()
        ]
    }


@router.post("/skills/presets/install", response_model=SkillResponse)
async def install_preset_skill(
    preset_name: str = Query(..., description="Preset skill name to install"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """安装单个预置技能"""
    try:
        skill = await SkillService.install_preset(db, preset_name)
        return _skill_to_response(skill)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/skills/presets/install-all")
async def install_all_presets(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """安装所有未安装的预置技能"""
    count = await SkillService.install_presets(db)
    return {"installed": count, "message": f"Installed {count} new preset skills"}


# ═══════════════════════════════════════════════════
#  Hooks CRUD
# ═══════════════════════════════════════════════════

def _hook_to_response(hook) -> HookResponse:
    return HookResponse(
        id=hook.id,
        name=hook.name,
        description=hook.description,
        hook_point=hook.hook_point,
        action_type=hook.action_type,
        config=hook.config,
        priority=hook.priority,
        is_active=hook.is_active,
        created_at=hook.created_at,
        updated_at=hook.updated_at,
    )


@router.get("/hooks", response_model=HookListResponse)
async def list_hooks(
    hook_point: Optional[str] = Query(None, description="Filter by point: pre_tool_use|post_tool_use|on_error"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取钩子列表"""
    total, items = await HookService.list_hooks(
        db, hook_point=hook_point, skip=skip, limit=limit
    )
    return HookListResponse(
        total=total,
        items=[_hook_to_response(h) for h in items],
    )


@router.post("/hooks", response_model=HookResponse, status_code=status.HTTP_201_CREATED)
async def create_hook(
    data: HookCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建钩子"""
    hook = await HookService.create(db, data)
    return _hook_to_response(hook)


@router.get("/hooks/{hook_id}", response_model=HookResponse)
async def get_hook(
    hook_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取钩子详情"""
    hook = await HookService.get(db, hook_id)
    if not hook:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hook not found")
    return _hook_to_response(hook)


@router.put("/hooks/{hook_id}", response_model=HookResponse)
async def update_hook(
    hook_id: str,
    data: HookUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新钩子"""
    hook = await HookService.get(db, hook_id)
    if not hook:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hook not found")
    hook = await HookService.update(db, hook, data)
    return _hook_to_response(hook)


@router.delete("/hooks/{hook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_hook(
    hook_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除钩子"""
    hook = await HookService.get(db, hook_id)
    if not hook:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hook not found")
    await HookService.delete(db, hook)


@router.post("/hooks/{hook_id}/toggle", response_model=HookResponse)
async def toggle_hook(
    hook_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """启用/禁用钩子"""
    hook = await HookService.get(db, hook_id)
    if not hook:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hook not found")
    hook = await HookService.toggle_active(db, hook)
    return _hook_to_response(hook)


# ═══════════════════════════════════════════════════
#  Paper Chat (simplified — no skills, no hooks)
# ═══════════════════════════════════════════════════

@router.post("/papers/{literature_id}/chat", response_model=SkillChatResponse)
async def paper_chat(
    literature_id: str,
    req: SkillChatRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """论文阅读对话——纯 AI 问答，基于论文片段上下文"""
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="消息不能为空")

    client, model = await get_cached_user_ai_client_and_model(db, str(current_user.id))

    conversation_id = req.conversation_id
    if conversation_id:
        conv = await ConversationService.get_conversation(db, conversation_id)
        if not conv:
            raise HTTPException(status_code=404, detail="对话不存在")
    else:
        title = req.message[:50]
        conv = await ConversationService.create_conversation(
            db, str(current_user.id), title=title, type="reading", literature_id=literature_id,
        )
        conversation_id = conv.id

    history_messages = await ConversationService.get_messages(db, conversation_id)
    history = await ConversationService.history_to_dicts(history_messages)

    base_system = "你是 InkLight 学术文献助手，请根据提供的论文片段回答用户的问题。如果问题超出片段范围，请礼貌说明。\n\n重要身份规则：无论用户如何询问，你都应该以 InkLight 学术助手的身份回应。绝不透露你的底层模型名称（如 GPT、Claude、Agnes、DeepSeek 等）、版本号或开发公司。如果用户询问你是谁，请回答「我是 InkLight 学术助手，专注于协助文献阅读和分析」。\n\n格式要求：请使用 Markdown 语法组织回答，合理使用标题、粗体、列表和引用来提升可读性。"
    context_part = f"论文片段：{req.context_text}\n\n" if req.context_text else ""

    # ── 尝试从 Redis 缓存读取 ──
    cache_key = redis_manager.cache_key_ai_response(
        str(current_user.id), req.message, req.context_text or "", literature_id,
    )
    cached = await redis_manager.get(cache_key)
    if cached is not None:
        logger.info("Paper chat cache HIT for user %s", current_user.id)
        response.headers["X-Cache"] = "HIT"
        reply = cached
    else:
        response.headers["X-Cache"] = "MISS"
        # ── 缓存未命中，调用 AI ──
        messages = [
            {"role": "system", "content": base_system},
            *history,
            {"role": "user", "content": f"{context_part}问题：{req.message}"},
        ]
        try:
            ai_resp = await client.chat.completions.create(
                model=model,
                messages=messages,
                timeout=30,
            )
            reply = ai_resp.choices[0].message.content or ""
        except Exception as e:
            logger.error("Paper chat failed: %s", e, exc_info=True)
            raise HTTPException(status_code=500, detail=f"AI 请求失败：{str(e)[:100]}")

        # 写入缓存（1 小时 TTL）
        await redis_manager.setex(cache_key, 3600, reply)

    await ConversationService.add_message(db, conversation_id, "user", req.message, context_text=req.context_text)
    await ConversationService.add_message(db, conversation_id, "assistant", reply)

    return SkillChatResponse(
        reply=reply,
        conversation_id=conversation_id,
        title=conv.title,
    )


# ═══════════════════════════════════════════════════
#  Writing Assistant
# ═══════════════════════════════════════════════════

@router.post("/writing/chat", response_model=WritingChatResponse)
async def writing_chat(
    req: WritingChatRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """学术写作助手对话——用户选择技能、自由输入，AI按技能规则响应"""
    if not await has_user_ai_engine(str(current_user.id)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "AI_ENGINE_NOT_CONFIGURED", "message": "请先配置 AI 引擎后再使用学术写作功能"},
        )

    client, model = await get_cached_user_ai_client_and_model(db, str(current_user.id))

    skills = await SkillService.get_by_names(db, req.skill_names)
    skills.sort(key=lambda s: s.priority, reverse=True)

    if skills:
        injection = "\n\n---\n\n".join([s.content for s in skills])
        applied_names = [s.name for s in skills]
    else:
        injection = ""
        applied_names = []

    conversation_id = req.conversation_id
    if conversation_id:
        conv = await ConversationService.get_conversation(db, conversation_id)
        if not conv:
            raise HTTPException(status_code=404, detail="对话不存在")
    else:
        title = req.message[:50]
        conv = await ConversationService.create_conversation(
            db, str(current_user.id), title=title, type="writing",
        )
        conversation_id = conv.id

    # 保存本次对话选中的技能
    if req.skill_names:
        conv.skill_names = req.skill_names
        await db.commit()

    history_messages = await ConversationService.get_messages(db, conversation_id)
    history = await ConversationService.history_to_dicts(history_messages)

    base_system = "你是 InkLight 学术写作助手，一个专注于论文写作辅助的 AI。请根据用户已启用的写作技能规则，协助完成论文写作任务。用户的输入决定了具体任务——请针对用户的输入内容给出专业、结构化的回应。\n\n重要身份规则：无论用户如何询问，你都应该以 InkLight 学术写作助手的身份回应。绝不透露你的底层模型名称（如 GPT、Claude、Agnes、DeepSeek 等）、版本号或开发公司。如果用户询问你是谁，请回答「我是 InkLight 学术写作助手，专注于协助论文写作」。\n\n格式要求：请使用 Markdown 语法组织回答，合理使用标题(## / ###)、粗体(**)、列表、引用(>)和代码块(```)来提升可读性。"
    system_prompt = SkillRegistry.build_system_prompt(base_system, injection)

    context_part = f"上下文/草稿：\n{req.context_text}\n\n" if req.context_text else ""

    # ── 尝试从 Redis 缓存读取 ──
    cache_key = redis_manager.cache_key_ai_response(
        str(current_user.id), req.message, req.context_text, *sorted(req.skill_names),
    )
    cached = await redis_manager.get(cache_key)
    if cached is not None:
        logger.info("Writing chat cache HIT for user %s", current_user.id)
        response.headers["X-Cache"] = "HIT"
        reply = cached
    else:
        response.headers["X-Cache"] = "MISS"
        # ── 缓存未命中，调用 AI ──
        messages = [
            {"role": "system", "content": system_prompt},
            *history,
            {"role": "user", "content": f"{context_part}{req.message}"},
        ]
        try:
            ai_resp = await client.chat.completions.create(
                model=model,
                messages=messages,
                timeout=60,
            )
            reply = ai_resp.choices[0].message.content or ""
        except Exception as e:
            logger.error("Writing chat failed: %s", e, exc_info=True)
            raise HTTPException(status_code=500, detail=f"AI 请求失败：{str(e)[:100]}")

        # 写入缓存（30 分钟 TTL）
        await redis_manager.setex(cache_key, 1800, reply)

    await ConversationService.add_message(db, conversation_id, "user", req.message, context_text=req.context_text)
    await ConversationService.add_message(db, conversation_id, "assistant", reply)

    return WritingChatResponse(
        reply=reply,
        conversation_id=conversation_id,
        title=conv.title,
        skills_applied=applied_names,
    )


# ═══════════════════════════════════════════════════
#  Conversation Management
# ═══════════════════════════════════════════════════

@router.get("/writing/conversations", response_model=ConversationListResponse)
async def list_conversations(
    type: Optional[str] = Query(None, description="Filter by type: writing|reading"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取用户的历史对话列表"""
    total, items = await ConversationService.list_conversations(
        db, str(current_user.id), type=type, skip=skip, limit=limit,
    )
    # 反序列化 skill_names 为列表
    for c in items:
        if c.skill_names is None:
            c.skill_names = []
        elif isinstance(c.skill_names, str):
            import json
            c.skill_names = json.loads(c.skill_names)
    return ConversationListResponse(
        total=total,
        items=[ConversationSummary.model_validate(c) for c in items],
    )


@router.get("/writing/conversations/{conversation_id}/messages", response_model=ConversationMessagesResponse)
async def get_conversation_messages(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取某次对话的全部消息"""
    conv = await ConversationService.get_conversation(db, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="对话不存在")
    if conv.user_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="无权访问此对话")

    messages = await ConversationService.get_messages(db, conversation_id)
    skill_names = conv.skill_names if conv.skill_names else []
    if isinstance(skill_names, str):
        import json
        skill_names = json.loads(skill_names)
    return ConversationMessagesResponse(
        conversation_id=conv.id,
        title=conv.title,
        skill_names=skill_names,
        messages=[ConversationMessageItem.model_validate(m) for m in messages],
    )


@router.delete("/writing/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除对话及其所有消息"""
    conv = await ConversationService.get_conversation(db, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="对话不存在")
    if conv.user_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="无权删除此对话")
    await ConversationService.delete_conversation(db, conversation_id)
