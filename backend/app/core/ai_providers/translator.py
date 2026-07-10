import asyncio
import hashlib
import logging
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, AsyncGenerator

from openai import AsyncOpenAI

try:
    from openai import BadRequestError
except ImportError:
    BadRequestError = Exception

logger = logging.getLogger(__name__)

PARAGRAPH_MAX_CHARS = 2000
PARAGRAPH_MERGE_MIN = 200
PARAGRAPH_MERGE_TARGET = 1000
MAX_CONCURRENT_PARAGRAPHS = 5

_TRANSLATION_CACHE_TTL = 3600
_TRANSLATION_CACHE_MAX = 2000
_translation_cache: dict[str, tuple[float, str]] = {}

STREAM_TIMEOUT = 60.0
STREAM_RETRIES = 2
STREAM_RETRY_BACKOFF_BASE = 1.5

TOKEN_LIMIT_KEYWORDS = (
    "maximum context length", "reduce the length", "too many tokens",
    "token limit", "context_length_exceeded", "max_tokens",
)

REASONING_TAG_PATTERN = re.compile(
    r'<\s*(?:think|thinking|Thought|reasoning|analysis|scratchpad)\s*>'
    r'.*?'
    r'<\s*/\s*(?:think|thinking|Thought|reasoning|analysis|scratchpad)\s*>',
    re.DOTALL,
)

TRANSLATION_MAX_OUTPUT_TOKENS = 4096
MIN_MAX_OUTPUT_TOKENS = 500
MAX_TOKENS_INPUT_RATIO = 5

TOKEN_WASTE_RATIO_THRESHOLD = 10
TOKEN_WASTE_ABSOLUTE_THRESHOLD = 1000

STOP_TOKENS_ENV_KEY = "TRANSLATION_STOP_TOKENS"
_DEFAULT_STOP_TOKENS: list[str] = ["\n\n\n", "Explanation:", "Note:", "说明：", "注："]
GLM_MAX_STOP_TOKENS = 4
GLM_RATE_LIMIT_RETRIES = 3
GLM_RATE_LIMIT_BACKOFF_BASE = 2.0
GLM_INTER_PARAGRAPH_DELAY = 1.5
RATE_LIMIT_KEYWORDS_429 = ("429", "rate limit", "速率限制", "访问量过大", "1302", "1305", "并发数过高", "频率过高")
PROVIDER_MAX_CONCURRENCY: dict[str, int] = {
    "glm": 1,
    "zhipu": 1,
}
# 模型专属 stop tokens 覆盖：None 表示不传 stop tokens
PROVIDER_STOP_TOKENS: dict[str, list[str] | None] = {
    "agnes": None,
}
_UNSET = object()
_stop_tokens_cache: list[str] | None | object = _UNSET


def _lazy_has_pdf_math_indicators(text: str) -> bool:
    from app.services.formula_protection_service import has_pdf_math_indicators
    return has_pdf_math_indicators(text)

COMMON_PREAMBLE_PATTERNS = [
    re.compile(r'^[,，。；\s]*'),
    re.compile(r'^(?:好的|当然|以下是|翻译(?:如下|结果)?|译文(?:如下)?)[:：，,\s]*', re.IGNORECASE),
    re.compile(r'^(?:Here\s+is|The\s+translation|Sure|Certainly|OK|Alright)[,:\s]+', re.IGNORECASE),
    re.compile(r'^(?:翻译内容|翻译文本|源文本|原文)[:：，,\s]*'),
]


@dataclass
class TranslationTiming:
    preprocess_ms: float = 0.0
    cache_lookup_ms: float = 0.0
    api_request_ms: float = 0.0
    api_stream_ms: float = 0.0
    postprocess_ms: float = 0.0
    total_ms: float = 0.0
    paragraph_count: int = 0
    cache_hits: int = 0
    first_token_ms: float = 0.0
    chunk_count: int = 0
    input_chars: int = 0

    def summary(self) -> str:
        parts = [f"total={self.total_ms:.0f}ms"]
        if self.input_chars > 0:
            parts.append(f"input={self.input_chars}chars")
        parts.append(f"paragraphs={self.paragraph_count}")
        parts.append(f"preprocess={self.preprocess_ms:.0f}ms")
        if self.cache_lookup_ms > 0:
            parts.append(f"cache_lookup={self.cache_lookup_ms:.0f}ms")
        if self.cache_hits > 0:
            parts.append(f"cache_hits={self.cache_hits}")
        if self.api_request_ms > 0:
            parts.append(f"api_request={self.api_request_ms:.0f}ms")
        if self.api_stream_ms > 0:
            parts.append(f"api_stream={self.api_stream_ms:.0f}ms")
        if self.first_token_ms > 0:
            parts.append(f"first_token={self.first_token_ms:.0f}ms")
            parts.append(f"chunks={self.chunk_count}")
        if self.postprocess_ms > 0:
            parts.append(f"postprocess={self.postprocess_ms:.0f}ms")
        return " | ".join(parts)


def _cache_key(text: str, source_lang: str, target_lang: str) -> str:
    raw = f"{text}|{source_lang}|{target_lang}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _cache_get(text: str, source_lang: str, target_lang: str) -> Optional[str]:
    key = _cache_key(text, source_lang, target_lang)
    entry = _translation_cache.get(key)
    if entry is None:
        return None
    ts, result = entry
    if time.monotonic() - ts > _TRANSLATION_CACHE_TTL:
        del _translation_cache[key]
        return None
    return result


