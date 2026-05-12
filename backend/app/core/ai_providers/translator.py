from abc import ABC, abstractmethod
from typing import Optional, AsyncGenerator

from openai import AsyncOpenAI


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
            f"Translate the following text from {source_lang} to {target_lang}. "
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
