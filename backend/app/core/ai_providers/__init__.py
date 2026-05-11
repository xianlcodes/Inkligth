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
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()
