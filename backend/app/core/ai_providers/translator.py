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


class OpenAITranslator(BaseTranslator):
    def __init__(self, client: AsyncOpenAI, model: str):
        self.client = client
        self.model = model

    LANG_DISPLAY: dict[str, str] = {
        "en": "英文", "zh": "中文", "zh-CN": "简体中文", "zh-TW": "繁体中文",
        "ja": "日文", "ko": "韩文", "fr": "法文", "de": "德文",
        "es": "西班牙文", "ru": "俄文", "ar": "阿拉伯文", "pt": "葡萄牙文",
    }

    @staticmethod
    def _build_prompt(text: str, source_lang: str, target_lang: str) -> str:
        src = OpenAITranslator.LANG_DISPLAY.get(source_lang, source_lang)
        tgt = OpenAITranslator.LANG_DISPLAY.get(target_lang, target_lang)
        return f"将以下{src}翻译为{tgt}，只输出译文：\n{text}"

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

        try:
            result = await self._translate_raw(text, source_lang, target_lang, timeout)
        except BadRequestError as e:
            if _is_token_limit_error(e):
                logger.warning("Token limit exceeded, auto-splitting text (%d chars)", len(text))
                chunks = _chunk_text(text, PARAGRAPH_MAX_CHARS // 2)
                sem = asyncio.Semaphore(MAX_CONCURRENT_PARAGRAPHS)
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
        t_start = time.perf_counter()
        prompt = self._build_prompt(text, source_lang, target_lang)
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            timeout=timeout,
        )
        result = response.choices[0].message.content.strip()
        elapsed = (time.perf_counter() - t_start) * 1000
        logger.debug(
            "_translate_raw: %d chars, %d chars output, %.0fms",
            len(text), len(result), elapsed
        )
        return result

    async def translate_stream(
        self,
        text: str,
        source_lang: str = "en",
        target_lang: str = "zh",
    ) -> AsyncGenerator[str, None]:
        t_start = time.perf_counter()
        first_token = True
        first_token_ms = 0.0
        chunk_count = 0
        prompt = self._build_prompt(text, source_lang, target_lang)
        last_error = ""

        for attempt in range(STREAM_RETRIES + 1):
            try:
                stream = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    stream=True,
                    timeout=STREAM_TIMEOUT,
                )
                async for chunk in stream:
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
                    "translate_stream: %d chars, %d chunks, first_token=%.0fms, total=%.0fms",
                    len(text), chunk_count, first_token_ms, elapsed
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

        sem = asyncio.Semaphore(MAX_CONCURRENT_PARAGRAPHS)
        results: dict[int, str] = {}

        t_api = time.perf_counter()

        async def _translate_one(idx: int, para: str) -> None:
            async with sem:
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

    async def translate_stream_paragraphs(
        self,
        text: str,
        source_lang: str = "en",
        target_lang: str = "zh",
    ) -> AsyncGenerator[str, None]:
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

        async def _producer(idx: int, para: str) -> None:
            try:
                async for chunk in self.translate_stream(para, source_lang, target_lang):
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