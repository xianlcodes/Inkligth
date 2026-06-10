"""
Skills/Hooks 业务逻辑层
"""

import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.skills.models import Skill, Hook
from app.skills.schemas import SkillCreate, SkillUpdate, HookCreate, HookUpdate
from app.skills.presets import get_presets, get_preset

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════
#  Skill Service
# ═══════════════════════════════════════════════════

class SkillService:

    @staticmethod
    async def create(db: AsyncSession, data: SkillCreate) -> Skill:
        skill = Skill(
            name=data.name,
            description=data.description,
            layer=data.layer.value,
            content=data.content,
            is_active=data.is_active,
            match_topic=data.match_topic,
            category=data.category,
            priority=data.priority,
        )
        db.add(skill)
        await db.commit()
        await db.refresh(skill)
        logger.info("Skill created: %s (%s)", skill.name, skill.layer)
        return skill

    @staticmethod
    async def get(db: AsyncSession, skill_id: str) -> Optional[Skill]:
        result = await db.execute(select(Skill).where(Skill.id == skill_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_name(db: AsyncSession, name: str) -> Optional[Skill]:
        result = await db.execute(select(Skill).where(Skill.name == name))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_names(db: AsyncSession, names: list[str]) -> list[Skill]:
        """按名称列表批量加载已激活的技能"""
        if not names:
            return []
        result = await db.execute(
            select(Skill).where(Skill.name.in_(names), Skill.is_active == True)
        )
        return list(result.scalars().all())

    @staticmethod
    async def update(db: AsyncSession, skill: Skill, data: SkillUpdate) -> Skill:
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(skill, field):
                setattr(skill, field, value)
        await db.commit()
        await db.refresh(skill)
        logger.info("Skill updated: %s", skill.name)
        return skill

    @staticmethod
    async def delete(db: AsyncSession, skill: Skill) -> None:
        await db.delete(skill)
        await db.commit()
        logger.info("Skill deleted: %s", skill.name)

    @staticmethod
    async def toggle_active(db: AsyncSession, skill: Skill) -> Skill:
        skill.is_active = not skill.is_active
        await db.commit()
        await db.refresh(skill)
        logger.info("Skill %s toggled to %s", skill.name, skill.is_active)
        return skill

    @staticmethod
    async def list_skills(
        db: AsyncSession,
        layer: Optional[str] = None,
        topic: Optional[str] = None,
        category: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[int, list[Skill]]:
        conditions = []
        if layer:
            conditions.append(Skill.layer == layer)
        if topic:
            conditions.append(Skill.match_topic == topic)
        if category:
            conditions.append(Skill.category == category)

        count_q = select(func.count()).select_from(Skill).where(*conditions)
        total = (await db.execute(count_q)).scalar() or 0

        q = select(Skill).where(*conditions).order_by(Skill.layer, Skill.priority.desc()).offset(skip).limit(limit)
        items = list((await db.execute(q)).scalars().all())
        return total, items

    @staticmethod
    async def install_presets(db: AsyncSession) -> int:
        """安装所有未安装的预置技能"""
        installed = 0
        for preset in get_presets():
            existing = await SkillService.get_by_name(db, preset.name)
            if existing:
                continue
            await SkillService.create(
                db,
                SkillCreate(
                    name=preset.name,
                    description=preset.description,
                    layer=preset.layer,
                    content=preset.content,
                    match_topic=preset.match_topic,
                    category=preset.category,
                    priority=preset.priority,
                ),
            )
            installed += 1

        if installed:
            logger.info("Installed %d preset skills", installed)
        return installed

    @staticmethod
    async def install_preset(db: AsyncSession, preset_name: str) -> Skill:
        """安装单个预置技能"""
        preset = get_preset(preset_name)
        if not preset:
            raise ValueError(f"Preset skill '{preset_name}' not found")

        existing = await SkillService.get_by_name(db, preset_name)
        if existing:
            raise ValueError(f"Skill '{preset_name}' already exists")

        return await SkillService.create(
            db,
            SkillCreate(
                name=preset.name,
                description=preset.description,
                layer=preset.layer,
                content=preset.content,
                match_topic=preset.match_topic,
                category=preset.category,
                priority=preset.priority,
            ),
        )


# ═══════════════════════════════════════════════════
#  Hook Service
# ═══════════════════════════════════════════════════

class HookService:

    @staticmethod
    async def create(db: AsyncSession, data: HookCreate) -> Hook:
        hook = Hook(
            name=data.name,
            description=data.description,
            hook_point=data.hook_point.value,
            action_type=data.action_type.value,
            config=data.config,
            priority=data.priority,
            is_active=data.is_active,
        )
        db.add(hook)
        await db.commit()
        await db.refresh(hook)
        logger.info("Hook created: %s (%s)", hook.name, hook.hook_point)
        return hook

    @staticmethod
    async def get(db: AsyncSession, hook_id: str) -> Optional[Hook]:
        result = await db.execute(select(Hook).where(Hook.id == hook_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def update(db: AsyncSession, hook: Hook, data: HookUpdate) -> Hook:
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(hook, field):
                setattr(hook, field, value)
        await db.commit()
        await db.refresh(hook)
        logger.info("Hook updated: %s", hook.name)
        return hook

    @staticmethod
    async def delete(db: AsyncSession, hook: Hook) -> None:
        await db.delete(hook)
        await db.commit()
        logger.info("Hook deleted: %s", hook.name)

    @staticmethod
    async def toggle_active(db: AsyncSession, hook: Hook) -> Hook:
        hook.is_active = not hook.is_active
        await db.commit()
        await db.refresh(hook)
        logger.info("Hook %s toggled to %s", hook.name, hook.is_active)
        return hook

    @staticmethod
    async def list_hooks(
        db: AsyncSession,
        hook_point: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[int, list[Hook]]:
        conditions = []
        if hook_point:
            conditions.append(Hook.hook_point == hook_point)

        count_q = select(func.count()).select_from(Hook).where(*conditions)
        total = (await db.execute(count_q)).scalar() or 0

        q = select(Hook).where(*conditions).order_by(Hook.priority).offset(skip).limit(limit)
        items = list((await db.execute(q)).scalars().all())
        return total, items
