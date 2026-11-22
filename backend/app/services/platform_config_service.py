"""平台 AI 配置：管理员在后台「系统配置」页可视化管理的免费额度凭据。

四个 SystemConfig 键（category=platform，运行时生效，无需重启）：
- platform_ai_key:             平台兜底 API Key（**Fernet 加密存储**，接口只回掩码）
- platform_ai_base_url:        兜底服务地址（默认智谱）
- platform_ai_model:           免费档模型（默认 glm-4.7-flash；勿填付费模型以免消耗余额）
- platform_free_translations:  每用户赠送翻译篇数（默认 1）

解析优先级：SystemConfig 后台值（非空时）→ .env 环境变量 → 内置默认。
后台保存行为（platform_ai_key 特殊处理）：
- 提交为空 / 含掩码 **** → 保留现有 Key 不变；
- 提交新值 → Fernet 加密后入库；
- 清空配置（删除该键或值置空且无环境变量）→ 平台免费额度停用。
"""
import json
import logging

from sqlalchemy import select

from app.core.config import settings
from app.db.database import AlibabaSessionLocal
from app.models.admin import SystemConfig
from app.services.ai_engine_service import decrypt_api_key, encrypt_api_key, mask_api_key

logger = logging.getLogger(__name__)

SECRET_KEY_NAME = "platform_ai_key"

# 配置项在管理页的分组归属：其余键归入「平台免费额度」卡片
RECALL_SWITCH_KEY = "recall_emails_enabled"

PROVIDER_PRESETS_KEY = "provider_presets"

DEFAULT_PROVIDER_PRESETS = [
    {"provider": "glm", "label": "GLM (智谱)", "base_url": "https://open.bigmodel.cn/api/paas/v4",
     "model": "glm-4.7-flash", "free": True, "note": "glm-4.7-flash 完全免费，注册即可用"},
    {"provider": "siliconflow", "label": "硅基流动 SiliconFlow", "base_url": "https://api.siliconflow.cn/v1",
     "model": "Qwen/Qwen2.5-7B-Instruct", "free": True, "note": "免费档含多个开源模型，见官网模型中心"},
    {"provider": "openrouter", "label": "OpenRouter", "base_url": "https://openrouter.ai/api/v1",
     "model": "openrouter/free", "free": True, "note": "免费模型加 :free 后缀，或用 openrouter/free 自动路由"},
    {"provider": "qwen", "label": "Qwen (通义千问)", "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
     "model": "qwen-plus", "free": False, "note": "新用户各模型赠 100 万 tokens（90 天有效，需实名认证）"},
    {"provider": "deepseek", "label": "DeepSeek", "base_url": "https://api.deepseek.com",
     "model": "deepseek-chat", "free": False, "note": "按量付费，非高峰时段约半价"},
    {"provider": "kimi", "label": "Kimi (月之暗面)", "base_url": "https://api.moonshot.cn/v1",
     "model": "moonshot-v1-8k", "free": False, "note": "按量付费"},
    {"provider": "agnes", "label": "Agnes", "base_url": "https://apihub.agnes-ai.com/v1",
     "model": "agnes-2.0-flash", "free": True, "note": ""},
]


_CONFIG_LABELS = {
    "recall_emails_enabled": "自动召回邮件",
    PROVIDER_PRESETS_KEY: "供应商预设列表",
    "platform_ai_key": "平台兜底 API Key",
    "platform_ai_base_url": "平台兜底服务地址",
    "platform_ai_model": "平台兜底模型（免费档）",
    "platform_free_translations": "每用户赠送翻译篇数",
}