def _cache_set(text: str, source_lang: str, target_lang: str, result: str) -> None:
    if len(_translation_cache) >= _TRANSLATION_CACHE_MAX:
        oldest = min(_translation_cache, key=lambda k: _translation_cache[k][0])
        del _translation_cache[oldest]
    key = _cache_key(text, source_lang, target_lang)
    _translation_cache[key] = (time.monotonic(), result)


def _is_token_limit_error(error: Exception) -> bool:
    msg = str(error).lower()
    return any(kw in msg for kw in TOKEN_LIMIT_KEYWORDS)


def _is_rate_limit_error(error: Exception) -> bool:
    msg = str(error).lower()
    return any(kw in msg for kw in RATE_LIMIT_KEYWORDS_429)


def beautify_translation_error(raw_error: str) -> str:
    if not raw_error:
        return "翻译失败，请重试"

    err_lower = raw_error.lower()

    if "403" in err_lower and "quota" in err_lower:
        return "API 配额已用尽，请在管理控制台充值或切换付费方案后重试"
    if "429" in err_lower:
        return "请求过于频繁，请稍后重试"
    if "401" in err_lower or "invalid api key" in err_lower:
        return "API 密钥无效，请在设置中更新 API 密钥"
    if "timeout" in err_lower:
        return "翻译请求超时，请稍后重试或缩短文本长度"
    if "free tier" in err_lower:
        return "免费额度已用尽，请在管理控制台关闭「仅使用免费层」或切换到付费方案"

    match = re.search(r"Error code: (\d+).*?message['\"]?\s*:\s*['\"]([^'\"]+)", raw_error)
    if match:
        code = match.group(1)
        msg = match.group(2)
        return f"API 错误 ({code}): {msg}"

    extra_match = re.search(r"\{\s*'error'[^}]*'message'\s*:\s*'([^']+)'", raw_error)
    if extra_match:
        msg = extra_match.group(1)
        if "quota" in msg.lower() or "free tier" in msg.lower():
            return f"API 配额不足: {msg}"

    if len(raw_error) > 120:
        return raw_error[:120] + "…"
    return raw_error


def split_paragraphs(text: str) -> list[str]:
    paragraphs = []
    for block in text.split("\n\n"):
        block = block.strip()
        if not block:
            continue
        sub_blocks = [s.strip() for s in block.split("\n") if s.strip()]
        if len(sub_blocks) <= 3:
            for sb in sub_blocks:
                if len(sb) <= PARAGRAPH_MAX_CHARS:
                    paragraphs.append(sb)
                else:
                    paragraphs.extend(_chunk_text(sb, PARAGRAPH_MAX_CHARS))
        else:
            if len(block) <= PARAGRAPH_MAX_CHARS:
                paragraphs.append(block)
            else:
                paragraphs.extend(_chunk_text(block, PARAGRAPH_MAX_CHARS))

    if len(paragraphs) <= 1:
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        paragraphs = []
        current = ""
        for line in lines:
            if len(current) + len(line) > PARAGRAPH_MAX_CHARS and current:
                paragraphs.append(current.strip())
                current = line
            else:
                current = current + "\n" + line if current else line
        if current.strip():
            paragraphs.append(current.strip())

    return _merge_small_paragraphs(paragraphs)


def _merge_small_paragraphs(paragraphs: list[str]) -> list[str]:
    if len(paragraphs) <= 1:
        return paragraphs
    merged = []
    buffer = ""
    for para in paragraphs:
        if not buffer:
            buffer = para
            continue
        if len(buffer) < PARAGRAPH_MERGE_MIN or (len(buffer) + len(para) + 1) <= PARAGRAPH_MERGE_TARGET:
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
    return chunks


class BaseTranslator(ABC):
    @abstractmethod
    async def translate(
        self,
        text: str,
        source_lang: str = "en",
        target_lang: str = "zh",
        timeout: float = 60.0,
    ) -> str:
        pass

    @abstractmethod
    async def translate_stream(
        self,
        text: str,
        source_lang: str = "en",
        target_lang: str = "zh",
    ) -> AsyncGenerator[str, None]:
        pass


def _is_glm_provider(model: str) -> bool:
    model_lower = model.lower()
    return model_lower.startswith("glm") or "zhipu" in model_lower or "chatglm" in model_lower


def _get_max_concurrent_for_model(model: str) -> int:
    model_lower = model.lower()
    for key, limit in PROVIDER_MAX_CONCURRENCY.items():
        if key in model_lower:
            logger.info(
                "GLM detected: lowering max concurrent paragraphs from %d to %d for model '%s'",
                MAX_CONCURRENT_PARAGRAPHS, limit, model,
            )
            return limit
    return MAX_CONCURRENT_PARAGRAPHS


