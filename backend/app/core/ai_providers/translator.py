from abc import ABC, abstractmethod
from typing import Optional, AsyncGenerator
import re

from openai import AsyncOpenAI


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

    async def translate(
        self,
        text: str,
        source_lang: str = "en",
        target_lang: str = "zh",
        timeout: float = 60.0,
    ) -> str:
        prompt = (
            f"Translate the following academic paper text from {source_lang} to {target_lang}. "
            "Only return the translated text, no explanations:\n\n"
            f"{text}"
        )
        from app.core.ai_client import logger
        logger.info(f"Calling AI with model: {self.model}, text length: {len(text)}")
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            timeout=timeout,
        )
        logger.info(f"AI response received, content length: {len(response.choices[0].message.content or '')}")
        return response.choices[0].message.content.strip()

    async def translate_stream(
        self,
        text: str,
        source_lang: str = "en",
        target_lang: str = "zh",
    ) -> AsyncGenerator[str, None]:
        prompt = (
            f"Translate the following text from {source_lang} to {target_lang}. "
            "Only return the translated text, no explanations:\n\n"
            f"{text}"
        )
        from app.core.ai_client import logger
        logger.info(f"Streaming translate with model: {self.model}, text length: {len(text)}")
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            stream=True,
        )
        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content
