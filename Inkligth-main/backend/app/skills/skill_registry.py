"""
技能注册表 - 管理技能的加载、匹配和提示注入
"""

import logging
from enum import Enum
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.skills.models import Skill

logger = logging.getLogger(__name__)


class Layer(str, Enum):
    SOUL = "soul"
    AGENTS = "agents"
    IDENTITY = "identity"

    @classmethod
    def ordered(cls) -> list["Layer"]:
        """返回按注入顺序排列的层级列表"""
        return [cls.SOUL, cls.AGENTS, cls.IDENTITY]


class SkillRegistry:
    """技能注册表 - 管理技能加载、匹配和提示构建"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_active_skills(
        self,
        topic: Optional[str] = None,
        layers: Optional[list[Layer]] = None,
    ) -> list[Skill]:
        """获取激活的技能，按 layer + priority 排序

        Args:
            topic: 匹配主题（如果提供，只返回匹配该主题的技能）
            layers: 筛选层级（如果提供，只返回指定层级的技能）

        Returns:
            按 (layer排序顺序, priority降序) 排列的技能列表
        """
        conditions = [Skill.is_active == True]

        if layers:
            layer_values = [l.value for l in layers]
            conditions.append(Skill.layer.in_(layer_values))

        if topic:
            # 匹配 topic：空 topic 的技能通用，或者 topic 完全匹配
            from sqlalchemy import or_
            conditions.append(
                or_(
                    Skill.match_topic == topic,
                    Skill.match_topic.is_(None),
                )
            )

        q = select(Skill).where(*conditions)
        result = await self.db.execute(q)
        skills = list(result.scalars().all())

        # 按 layer 顺序 + priority 降序排序
        layer_order = {l.value: i for i, l in enumerate(Layer.ordered())}

        def sort_key(skill: Skill) -> tuple:
            return (layer_order.get(skill.layer, 99), -skill.priority)

        skills.sort(key=sort_key)
        return skills

    async def build_prompt_injection(
        self,
        topic: Optional[str] = None,
        layers: Optional[list[Layer]] = None,
    ) -> tuple[str, list[str]]:
        """构建技能注入文本，用于拼入 system prompt

        Returns:
            (注入文本, 已应用的技能名称列表)
        """
        skills = await self.get_active_skills(topic=topic, layers=layers)

        parts: list[str] = []
        names: list[str] = []

        for skill in skills:
            parts.append(
                f"<!-- SKILL: {skill.name} ({skill.layer}) -->\n{skill.content}"
            )
            names.append(skill.name)

        combined = "\n\n".join(parts)
        return combined, names

    @staticmethod
    def build_system_prompt(
        base_prompt: str,
        skill_injection: str,
    ) -> str:
        """将基础 system prompt 与技能注入合并

        Args:
            base_prompt: 基础 system prompt
            skill_injection: build_prompt_injection() 的返回值

        Returns:
            合并后的 system prompt
        """
        if not skill_injection:
            return base_prompt
        return f"{base_prompt}\n\n{skill_injection}"
