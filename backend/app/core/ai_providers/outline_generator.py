import json
import logging
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

OUTLINE_PROMPT = """You are an academic presentation designer. Based on the following paper, generate a presentation outline in JSON format for a group meeting report.

Return ONLY valid JSON with this exact structure:
{
  "slides": [
    {
      "title": "Slide title in Chinese",
      "bullets": ["Bullet point 1 in Chinese", "Bullet point 2 in Chinese", ...],
      "notes": "Optional speaker notes in Chinese"
    }
  ]
}

Requirements:
- Slide 1: Title slide (paper title, authors, journal/year)
- Slide 2: Research Background & Motivation
- Slide 3: Core Problem / Research Question
- Slide 4: Methodology Overview
- Slide 5: Key Experiments / Evaluation
- Slide 6: Main Results & Findings
- Slide 7: Innovations & Contributions
- Slide 8: Limitations & Future Work
- Slide 9: Summary & Conclusions
- Each slide: 3-5 bullet points, concise and scannable
- All content in Chinese
- Return ONLY valid JSON, no markdown code blocks, no extra text

Paper content:
{text}"""


class OutlineGenerator:
    def __init__(self, client: AsyncOpenAI, model: str):
        self.client = client
        self.model = model

    async def generate(self, text: str, title: str = "", authors: str = "", year: str = "", journal: str = "") -> dict:
        context = f"Title: {title}\nAuthors: {authors}\nYear: {year}\nJournal: {journal}\n\nContent:\n{text[:12000]}"
        prompt = OUTLINE_PROMPT.replace("{text}", context)

        logger.info(f"Calling AI outline generation with model: {self.model}")
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            timeout=120.0,
        )

        content = response.choices[0].message.content.strip()
        logger.info(f"AI outline response received, length: {len(content)}")

        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        try:
            result = json.loads(content)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse outline JSON, raw: {content[:500]}")
            result = {"slides": []}

        if "slides" not in result:
            result["slides"] = []

        return result