from abc import ABC, abstractmethod
from typing import Optional

from openai import AsyncOpenAI


class BaseTranslator(ABC):
    @abstractmethod
    async def translate(
        self,
        text: str,
        source_lang: str = "en",
        target_lang: str = "zh",
    ) -> str:
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
        )
        logger.info(f"AI response received, content length: {len(response.choices[0].message.content or '')}")
        return response.choices[0].message.content.strip()
