from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from openai import AsyncOpenAI
import json
import logging

logger = logging.getLogger(__name__)

# 提示词模板（只留一个 {text} 占位符，将通过 replace 替换）
ANALYSIS_PROMPT_TEMPLATE = """\
You are a helpful academic assistant. Please analyze the following paper text and provide a structured response in JSON format. The JSON should contain the following fields:
- summary: an object with fields "background", "method", "result", "conclusion". Each field should be a concise summary (1-2 sentences).
- innovations: a list of up to 5 innovative points of the paper.
- methods: a brief description of the reproducible method steps.

Text:
{text}

Return ONLY the JSON object, no other text."""


# ==================== Pydantic 模型 ====================

class SummarySchema(BaseModel):
    background: str = ""
    method: str = ""
    result: str = ""
    conclusion: str = ""


class AnalysisResponse(BaseModel):
    id: str
    user_id: str
    literature_id: str
    summary: Optional[dict] = None
    innovations: Optional[List[str]] = None
    methods: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AnalyzeResponse(BaseModel):
    task_id: str
    message: str


# ==================== AI 分析器 ====================

class OpenAIAnalyzer:
    def __init__(self, client: AsyncOpenAI, model: str):
        self.client = client
        self.model = model

    async def analyze(self, text: str) -> dict:
        prompt = ANALYSIS_PROMPT_TEMPLATE.replace("{text}", text[:15000])
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a precise academic analyst."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content
            result = json.loads(content)
            return result
        except Exception as e:
            logger.error(f"Analysis failed: {e}", exc_info=True)
            raise