_CONFIG_DESCRIPTIONS = {
    "recall_emails_enabled": (
        "每天 10:00 自动发送提醒邮件：注册满 3 天未上传文献的用户，以及 30~60 天未登录的用户。"
        "每个用户每种邮件最多收到一封，不会重复骚扰。"
    ),
    PROVIDER_PRESETS_KEY: (
        "用户 AI 设置页下拉的预置供应商（JSON 数组）。"
        '每项格式：{"provider":"英文标识","label":"显示名","base_url":"API地址","model":"默认模型","free":true/false,"note":"说明"}。'
        "修改保存后用户端立即生效。"
    ),
    "platform_ai_key": "新用户免费翻译使用的服务 Key。保存后立即生效；列表中只显示掩码，提交含****的值表示不修改。",
    "platform_ai_base_url": "平台免费额度调用的服务地址（OpenAI 兼容）。",
    "platform_ai_model": "平台免费额度调用的模型。务必使用免费档模型（如 glm-4.7-flash），填付费模型会消耗账户余额！",
    "platform_free_translations": "每个新用户注册赠送的 PDF 文献翻译次数（篇）。设为 0 停止向新用户赠送。",
}

_BUILTIN_DEFAULTS = {
    "recall_emails_enabled": "false",
    PROVIDER_PRESETS_KEY: json.dumps(DEFAULT_PROVIDER_PRESETS, ensure_ascii=False, indent=2),
    "platform_ai_key": "",  # 默认无：未配置时平台免费额度停用
    "platform_ai_base_url": "https://open.bigmodel.cn/api/paas/v4",
    "platform_ai_model": "glm-4.7-flash",
    "platform_free_translations": "1",
}

# 供应商预设（用户 AI 设置页下拉动态读取；管理员可在系统配置 provider_presets 编辑 JSON）
# 信息核实于 2026-11（各平台官方文档），base_url 均为 OpenAI 兼容接口。
_ENV_FALLBACK = {
    "provider_presets": None,
    "platform_ai_key": "DEFAULT_AI_KEY",
    "platform_ai_base_url": "DEFAULT_AI_BASE_URL",
    "platform_ai_model": "PLATFORM_FALLBACK_MODEL",
    "platform_free_translations": "PLATFORM_FREE_TRANSLATIONS",
}


