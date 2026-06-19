import json
import logging
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

ANALYSIS_PROMPT = """You are an academic literature analyst. Analyze the following paper text and return a JSON object with exactly this structure:

{
  "summary": {
    "background": "Research background and motivation (1-2 sentences in Chinese)",
    "method": "Core methodology used (1-2 sentences in Chinese)",
    "result": "Key findings and results (1-2 sentences in Chinese)",
    "conclusion": "Main conclusions and implications (1-2 sentences in Chinese)"
  },
  "innovations": [
    "Innovation point 1 (in Chinese, concise)",
    "Innovation point 2 (in Chinese, concise)",
    ...
  ],
  "methods": "Detailed reproducible method steps (in Chinese, numbered steps)"
}

Rules:
- summary fields: each 1-2 concise Chinese sentences
- innovations: at most 5 items, each one sentence, focus on novel contributions
- methods: numbered step-by-step reproducible procedure in Chinese
- Return ONLY valid JSON, no markdown code blocks, no extra text

Paper text:
{text}"""


class OpenAIAnalyzer:
    def __init__(self, client: AsyncOpenAI, model: str):
        self.client = client
        self.model = model

    async def analyze(self, text: str) -> dict:
        prompt = ANALYSIS_PROMPT.replace("{text}", text[:15000])

        logger.info(f"Calling AI analysis with model: {self.model}, text length: {len(text)}")
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            timeout=120.0,
        )

        content = response.choices[0].message.content.strip()
        logger.info(f"AI analysis response received, length: {len(content)}")

        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        try:
            result = json.loads(content)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse AI response as JSON, raw: {content[:500]}")
            result = {
                "summary": {"background": "", "method": "", "result": "", "conclusion": ""},
                "innovations": [],
                "methods": content,
            }

        if "summary" not in result:
            result["summary"] = {"background": "", "method": "", "result": "", "conclusion": ""}
        if "innovations" not in result:
            result["innovations"] = []
        if "methods" not in result:
            result["methods"] = ""

        return result