class OpenAITranslator(BaseTranslator):
    def __init__(self, client: AsyncOpenAI, model: str, cancel_check=None):
        self.client = client
        self.model = model
        self._cancel_check = cancel_check
        self._total_prompt_tokens: int = 0
        self._total_completion_tokens: int = 0
        self._total_tokens: int = 0

    def _is_cancelled(self) -> bool:
        if self._cancel_check is None:
            return False
        return self._cancel_check()

    async def _call_llm_cancellable(self, params: dict):
        task = asyncio.create_task(self.client.chat.completions.create(**params))
        try:
            while not task.done():
                if self._is_cancelled():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                    return None
                await asyncio.sleep(0.1)
            return task.result()
        except asyncio.CancelledError:
            if not task.done():
                task.cancel()
            return None

    COMBINED_TRANSLATION_PROMPT: str = (
        "You are a professional, authentic machine translation engine. "
        "Only Output the translated text, do not include any other text."
        "\n\n"
        "Translate the following source text to {target_lang}. "
        "Output translation directly without any additional text."
        "\n\n"
        "Source Text: {text}"
        "\n\n"
        "Translated Text:"
    )

    COMBINED_FORMULA_PROMPT: str = (
        "You are a professional, authentic machine translation engine. "
        "Only Output the translated text, do not include any other text."
        "\n\n"
        "Translate the following markdown source text to {target_lang}. "
        "Keep the formula notation {{v*}} unchanged. "
        "Output translation directly without any additional text."
        "\n\n"
        "Source Text: {text}"
        "\n\n"
        "Translated Text:"
    )

    @staticmethod
    def _compute_max_tokens(text_len: int) -> int:
        dynamic = max(MIN_MAX_OUTPUT_TOKENS, text_len * MAX_TOKENS_INPUT_RATIO)
        return min(dynamic, TRANSLATION_MAX_OUTPUT_TOKENS)

    @staticmethod
    def _get_stop_tokens(model: str | None = None) -> list[str] | None:
        global _stop_tokens_cache
        if _stop_tokens_cache is not _UNSET:
            tokens: list[str] | None = _stop_tokens_cache  # type: ignore[assignment]
        else:
            from app.core.config import settings
            env_val: str = getattr(settings, STOP_TOKENS_ENV_KEY, '') or ''
            if env_val:
                tokens = [t.strip() for t in env_val.split(',') if t.strip()]
                tokens = tokens if tokens else None
            else:
                tokens = list(_DEFAULT_STOP_TOKENS)
            _stop_tokens_cache = tokens  # type: ignore[assignment]

        if tokens and model and _is_glm_provider(model) and len(tokens) > GLM_MAX_STOP_TOKENS:
            logger.info(
                "Truncating stop tokens from %d to %d for GLM provider (max %d)",
                len(tokens), GLM_MAX_STOP_TOKENS, GLM_MAX_STOP_TOKENS,
            )
            return tokens[:GLM_MAX_STOP_TOKENS]

        # 模型专属 stop tokens 覆盖
        if model:
            model_lower = model.lower()
            for key, override in PROVIDER_STOP_TOKENS.items():
                if key in model_lower:
                    logger.info(
                        "Overriding stop tokens for model '%s' (matched '%s'): %s",
                        model, key, override,
                    )
                    return override

        return tokens

    @staticmethod
    def _build_combined_prompt(text: str, source_lang: str, target_lang: str, has_formula: bool = False) -> str:
        _ = source_lang
        tgt = OpenAITranslator.LANG_DISPLAY.get(target_lang, target_lang)
        template = OpenAITranslator.COMBINED_FORMULA_PROMPT if has_formula else OpenAITranslator.COMBINED_TRANSLATION_PROMPT
        return template.format(target_lang=tgt, text=text)

    LANG_DISPLAY: dict[str, str] = {
        "en": "英文", "zh": "中文", "zh-CN": "简体中文", "zh-TW": "繁体中文",
        "ja": "日文", "ko": "韩文", "fr": "法文", "de": "德文",
        "es": "西班牙文", "ru": "俄文", "ar": "阿拉伯文", "pt": "葡萄牙文",
    }

    @staticmethod
    def _build_prompt(text: str, source_lang: str, target_lang: str) -> str:
        return OpenAITranslator._build_combined_prompt(text, source_lang, target_lang, has_formula=False)

    def _log_usage(self, label: str, usage, message, input_len: int, output_len: int, elapsed_ms: float) -> None:
        reasoning_info = self._extract_reasoning_info(message, usage)
        if usage is None:
            logger.warning(
                "TOKEN USAGE [%s] | input_chars=%d output_chars=%d elapsed=%.0fms | usage=N/A",
                label, input_len, output_len, elapsed_ms,
            )
            return
        prompt_tokens = getattr(usage, 'prompt_tokens', 0)
        completion_tokens = getattr(usage, 'completion_tokens', 0)
        total_tokens = getattr(usage, 'total_tokens', 0)
        reasoning_tokens = reasoning_info.get("reasoning_tokens", 0)
        non_reasoning_completion = completion_tokens - reasoning_tokens
        self._total_prompt_tokens += prompt_tokens
        self._total_completion_tokens += completion_tokens
        self._total_tokens += total_tokens
        if reasoning_tokens > 0:
            logger.warning(
                "TOKEN USAGE [%s] | input_chars=%d output_chars=%d elapsed=%.0fms | "
                "prompt_tokens=%d completion_tokens=%d(%dreasoning+%doutput) total_tokens=%d | "
                "cumulative_prompt=%d cumulative_completion=%d cumulative_total=%d",
                label, input_len, output_len, elapsed_ms,
                prompt_tokens, completion_tokens, reasoning_tokens, non_reasoning_completion, total_tokens,
                self._total_prompt_tokens, self._total_completion_tokens, self._total_tokens,
            )
        else:
            logger.warning(
                "TOKEN USAGE [%s] | input_chars=%d output_chars=%d elapsed=%.0fms | "
                "prompt_tokens=%d completion_tokens=%d total_tokens=%d | "
                "cumulative_prompt=%d cumulative_completion=%d cumulative_total=%d",
                label, input_len, output_len, elapsed_ms,
                prompt_tokens, completion_tokens, total_tokens,
                self._total_prompt_tokens, self._total_completion_tokens, self._total_tokens,
            )

    @staticmethod
    def _extract_reasoning_info(message, usage) -> dict:
        info: dict = {"reasoning_tokens": 0, "has_reasoning_content": False}
        if message is not None:
            reasoning_content = getattr(message, 'reasoning_content', None)
            if reasoning_content:
                info["has_reasoning_content"] = True
                info["reasoning_content_length"] = len(str(reasoning_content))
        if usage is not None:
            details = getattr(usage, 'completion_tokens_details', None)
            if details is not None:
                rt = getattr(details, 'reasoning_tokens', None)
                if rt is not None:
                    info["reasoning_tokens"] = rt
        return info

    def _is_reasoning_model(self, model_name: str | None = None) -> bool:
        name = (model_name or self.model).lower()
        reasoning_keywords = [
            "r1", "reasoner", "qwq", "o1", "o3", "o4",
            "k2.5", "k2.6", "m2.5", "m2.7", "thinking",
            "gemini-2.5-pro",
        ]
        return any(kw in name for kw in reasoning_keywords)

    REASONING_TO_NON_REASONING: dict[str, str] = {
        "deepseek-r1": "deepseek-v4-flash",
        "deepseek-r1-0528": "deepseek-v4-flash",
        "deepseek-reasoner": "deepseek-v4-flash",
        "qwen3-max-thinking": "qwen3.6-plus",
        "qwq-32b": "qwen3.6-plus",
        "o3": "gpt-5-nano",
        "o4-mini": "gpt-5-nano",
        "o1": "gpt-4o",
        "glm-5.1": "glm-4.7-flash",
        "kimi-k2.5": "kimi-k2-instruct-0905",
        "kimi-k2.6": "kimi-k2-instruct-0905",
        "m2.5": "MiniMax-Text-01",
        "m2.7": "MiniMax-Text-01",
        "gemini-2.5-pro": "gemini-3.5-flash",
    }

    NON_THINKING_PARAMS: dict[str, dict] = {
        "deepseek-v4-flash": {"extra_body": {"thinking": {"type": "disabled"}}},
        "deepseek-v4-pro": {"extra_body": {"thinking": {"type": "disabled"}}},
        "glm-4.7-flash": {"extra_body": {"thinking": {"type": "disabled"}}},
        "glm-4.5-flash": {"extra_body": {"thinking": {"type": "disabled"}}},
    }

    def _resolve_model(self) -> str:
        resolved = self.REASONING_TO_NON_REASONING.get(self.model.lower(), self.model)
        if resolved != self.model:
            logger.warning(
                "[Model Auto-Downgrade] Replaced reasoning model '%s' with '%s'",
                self.model, resolved,
            )
        elif self._is_reasoning_model(self.model):
            logger.warning(
                "[Reasoning Model] Model '%s' is a reasoning model but no replacement mapping exists. "
                "Using as-is. Consider configuring a non-reasoning model.",
                self.model,
            )
        return resolved

    def _get_non_thinking_params(self, model_name: str) -> dict:
        return self.NON_THINKING_PARAMS.get(model_name.lower(), {})

    def _get_max_concurrent(self) -> int:
        return _get_max_concurrent_for_model(self.model)

    @staticmethod
    def _clean_reasoning_output(text: str) -> str:
        cleaned = REASONING_TAG_PATTERN.sub('', text).strip()
        if not cleaned and text.strip():
            last_tag_end = 0
            for m in REASONING_TAG_PATTERN.finditer(text):
                last_tag_end = max(last_tag_end, m.end())
            after = text[last_tag_end:].strip()
            if after:
                cleaned = after
        return cleaned

    def get_usage_summary(self) -> dict:
        return {
            "total_prompt_tokens": self._total_prompt_tokens,
            "total_completion_tokens": self._total_completion_tokens,
            "total_tokens": self._total_tokens,
        }

    @staticmethod
    def _strip_preamble(text: str) -> str:
        for pattern in COMMON_PREAMBLE_PATTERNS:
            text = pattern.sub('', text, count=1)
        return text

    def _validate_and_clean_output(
        self, raw_output: str, source_text: str, usage, label: str,
    ) -> str:
        raw_output = self._clean_reasoning_output(raw_output)

        cleaned = self._strip_preamble(raw_output.strip())

        if len(cleaned) > len(source_text) * 3:
            prefix = source_text[:50].strip()
            if prefix and cleaned.startswith(prefix):
                logger.warning(
                    "OUTPUT CONTAINS REPEATED INPUT [%s] | removing echoed source text "
                    "from output (output=%d chars, input=%d chars)",
                    label, len(cleaned), len(source_text),
                )
                cleaned = cleaned[len(prefix):].strip()
                cleaned = self._strip_preamble(cleaned)

        if usage is not None:
            completion_tokens = getattr(usage, 'completion_tokens', 0)
            reasoning_info = self._extract_reasoning_info(None, usage)
            reasoning_tokens = reasoning_info.get("reasoning_tokens", 0)
            effective_output_tokens = completion_tokens - reasoning_tokens

            if effective_output_tokens > 0 and len(cleaned) > 0:
                ratio = effective_output_tokens / max(len(cleaned), 1)
                if ratio > TOKEN_WASTE_RATIO_THRESHOLD and effective_output_tokens > TOKEN_WASTE_ABSOLUTE_THRESHOLD:
                    logger.warning(
                        "TOKEN WASTE ALERT [%s] | output_chars=%d completion_tokens=%d "
                        "reasoning_tokens=%d effective_tokens=%d ratio=%.1fx threshold=%.1fx | "
                        "Model may be generating excessive hidden/reasoning content",
                        label, len(cleaned), completion_tokens,
                        reasoning_tokens, effective_output_tokens, ratio, TOKEN_WASTE_RATIO_THRESHOLD,
                    )

        return cleaned

    @staticmethod
    def _build_formula_prompt(text: str, source_lang: str, target_lang: str) -> str:
        src = OpenAITranslator.LANG_DISPLAY.get(source_lang, source_lang)
        tgt = OpenAITranslator.LANG_DISPLAY.get(target_lang, target_lang)
        return (
            f"将以下{src}翻译为{tgt}。\n"
            f"严格只输出纯译文，不要输出原文、不要解释、不要前缀标签、不要任何额外内容。\n"
            f"注意：文本中的 {{v0}}, {{v1}} 等占位符是数学公式，"
            f"必须原样保留在译文中，不要翻译或修改这些占位符。\n\n"
            f"{text}"
        )

    async def translate(
        self,
        text: str,
        source_lang: str = "en",
        target_lang: str = "zh",
        timeout: float = 60.0,
    ) -> str:
        cached = _cache_get(text, source_lang, target_lang)
        if cached is not None:
            return cached

        has_formulas = _lazy_has_pdf_math_indicators(text)
        if has_formulas:
            from app.services.formula_protection_service import FormulaProtectionService
            fsvc = FormulaProtectionService()
            protected = fsvc.protect_text(text)
            try:
                result = await self._translate_with_formula_prompt(protected, source_lang, target_lang, timeout)
            except BadRequestError as e:
                if _is_token_limit_error(e):
                    logger.warning("Token limit in formula-protected translate, auto-splitting (%d chars)", len(text))
                    chunks = _chunk_text(text, PARAGRAPH_MAX_CHARS // 2)
                    sem = asyncio.Semaphore(self._get_max_concurrent())
                    results: dict[int, str] = {}

                    async def _translate_chunk(idx: int, chunk: str) -> None:
                        async with sem:
                            try:
                                csvc = FormulaProtectionService()
                                cprotected = csvc.protect_text(chunk)
                                raw = await self._translate_with_formula_prompt(cprotected, source_lang, target_lang, timeout)
                                results[idx] = csvc.restore_text(raw)
                            except Exception as inner_e:
                                logger.error("Auto-split chunk %d failed: %s", idx, inner_e)
                                results[idx] = f"[翻译失败: {beautify_translation_error(str(inner_e))}]"

                    await asyncio.gather(*[_translate_chunk(i, c) for i, c in enumerate(chunks)])
                    result = " ".join(results[i] for i in range(len(chunks)))
                else:
                    raise
            result = fsvc.restore_text(result)
        else:
            try:
                result = await self._translate_raw(text, source_lang, target_lang, timeout)
            except BadRequestError as e:
                if _is_token_limit_error(e):
                    logger.warning("Token limit exceeded, auto-splitting text (%d chars)", len(text))
                    chunks = _chunk_text(text, PARAGRAPH_MAX_CHARS // 2)
                    sem = asyncio.Semaphore(self._get_max_concurrent())
                    results: dict[int, str] = {}

                    async def _translate_chunk(idx: int, chunk: str) -> None:
                        async with sem:
                            try:
                                results[idx] = await self._translate_raw(
                                    chunk, source_lang, target_lang, timeout
                                )
                            except Exception as inner_e:
                                logger.error("Auto-split chunk %d failed: %s", idx, inner_e)
                                results[idx] = f"[翻译失败: {beautify_translation_error(str(inner_e))}]"

                    await asyncio.gather(*[_translate_chunk(i, c) for i, c in enumerate(chunks)])
                    result = " ".join(results[i] for i in range(len(chunks)))
                else:
                    raise

        _cache_set(text, source_lang, target_lang, result)
        return result

    async def _translate_raw(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        timeout: float,
    ) -> str:
        if self._is_cancelled():
            return text

        t_start = time.perf_counter()
        effective_model = self._resolve_model()
        merged_prompt = self._build_prompt(text, source_lang, target_lang)

        messages: list[dict] = [{"role": "user", "content": merged_prompt}]

        max_tokens = self._compute_max_tokens(len(text))

        params: dict = {
            "model": effective_model,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": max_tokens,
            "timeout": timeout,
        }
        stop_tokens = self._get_stop_tokens(effective_model)
        if stop_tokens:
            params["stop"] = stop_tokens

        non_thinking = self._get_non_thinking_params(effective_model)
        if non_thinking:
            params.update(non_thinking)

        is_glm = _is_glm_provider(effective_model)
        max_attempts = GLM_RATE_LIMIT_RETRIES + 1 if is_glm else 1
        response = None
        last_error: Exception | None = None

        for attempt in range(max_attempts):
            if self._is_cancelled():
                return text

            if attempt > 0:
                delay = GLM_RATE_LIMIT_BACKOFF_BASE ** (attempt - 1)
                logger.warning(
                    "GLM rate limit retry %d/%d for translate_raw (%d chars), waiting %.1fs",
                    attempt, GLM_RATE_LIMIT_RETRIES, len(text), delay,
                )
                await asyncio.sleep(delay)
                if self._is_cancelled():
                    return text

            try:
                response = await self._call_llm_cancellable(params)
                if response is None:
                    return text
                break
            except Exception as e:
                last_error = e
                if is_glm and _is_rate_limit_error(e) and attempt < max_attempts - 1:
                    continue
                raise

        if response is None and last_error is not None:
            raise last_error

        raw_result = response.choices[0].message.content
        if raw_result is None:
            raw_result = ""

        if not raw_result.strip():
            reasoning_content = getattr(response.choices[0].message, 'reasoning_content', None)
            if reasoning_content and str(reasoning_content).strip():
                logger.warning(
                    "_translate_raw: content empty but reasoning_content present (%d chars), "
                    "using reasoning_content as fallback. Add NON_THINKING_PARAMS for this model.",
                    len(str(reasoning_content)),
                )
                raw_result = str(reasoning_content)

        result = self._validate_and_clean_output(
            raw_result, text, getattr(response, 'usage', None), "_translate_raw",
        )

        elapsed = (time.perf_counter() - t_start) * 1000
        logger.debug(
            "_translate_raw: %d chars input -> %d chars output (raw=%d), %.0fms, max_tokens=%d stop=%s non_thinking=%s",
            len(text), len(result), len(raw_result), elapsed, max_tokens, bool(stop_tokens), bool(non_thinking),
        )
        self._log_usage(
            "_translate_raw",
            getattr(response, 'usage', None),
            response.choices[0].message,
            len(text),
            len(result),
            elapsed,
        )
        return result

    async def translate_stream(
        self,
        text: str,
        source_lang: str = "en",
        target_lang: str = "zh",
    ) -> AsyncGenerator[str, None]:
        if self._is_cancelled():
            return

        t_start = time.perf_counter()
        first_token = True
        first_token_ms = 0.0
        chunk_count = 0
        effective_model = self._resolve_model()
        merged_prompt = self._build_prompt(text, source_lang, target_lang)
        is_reasoning = self._is_reasoning_model(self.model)
        last_error = ""

        messages: list[dict] = [{"role": "user", "content": merged_prompt}]

        max_tokens = self._compute_max_tokens(len(text))

        stream_params: dict = {
            "model": effective_model,
            "messages": messages,
            "stream": True,
            "temperature": 0.3,
            "max_tokens": max_tokens,
            "timeout": STREAM_TIMEOUT,
        }
        stop_tokens = self._get_stop_tokens(effective_model)
        if stop_tokens:
            stream_params["stop"] = stop_tokens

        non_thinking = self._get_non_thinking_params(effective_model)
        if non_thinking:
            stream_params.update(non_thinking)

        for attempt in range(STREAM_RETRIES + 1):
            try:
                stream = await self.client.chat.completions.create(**stream_params)
                async for chunk in stream:
                    if self._is_cancelled():
                        return
                    if not chunk.choices:
                        continue
                    delta = chunk.choices[0].delta
                    if delta and delta.content:
                        if first_token:
                            first_token_ms = (time.perf_counter() - t_start) * 1000
                            first_token = False
                        chunk_count += 1
                        yield delta.content
                elapsed = (time.perf_counter() - t_start) * 1000
                logger.debug(
                    "translate_stream: %d chars input, %d chunks, first_token=%.0fms, total=%.0fms",
                    len(text), chunk_count, first_token_ms, elapsed,
                )
                logger.warning(
                    "TOKEN USAGE [translate_stream] | input_chars=%d chunks=%d elapsed=%.0fms | "
                    "streaming - usage not available | model=%s reasoning=%s",
                    len(text), chunk_count, elapsed, self.model, is_reasoning,
                )
                return
            except Exception as e:
                last_error = str(e)
                err_lower = last_error.lower()
                retryable = any(k in err_lower for k in ("429", "rate limit", "timeout", "connection", "reset", "503", "502"))
                if retryable and attempt < STREAM_RETRIES:
                    delay = STREAM_RETRY_BACKOFF_BASE ** attempt
                    logger.warning(
                        "translate_stream attempt %d/%d failed: %s, retrying in %.1fs",
                        attempt + 1, STREAM_RETRIES + 1, e, delay
                    )
                    await asyncio.sleep(delay)
                    first_token = True
                    first_token_ms = 0.0
                    chunk_count = 0
                else:
                    elapsed = (time.perf_counter() - t_start) * 1000
                    logger.error(
                        "translate_stream failed after %.0fms (attempts=%d): %s",
                        elapsed, attempt + 1, e
                    )
                    raise

        if last_error:
            raise RuntimeError(last_error)

    async def translate_paragraphs(
        self,
        text: str,
        source_lang: str = "en",
        target_lang: str = "zh",
        timeout: float = 60.0,
    ) -> tuple[str, TranslationTiming]:
        timing = TranslationTiming()
        t_start = time.perf_counter()

        t0 = time.perf_counter()
        paragraphs = split_paragraphs(text)
        timing.preprocess_ms = (time.perf_counter() - t0) * 1000
        timing.paragraph_count = len(paragraphs)

        if len(paragraphs) <= 1:
            t_cache = time.perf_counter()
            cached = _cache_get(text, source_lang, target_lang)
            timing.cache_lookup_ms = (time.perf_counter() - t_cache) * 1000
            if cached is not None:
                timing.cache_hits = 1
                timing.total_ms = (time.perf_counter() - t_start) * 1000
                return cached, timing
            t_api = time.perf_counter()
            result = await self._translate_raw(text, source_lang, target_lang, timeout)
            timing.api_request_ms = (time.perf_counter() - t_api) * 1000
            _cache_set(text, source_lang, target_lang, result)
            timing.total_ms = (time.perf_counter() - t_start) * 1000
            return result, timing

        cache_hits = 0
        uncached_paragraphs: list[tuple[int, str]] = []
        t_cache = time.perf_counter()
        for i, para in enumerate(paragraphs):
            cached = _cache_get(para, source_lang, target_lang)
            if cached is not None:
                cache_hits += 1
            else:
                uncached_paragraphs.append((i, para))
        timing.cache_lookup_ms = (time.perf_counter() - t_cache) * 1000
        timing.cache_hits = cache_hits

        sem = asyncio.Semaphore(self._get_max_concurrent())
        results: dict[int, str] = {}

        t_api = time.perf_counter()

        async def _translate_one(idx: int, para: str) -> None:
            if self._is_cancelled():
                return
            async with sem:
                if self._is_cancelled():
                    return
                try:
                    results[idx] = await self._translate_raw(para, source_lang, target_lang, timeout)
                    _cache_set(para, source_lang, target_lang, results[idx])
                except Exception as e:
                    logger.error("Paragraph %d translation failed: %s", idx, e)
                    results[idx] = f"[翻译失败: {beautify_translation_error(str(e))}]"

        if uncached_paragraphs:
            tasks = [_translate_one(i, p) for i, p in uncached_paragraphs]
            await asyncio.gather(*tasks)

        timing.api_request_ms = (time.perf_counter() - t_api) * 1000

        t_post = time.perf_counter()
        for i in range(len(paragraphs)):
            if i not in results:
                results[i] = _cache_get(paragraphs[i], source_lang, target_lang)
        merged = "\n\n".join(results[i] for i in range(len(paragraphs)))
        timing.postprocess_ms = (time.perf_counter() - t_post) * 1000

        timing.total_ms = (time.perf_counter() - t_start) * 1000
        logger.info("translate_paragraphs timing: %s", timing.summary())
        return merged, timing

    async def translate_with_formula_protection(
        self,
        text: str,
        formula_service,
        source_lang: str = "en",
        target_lang: str = "zh",
        timeout: float = 60.0,
    ) -> str:
        protected_text = formula_service.protect_text(text)
        protect_ms = formula_service._last_protect_ms if hasattr(formula_service, '_last_protect_ms') else 0.0

        try:
            result = await self._translate_with_formula_prompt(
                protected_text, source_lang, target_lang, timeout
            )
        except BadRequestError as e:
            if _is_token_limit_error(e):
                logger.warning(
                    "Token limit exceeded in formula-protected translate, auto-splitting (%d chars)",
                    len(protected_text)
                )
                paragraphs = split_paragraphs(text)
                sem = asyncio.Semaphore(self._get_max_concurrent())
                results: dict[int, str] = {}

                async def _do_one(idx: int, para: str) -> None:
                    async with sem:
                        try:
                            svc = type(formula_service)()
                            svc.protect_text(para)
                            protected = svc._last_text if hasattr(svc, '_last_text') else para
                            raw = await self._translate_with_formula_prompt(
                                protected, source_lang, target_lang, timeout
                            )
                            results[idx] = svc.restore_text(raw)
                        except Exception as inner_e:
                            logger.error("Protected chunk %d failed: %s", idx, inner_e)
                            results[idx] = f"[翻译失败: {beautify_translation_error(str(inner_e))}]"

                await asyncio.gather(*[_do_one(i, p) for i, p in enumerate(paragraphs)])
                result = " ".join(results[i] for i in range(len(paragraphs)))
            else:
                raise

        return formula_service.restore_text(result)

    async def _translate_with_formula_prompt(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        timeout: float,
    ) -> str:
        if self._is_cancelled():
            return text

        t_start = time.perf_counter()
        effective_model = self._resolve_model()
        merged_prompt = self._build_formula_prompt(text, source_lang, target_lang)

        messages: list[dict] = [{"role": "user", "content": merged_prompt}]

        max_tokens = self._compute_max_tokens(len(text))

        params: dict = {
            "model": effective_model,
            "messages": messages,
            "temperature": 0.0,
            "max_tokens": max_tokens,
            "timeout": timeout,
        }
        stop_tokens = self._get_stop_tokens(effective_model)
        if stop_tokens:
            params["stop"] = stop_tokens

        non_thinking = self._get_non_thinking_params(effective_model)
        if non_thinking:
            params.update(non_thinking)

        is_glm = _is_glm_provider(effective_model)
        max_attempts = GLM_RATE_LIMIT_RETRIES + 1 if is_glm else 1
        response = None
        last_error: Exception | None = None

        for attempt in range(max_attempts):
            if self._is_cancelled():
                return text

            if attempt > 0:
                delay = GLM_RATE_LIMIT_BACKOFF_BASE ** (attempt - 1)
                logger.warning(
                    "GLM rate limit retry %d/%d for translate_with_formula_prompt (%d chars), waiting %.1fs",
                    attempt, GLM_RATE_LIMIT_RETRIES, len(text), delay,
                )
                await asyncio.sleep(delay)
                if self._is_cancelled():
                    return text

            try:
                response = await self._call_llm_cancellable(params)
                if response is None:
                    return text
                break
            except Exception as e:
                last_error = e
                if is_glm and _is_rate_limit_error(e) and attempt < max_attempts - 1:
                    continue
                raise

        if response is None and last_error is not None:
            raise last_error

        raw_result = response.choices[0].message.content
        if raw_result is None:
            raw_result = ""

        if not raw_result.strip():
            reasoning_content = getattr(response.choices[0].message, 'reasoning_content', None)
            if reasoning_content and str(reasoning_content).strip():
                logger.warning(
                    "_translate_with_formula_prompt: content empty but reasoning_content present (%d chars), "
                    "using reasoning_content as fallback.",
                    len(str(reasoning_content)),
                )
                raw_result = str(reasoning_content)

        result = self._validate_and_clean_output(
            raw_result, text, getattr(response, 'usage', None),
            "_translate_with_formula_prompt",
        )

        elapsed = (time.perf_counter() - t_start) * 1000
        logger.debug(
            "_translate_with_formula_prompt: %d chars input -> %d chars output (raw=%d), %.0fms",
            len(text), len(result), len(raw_result), elapsed,
        )
        self._log_usage(
            "_translate_with_formula_prompt",
            getattr(response, 'usage', None),
            response.choices[0].message,
            len(text),
            len(result),
            elapsed,
        )
        return result

    async def translate_paragraphs_with_formula_protection(
        self,
        text: str,
        source_lang: str = "en",
        target_lang: str = "zh",
        timeout: float = 60.0,
    ) -> tuple[str, TranslationTiming]:
        from app.services.formula_protection_service import FormulaProtectionService

        timing = TranslationTiming()
        t_start = time.perf_counter()

        t0 = time.perf_counter()
        paragraphs = split_paragraphs(text)
        timing.preprocess_ms = (time.perf_counter() - t0) * 1000
        timing.paragraph_count = len(paragraphs)

        fsvc = FormulaProtectionService()
        protected_paragraphs = fsvc.protect_paragraphs(paragraphs)

        if len(paragraphs) <= 1:
            t_api = time.perf_counter()
            result = await self._translate_with_formula_prompt(
                protected_paragraphs[0] if protected_paragraphs else text,
                source_lang, target_lang, timeout
            )
            timing.api_request_ms = (time.perf_counter() - t_api) * 1000
            result = fsvc.restore_text(result)
            timing.total_ms = (time.perf_counter() - t_start) * 1000
            return result, timing

        sem = asyncio.Semaphore(self._get_max_concurrent())
        results: dict[int, str] = {}

        t_api = time.perf_counter()

        async def _translate_one(idx: int, para: str) -> None:
            if self._is_cancelled():
                return
            async with sem:
                if self._is_cancelled():
                    return
                try:
                    results[idx] = await self._translate_with_formula_prompt(
                        para, source_lang, target_lang, timeout
                    )
                except Exception as e:
                    logger.error("Paragraph %d formula-protected translation failed: %s", idx, e)
                    results[idx] = f"[翻译失败: {beautify_translation_error(str(e))}]"

        tasks = [_translate_one(i, p) for i, p in enumerate(protected_paragraphs)]
        await asyncio.gather(*tasks)

        timing.api_request_ms = (time.perf_counter() - t_api) * 1000

        t_post = time.perf_counter()
        restored = fsvc.restore_paragraphs([
            results.get(i, f"[段落 {i} 翻译缺失]")
            for i in range(len(paragraphs))
        ])
        merged = "\n\n".join(restored)
        timing.postprocess_ms = (time.perf_counter() - t_post) * 1000

        timing.total_ms = (time.perf_counter() - t_start) * 1000
        logger.info("translate_paragraphs_with_formula_protection timing: %s", timing.summary())
        return merged, timing

    async def translate_stream_paragraphs(
        self,
        text: str,
        source_lang: str = "en",
        target_lang: str = "zh",
    ) -> AsyncGenerator[str, None]:
        if self._is_cancelled():
            return

        timing = TranslationTiming()
        t_start = time.perf_counter()
        timing.input_chars = len(text)

        t0 = time.perf_counter()
        paragraphs = split_paragraphs(text)
        timing.preprocess_ms = (time.perf_counter() - t0) * 1000
        timing.paragraph_count = len(paragraphs)
        n = len(paragraphs)

        if n <= 1:
            async for chunk in self.translate_stream(text, source_lang, target_lang):
                yield chunk
            timing.total_ms = (time.perf_counter() - t_start) * 1000
            logger.info("translate_stream_paragraphs timing: %s", timing.summary())
            return

        t_api = time.perf_counter()
        queue: asyncio.Queue = asyncio.Queue(maxsize=n * 4)
        first_token_recorded = False
        stream_sem = asyncio.Semaphore(self._get_max_concurrent())

        async def _producer(idx: int, para: str) -> None:
            if self._is_cancelled():
                await queue.put((idx, "", True))
                return
            async with stream_sem:
                if self._is_cancelled():
                    await queue.put((idx, "", True))
                    return
                try:
                    async for chunk in self.translate_stream(para, source_lang, target_lang):
                        if self._is_cancelled():
                            await queue.put((idx, "", True))
                            return
                        await queue.put((idx, chunk, False))
                    await queue.put((idx, "", True))
                except Exception as e:
                    logger.error("Paragraph %d stream translation failed: %s", idx, e)
                    error_msg = f"[翻译失败: {beautify_translation_error(str(e))}]"
                    await queue.put((idx, error_msg, True))

        producers = [asyncio.create_task(_producer(i, p)) for i, p in enumerate(paragraphs)]

        next_idx = 0
        finished: set[int] = set()
        buffer: dict[int, list[str]] = {}
        done_count = 0
        first_content_seen = False

        while done_count < n:
            idx, content, is_last = await queue.get()

            if not first_token_recorded and not is_last:
                timing.first_token_ms = (time.perf_counter() - t_start) * 1000
                first_token_recorded = True
            timing.chunk_count += 1

            if is_last:
                done_count += 1
                finished.add(idx)
                if not content:
                    if idx == next_idx:
                        next_idx += 1
                        if next_idx < n:
                            yield "\n\n"
                        while next_idx in finished and next_idx < n:
                            next_idx += 1
                            if next_idx < n:
                                yield "\n\n"
                    continue

            if idx == next_idx:
                first_content_seen = True
                yield content
                if idx in finished:
                    next_idx += 1
                    if next_idx < n:
                        yield "\n\n"
                    while next_idx in finished and next_idx < n:
                        if next_idx in buffer:
                            for buf_chunk in buffer.pop(next_idx):
                                yield buf_chunk
                            first_content_seen = True
                        next_idx += 1
                        if next_idx < n:
                            yield "\n\n"
            elif idx > next_idx:
                if idx not in buffer:
                    buffer[idx] = []
                buffer[idx].append(content)
                if not first_content_seen and buffer:
                    first_content_seen = True
                    yield "\u200b"
                if idx in finished:
                    pass

        timing.api_stream_ms = (time.perf_counter() - t_api) * 1000
        timing.total_ms = (time.perf_counter() - t_start) * 1000
        logger.info("translate_stream_paragraphs timing: %s", timing.summary())

        await asyncio.gather(*producers)