class PlatformConfigService:
    @staticmethod
    async def ensure_seeded() -> None:
        """启动时幂等写入 4 个配置行（带中文说明）；已存在的键不覆盖。"""
        try:
            async with AlibabaSessionLocal() as db:
                existing = (
                    await db.execute(
                        select(SystemConfig.key).where(
                            SystemConfig.key.in_(_CONFIG_LABELS.keys())
                        )
                    )
                ).scalars().all()
                missing = set(_CONFIG_LABELS) - set(existing)
                category_of = {
                    PROVIDER_PRESETS_KEY: "platform",
                    SECRET_KEY_NAME: "platform",
                    "platform_ai_base_url": "platform",
                    "platform_ai_model": "platform",
                    "platform_free_translations": "platform",
                    "recall_emails_enabled": "notification",
                }
                type_of = {
                    PROVIDER_PRESETS_KEY: "textarea",
                    "platform_free_translations": "number",
                    "recall_emails_enabled": "toggle",
                }
                for key in sorted(missing):
                    db.add(SystemConfig(
                        key=key,
                        value=_BUILTIN_DEFAULTS[key] if key != SECRET_KEY_NAME else None,
                        category=category_of.get(key, "general"),
                        config_type=type_of.get(key, "text"),
                        label=_CONFIG_LABELS[key],
                        description=_CONFIG_DESCRIPTIONS[key],
                        is_critical=key == SECRET_KEY_NAME,
                        requires_restart=False,
                        scope="admin",
                        default_value=_BUILTIN_DEFAULTS[key] or None,
                    ))
                if missing:
                    await db.commit()
                    logger.info("平台 AI 配置项已写入系统配置: %s", sorted(missing))
        except Exception as e:
            logger.warning("平台 AI 配置种子写入失败（不影响启动）: %s", e)

    @staticmethod
    async def _get_raw(key: str) -> str | None:
        """读取后台配置原值（platform_ai_key 返回的是密文）。不存在/为空 → None。"""
        async with AlibabaSessionLocal() as db:
            row = (
                await db.execute(select(SystemConfig).where(SystemConfig.key == key))
            ).scalar_one_or_none()
        if row is None or row.value is None or str(row.value).strip() == "":
            return None
        return str(row.value).strip()

    @staticmethod
    async def resolve() -> dict:
        """解析平台兜底凭据：DB 优先 → 环境变量 → 内置默认。

        返回 {key, base_url, model, free_translations, configured}；
        key 为解密后的明文，仅供服务端调用使用。
        """
        # key：后台密文 → 解密；失败视为未配置（防止改坏后全站报错）
        key = None
        encrypted = await PlatformConfigService._get_raw(SECRET_KEY_NAME)
        if encrypted:
            try:
                key = decrypt_api_key(encrypted)
            except Exception as e:
                logger.error("platform_ai_key 解密失败，平台免费额度停用: %s", e)
        if not key:
            key = settings.DEFAULT_AI_KEY or None

        # base_url / model / 篇数：后台值 → 环境变量 → 内置默认
        base_url = await PlatformConfigService._get_raw("platform_ai_base_url") \
            or settings.DEFAULT_AI_BASE_URL \
            or _BUILTIN_DEFAULTS["platform_ai_base_url"]

        model = await PlatformConfigService._get_raw("platform_ai_model") \
            or settings.PLATFORM_FALLBACK_MODEL \
            or _BUILTIN_DEFAULTS["platform_ai_model"]

        raw_free = await PlatformConfigService._get_raw("platform_free_translations")
        raw_free = raw_free or str(settings.PLATFORM_FREE_TRANSLATIONS)
        try:
            free_translations = max(0, int(raw_free))
        except ValueError:
            logger.warning("platform_free_translations 配置非法（%r），回退默认 1", raw_free)
            free_translations = 1

        return {
            "key": key,
            "base_url": base_url,
            "model": model,
            "free_translations": free_translations,
            "configured": bool(key),
        }

    @staticmethod
    async def get_provider_presets() -> list[dict]:
        """读取供应商预设：解析后台 JSON；非法/为空时回退内置默认。

        每项字段：provider(标识)、label(显示名)、base_url、model、free(免费?)、note(说明)。
        缺少必填字段的项会被过滤，保证用户下拉不会出现坏数据。
        """
        try:
            raw = await PlatformConfigService._get_raw(PROVIDER_PRESETS_KEY)
        except Exception as e:
            logger.warning("provider_presets 读取失败，回退内置默认: %s", e)
            raw = None

        candidates = None
        if raw:
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    candidates = parsed
            except json.JSONDecodeError as e:
                logger.warning("provider_presets JSON 解析失败，回退内置默认: %s", e)

        if candidates is None:
            candidates = DEFAULT_PROVIDER_PRESETS

        presets = []
        for item in candidates:
            if not isinstance(item, dict):
                continue
            provider = str(item.get("provider") or "").strip()
            label = str(item.get("label") or "").strip()
            base_url = str(item.get("base_url") or "").strip()
            model = str(item.get("model") or "").strip()
            if not (provider and label and base_url and model):
                continue
            presets.append({
                "provider": provider[:50],
                "label": label[:80],
                "base_url": base_url[:300],
                "model": model[:100],
                "free": bool(item.get("free")),
                "note": str(item.get("note") or "")[:200],
            })
        if not presets:
            return [dict(x) for x in DEFAULT_PROVIDER_PRESETS]
        return presets

    @staticmethod
    def mask_config_value(key: str, value: str | None) -> str | None:
        """对外展示/审计日志用的掩码：platform_ai_key 解密后掩码，其余原样。"""
        if key != SECRET_KEY_NAME:
            return value
        if not value:
            return None
        try:
            return mask_api_key(decrypt_api_key(value))
        except Exception:
            return "已配置（无法解析）"

    @staticmethod
    def normalize_incoming_secret(key: str, value: str | None) -> str | None:
        """后台提交 platform_ai_key 的规范化：空串/掩码 → None（保持现状），新值 → 加密。"""
        if key != SECRET_KEY_NAME:
            return value
        stripped = (value or "").strip()
        if not stripped or "****" in stripped:
            return None
        return encrypt_api_key(stripped)
