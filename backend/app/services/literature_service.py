import os
import re
import uuid
import shutil
import logging
from typing import Optional
from xml.etree import ElementTree as ET

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.literature import Literature
from app.schemas.literature import LiteratureCreate, LiteratureUpdate

logger = logging.getLogger(__name__)

UPLOAD_DIR = "uploads"

# Patterns for identifiers
DOI_PATTERN = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.IGNORECASE)
ARXIV_URL_PATTERN = re.compile(r"arxiv\.org/abs/(\d{4,5}\.\d{4,5})", re.IGNORECASE)
ARXIV_ID_PATTERN = re.compile(r"\barXiv[\s:]*(\d{4,5}\.\d{4,5})", re.IGNORECASE)
PMID_PATTERN = re.compile(r"PMID[\s:]*(\d+)", re.IGNORECASE)
PMCID_PATTERN = re.compile(r"PMCID[\s:]*(\d+)", re.IGNORECASE)

# Text parsing helpers
COMMON_START_WORDS = re.compile(r"^(a|an|the|this|that|these|those|we|in|on|at|for|with|by|from|to|of|and|or|but)\s", re.IGNORECASE)
ABSTRACT_END_PATTERN = re.compile(r"\n\s*(INTRODUCTION|KEYWORDS|1\.\s|CHAPTER|FIGURE|TABLE|REFERENCES|ACKNOWLEDGMENTS)\s*\n", re.IGNORECASE)
EMAIL_PATTERN = re.compile(r"[\w.-]+@[\w.-]+\.[A-Za-z]{2,}")
DIGIT_MARKER_PATTERN = re.compile(r"^\d+\s*[.,]?\s*")
PAREN_UNIT_PATTERN = re.compile(r"\([^)]*(university|institute|college|school|department|lab|center|centre)[^)]*\)", re.IGNORECASE)


class LiteratureService:
    @staticmethod
    def ensure_upload_dir():
        os.makedirs(UPLOAD_DIR, exist_ok=True)

    @staticmethod
    def save_upload_file(file) -> str:
        LiteratureService.ensure_upload_dir()
        ext = os.path.splitext(file.filename)[1] or ".pdf"
        filename = f"{uuid.uuid4()}{ext}"
        file_path = os.path.join(UPLOAD_DIR, filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return file_path

    @staticmethod
    def extract_text_from_pdf(file_path: str) -> str:
        try:
            import fitz
            text = ""
            with fitz.open(file_path) as doc:
                for page in doc:
                    text += page.get_text()
            return text.replace("\x00", "")
        except Exception as e:
            logger.error(f"PDF text extraction failed: {e}")
            return ""

    # ------------------------------------------------------------------
    # Layer 1: Identifier extraction
    # ------------------------------------------------------------------
    @staticmethod
    def extract_identifiers(text: str) -> dict:
        """Extract DOI, arXiv, PMID, PMCID from text."""
        result = {"doi": None, "arxiv": None, "pmid": None, "pmcid": None}

        doi_match = DOI_PATTERN.search(text)
        if doi_match:
            result["doi"] = doi_match.group(0)

        arxiv_match = ARXIV_URL_PATTERN.search(text)
        if not arxiv_match:
            arxiv_match = ARXIV_ID_PATTERN.search(text)
        if arxiv_match:
            result["arxiv"] = arxiv_match.group(1)

        pmid_match = PMID_PATTERN.search(text)
        if pmid_match:
            result["pmid"] = pmid_match.group(1)

        pmcid_match = PMCID_PATTERN.search(text)
        if pmcid_match:
            result["pmcid"] = pmcid_match.group(1)

        return result

    @staticmethod
    def extract_doi_from_text(text: str) -> Optional[str]:
        """Legacy wrapper."""
        ids = LiteratureService.extract_identifiers(text)
        return ids.get("doi")

    # ------------------------------------------------------------------
    # Layer 1: API metadata fetchers
    # ------------------------------------------------------------------
    @staticmethod
    async def fetch_crossref_metadata(doi: str) -> dict:
        url = f"https://api.crossref.org/works/{doi}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers={"User-Agent": "InkLight/0.1.0 (mailto:admin@inklight.local)"})
                if resp.status_code == 200:
                    data = resp.json().get("message", {})
                    authors_list = data.get("author", [])
                    authors = ", ".join(
                        [f"{a.get('given', '')} {a.get('family', '')}".strip() for a in authors_list]
                    )
                    return {
                        "title": data.get("title", [None])[0],
                        "authors": authors if authors else None,
                        "abstract": data.get("abstract") or None,
                        "year": str(data.get("published-print", {}).get("date-parts", [[None]])[0][0]) if data.get("published-print") else str(data.get("published-online", {}).get("date-parts", [[None]])[0][0]) if data.get("published-online") else None,
                        "journal": data.get("container-title", [None])[0] if data.get("container-title") else None,
                        "doi": doi,
                    }
        except Exception as e:
            logger.error(f"Crossref fetch failed for DOI {doi}: {e}")
        return {}

    @staticmethod
    async def fetch_arxiv_metadata(arxiv_id: str) -> dict:
        url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    root = ET.fromstring(resp.text)
                    ns = {"atom": "http://www.w3.org/2005/Atom"}
                    entry = root.find("atom:entry", ns)
                    if entry is not None:
                        title_elem = entry.find("atom:title", ns)
                        title = title_elem.text.strip() if title_elem is not None and title_elem.text else None

                        authors_elems = entry.findall("atom:author/atom:name", ns)
                        authors = ", ".join([a.text for a in authors_elems if a.text]) if authors_elems else None

                        summary_elem = entry.find("atom:summary", ns)
                        abstract = summary_elem.text.strip() if summary_elem is not None and summary_elem.text else None

                        published_elem = entry.find("atom:published", ns)
                        year = None
                        if published_elem is not None and published_elem.text:
                            year = published_elem.text[:4]

                        return {
                            "title": title,
                            "authors": authors,
                            "abstract": abstract,
                            "year": year,
                            "journal": "arXiv",
                            "doi": None,
                        }
        except Exception as e:
            logger.error(f"arXiv fetch failed for {arxiv_id}: {e}")
        return {}

    @staticmethod
    async def fetch_pubmed_metadata(pmid: str) -> dict:
        """Fetch PubMed metadata via NCBI E-utilities."""
        summary_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
        params = {"db": "pubmed", "id": pmid, "retmode": "json"}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(summary_url, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    result = data.get("result", {}).get(pmid, {})
                    authors_list = result.get("authors", [])
                    authors = ", ".join([a.get("name", "") for a in authors_list]) if authors_list else None
                    return {
                        "title": result.get("title"),
                        "authors": authors,
                        "abstract": None,  # esummary does not return abstract; could call efetch if needed
                        "year": str(result.get("pubdate", ""))[:4] if result.get("pubdate") else None,
                        "journal": result.get("fulljournalname") or result.get("source"),
                        "doi": None,
                    }
        except Exception as e:
            logger.error(f"PubMed fetch failed for PMID {pmid}: {e}")
        return {}

    # ------------------------------------------------------------------
    # Layer 2: Title extraction from text
    # ------------------------------------------------------------------
    @staticmethod
    def extract_title_from_text(text: str) -> Optional[str]:
        """Extract the most probable title from the first 50 lines of text.
        
        Handles multi-line titles by merging consecutive title-like lines.
        """
        raw_lines = text.splitlines()[:50]
        lines = [line.strip() for line in raw_lines if line.strip()]
        if not lines:
            return None

        # First pass: score each line
        candidates = []
        for i, line in enumerate(lines):
            score = 0
            word_count = len(line.split())

            # Prefer lines with 5-30 words
            if 5 <= word_count <= 30:
                score += 3
            elif 3 <= word_count < 5:
                score += 1

            # Penalize common sentence starters
            if COMMON_START_WORDS.match(line):
                score -= 3

            # Markdown header bonus
            if line.startswith("# "):
                score += 5
                line = line.lstrip("# ").strip()

            # Bonus if next line looks like authors/affiliations/abstract
            if i + 1 < len(lines):
                next_line = lines[i + 1].lower()
                if any(k in next_line for k in ["abstract", "author", "university", "institute", "department", "lab", "@"]):
                    score += 2

            # Penalize lines that are too short or too long
            if len(line) < 10:
                score -= 2
            if len(line) > 200:
                score -= 1

            # Penalize lines with lots of numbers / symbols (unlikely to be titles)
            alpha_ratio = sum(c.isalpha() or c.isspace() for c in line) / max(len(line), 1)
            if alpha_ratio < 0.7:
                score -= 2

            # Slight penalty for the very first line (often header / noise)
            if i == 0:
                score -= 1

            # Penalize lines that are single sentences ending with period
            if line.endswith(".") and word_count > 3:
                score -= 2

            # Strong penalty for lines containing "PDF" (likely header/footer)
            if "pdf" in line.lower():
                score -= 3

            # Bonus if previous line is short (title often follows a blank/separator line)
            if i > 0 and len(lines[i - 1]) < 20:
                score += 1

            # Penalize lines with many uppercase words (likely headers / author names in caps)
            words = line.split()
            if words:
                upper_ratio = sum(1 for w in words if w.isupper() and len(w) > 1) / len(words)
                if upper_ratio > 0.5:
                    score -= 2

            # Strong bonus if the next line looks like an author list (comma-separated short words)
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                if "," in next_line:
                    avg_word_len = sum(len(w.strip()) for w in next_line.split(",")) / max(len(next_line.split(",")), 1)
                    if avg_word_len < 10:
                        score += 3

            # Penalize lines that look like author lists themselves (many commas, short words)
            if "," in line:
                avg_word_len = sum(len(w.strip()) for w in line.split(",")) / max(len(line.split(",")), 1)
                if avg_word_len < 10:
                    score -= 2

            # Bonus if line has no comma but next line does (title often followed by author list)
            if "," not in line and i + 1 < len(lines) and "," in lines[i + 1]:
                score += 2

            # Penalize lines that match DOI / arXiv / URL patterns (metadata, not title)
            if DOI_PATTERN.search(line) or ARXIV_URL_PATTERN.search(line) or ARXIV_ID_PATTERN.search(line) or line.startswith("http"):
                score -= 3

            # NEW: Strong penalty for lines that contain author name patterns (Name + superscript digit)
            if re.search(r"[A-Za-z]+\s+[A-Za-z]+[\d∗*]", line):
                score -= 5

            # NEW: Strong penalty for lines starting with digits (affiliation markers like "1Faculty", "2College")
            if re.match(r"^\d+[A-Za-z]", line):
                score -= 5

            # Penalize lines that look like email addresses
            if "@" in line and "." in line.split("@")[-1]:
                score -= 20

            # Strong penalty for lines containing "Abstract" or "Summary" keywords
            if re.search(r"\b(Abstract|Summary)\b", line, re.IGNORECASE):
                score -= 30

            # Strong penalty for lines that are clearly abstract content (long sentences with periods)
            if word_count > 15 and line.count(".") >= 2:
                score -= 15

            # Strong penalty for lines starting with common abstract indicators
            if re.match(r"^(Abstract|Summary|Introduction|Background|Keywords)\s*[:.]?\s*", line, re.IGNORECASE):
                score -= 25

            candidates.append((score, line, i))

        if not candidates:
            fallback = lines[0][:100]
            logger.warning(f"Title extraction fallback used: {fallback}")
            return fallback if fallback else None

        # Sort by score descending
        candidates.sort(key=lambda x: x[0], reverse=True)
        best_score, best_line, best_idx = candidates[0]

        # Merge with adjacent title-like lines (multi-line title support)
        title_parts = [best_line]
        
        # Look backward: if previous line has similar score and no comma, merge
        for idx in range(best_idx - 1, -1, -1):
            prev_line = lines[idx]
            # Stop if line looks like an author list or has too many commas
            if "," in prev_line:
                avg_word_len = sum(len(w.strip()) for w in prev_line.split(",")) / max(len(prev_line.split(",")), 1)
                if avg_word_len < 10:
                    break
            # Stop if line is a conference header (contains "conference", "proceedings", etc.)
            if any(k in prev_line.lower() for k in ["conference", "proceedings", "journal of", "transactions on", "symposium"]):
                break
            # NEW: Stop if line contains author name patterns (Name + superscript digit)
            if re.search(r"[A-Za-z]+\s+[A-Za-z]+[\d∗*]", prev_line):
                break
            # NEW: Stop if line starts with digit + text (affiliation marker)
            if re.match(r"^\d+[A-Za-z]", prev_line):
                break
            # Only merge if it's reasonably title-like (no period at end, decent length)
            if len(prev_line) > 5 and not prev_line.endswith("."):
                title_parts.insert(0, prev_line)
            else:
                break
        
        # Look forward: if next lines have no comma and decent length, merge
        for idx in range(best_idx + 1, len(lines)):
            next_line = lines[idx]
            # Stop if line looks like an author list
            if "," in next_line:
                avg_word_len = sum(len(w.strip()) for w in next_line.split(",")) / max(len(next_line.split(",")), 1)
                if avg_word_len < 10:
                    break
            # Stop if line is too short or ends with period
            if len(next_line) < 5 or next_line.endswith("."):
                break
            # Stop if line contains author keywords
            if any(k in next_line.lower() for k in ["university", "institute", "college", "department", "lab", "@"]):
                break
            # NEW: Stop if line contains author name patterns (Name1, Name2 with superscript digits)
            if re.search(r"[A-Za-z]+\s+[A-Za-z]+[\d∗*]", next_line):
                break
            # NEW: Stop if line starts with digit + text (affiliation marker)
            if re.match(r"^\d+[A-Za-z]", next_line):
                break
            title_parts.append(next_line)

        title = " ".join(title_parts)
        
        # Final cleanup: if title still contains author-like patterns, truncate
        author_match = re.search(r"[A-Za-z]+\s+[A-Za-z]+[\d∗*]", title)
        if author_match:
            title = title[:author_match.start()].strip()
        
        # Final cleanup: if title still contains affiliation markers, truncate
        affiliation_match = re.search(r"\d+[A-Za-z]", title)
        if affiliation_match:
            title = title[:affiliation_match.start()].strip()
        
        return title[:300] if title else None

    # ------------------------------------------------------------------
    # Layer 3: Authors & Abstract extraction from text
    # ------------------------------------------------------------------
    @staticmethod
    def extract_authors_from_text(text: str, title: Optional[str] = None) -> Optional[str]:
        """Heuristic extraction of authors from text."""
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            return None

        start_idx = 0
        if title:
            for i, line in enumerate(lines):
                if title.lower() in line.lower() or line.lower() in title.lower():
                    start_idx = i + 1
                    break

        author_lines = []
        for line in lines[start_idx:start_idx + 10]:
            lower = line.lower()
            # Stop at abstract or section headers
            if any(k in lower for k in ["abstract", "summary", "introduction", "background", "keywords"]):
                break
            # Skip lines that are clearly not authors
            if line.startswith("http") or line.startswith("www"):
                continue
            # Skip lines that look like the title itself
            if title and (line.lower() == title.lower() or title.lower() in line.lower()):
                continue
            # Skip affiliation lines (start with digit + text, or contain university/institute)
            if re.match(r"^\d+[A-Za-z]", line):
                continue
            if any(k in lower for k in ["university", "institute", "college", "school", "department", "laboratory", "lab", "center", "centre"]):
                continue
            # Skip email lines
            if "@" in line:
                continue
            # Skip lines that are too long (likely title or abstract content)
            if len(line) > 200:
                continue
            # Clean line
            cleaned = EMAIL_PATTERN.sub("", line)
            cleaned = PAREN_UNIT_PATTERN.sub("", cleaned)
            cleaned = DIGIT_MARKER_PATTERN.sub("", cleaned)
            cleaned = cleaned.strip(" ,;*†")
            if cleaned and len(cleaned) > 3:
                author_lines.append(cleaned)

        if author_lines:
            return ", ".join(author_lines)[:300]
        return None

    @staticmethod
    def extract_abstract_from_text(text: str) -> Optional[str]:
        """Heuristic extraction of abstract from text."""
        # Find abstract section
        match = re.search(r"\b(Abstract|Summary)\b[\s:]*\n?(.*?)(?=\n\s*(INTRODUCTION|KEYWORDS|1\.\s|CHAPTER|FIGURE|TABLE|REFERENCES|ACKNOWLEDGMENTS)\s*\n|$)", text, re.IGNORECASE | re.DOTALL)
        if match:
            abstract = match.group(2).strip()
            # Truncate to ~200 words if too long
            words = abstract.split()
            if len(words) > 250:
                abstract = " ".join(words[:250]) + "..."
            return abstract[:2000] if abstract else None
        return None

    # ------------------------------------------------------------------
    # AI-based metadata extraction
    # ------------------------------------------------------------------
    @staticmethod
    async def extract_metadata_by_ai(text: str, ai_client, model: str) -> dict:
        """Use AI to extract metadata from raw text."""
        # Truncate text to avoid token limits (keep first 8000 chars which usually contains title/authors/abstract)
        truncated_text = text[:8000] if len(text) > 8000 else text

        prompt = (
            "You are an academic paper metadata extractor. Extract the following fields from the given paper text:\n"
            "- title: The paper title\n"
            "- authors: Comma-separated list of author names\n"
            "- abstract: The abstract text\n"
            "- year: Publication year (4 digits)\n"
            "- journal: Journal or conference name\n"
            "- doi: DOI if present\n\n"
            "Return ONLY a valid JSON object with these keys. Use null for missing fields.\n\n"
            f"Paper text:\n{truncated_text}"
        )

        try:
            response = await ai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a precise metadata extractor. Return only valid JSON."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=1000,
            )
            content = response.choices[0].message.content.strip()
            # Try to extract JSON from response
            import json
            # Handle markdown code blocks
            if "```" in content:
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()
            result = json.loads(content)
            return {
                "title": result.get("title"),
                "authors": result.get("authors"),
                "abstract": result.get("abstract"),
                "year": str(result.get("year", ""))[:4] if result.get("year") else None,
                "journal": result.get("journal"),
                "doi": result.get("doi"),
            }
        except Exception as e:
            logger.error(f"AI metadata extraction failed: {e}")
            return {}

    # ------------------------------------------------------------------
    # Combined metadata extraction (Layer 1 -> 2 -> 3)
    # ------------------------------------------------------------------
    @staticmethod
    async def extract_metadata(text: str, ai_client=None, model: str = None) -> dict:
        """Extract metadata using AI first (if available), then identifiers, then fallback to text parsing."""
        metadata = {"title": None, "authors": None, "abstract": None, "year": None, "journal": None, "doi": None}

        # Layer 0: AI extraction (if available)
        if ai_client and model:
            logger.info("Attempting AI-based metadata extraction")
            ai_metadata = await LiteratureService.extract_metadata_by_ai(text, ai_client, model)
            if ai_metadata.get("title"):
                logger.info("AI extraction successful")
                # Merge AI results, but keep identifier-based DOI if found
                ids = LiteratureService.extract_identifiers(text)
                if ids["doi"]:
                    ai_metadata["doi"] = ids["doi"]
                return ai_metadata
            else:
                logger.warning("AI extraction returned no title, falling back to heuristic methods")

        # Layer 1: identifiers
        ids = LiteratureService.extract_identifiers(text)
        logger.info(f"Extracted identifiers: {ids}")

        if ids["doi"]:
            metadata = await LiteratureService.fetch_crossref_metadata(ids["doi"])
            metadata["doi"] = ids["doi"]
        elif ids["arxiv"]:
            metadata = await LiteratureService.fetch_arxiv_metadata(ids["arxiv"])
        elif ids["pmid"]:
            metadata = await LiteratureService.fetch_pubmed_metadata(ids["pmid"])

        # Layer 2: ensure title
        if not metadata.get("title"):
            title = LiteratureService.extract_title_from_text(text)
            if title:
                metadata["title"] = title
            else:
                # Absolute fallback
                first_line = text.strip().splitlines()[0][:100] if text.strip() else None
                metadata["title"] = first_line
                logger.warning(f"Absolute title fallback used: {first_line}")

        # Layer 3: fill missing authors / abstract from text
        if not metadata.get("authors"):
            metadata["authors"] = LiteratureService.extract_authors_from_text(text, metadata.get("title"))
        if not metadata.get("abstract"):
            metadata["abstract"] = LiteratureService.extract_abstract_from_text(text)

        return metadata

    # ------------------------------------------------------------------
    # Database operations
    # ------------------------------------------------------------------
    @staticmethod
    async def get_literature_by_doi_and_user(db: AsyncSession, doi: str, user_id: str) -> Optional[Literature]:
        result = await db.execute(select(Literature).where(Literature.doi == doi, Literature.user_id == user_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_literature_by_id(db: AsyncSession, literature_id: str, user_id: str) -> Optional[Literature]:
        result = await db.execute(select(Literature).where(Literature.id == literature_id, Literature.user_id == user_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def create_literature(db: AsyncSession, user_id: str, file, literature_in: LiteratureCreate) -> Literature:
        db_literature = Literature(
            user_id=user_id,
            title=literature_in.title,
            authors=literature_in.authors,
            abstract=literature_in.abstract,
            year=literature_in.year,
            journal=literature_in.journal,
            doi=literature_in.doi,
            file_path=literature_in.file_path,
            raw_text=literature_in.raw_text,
            status=literature_in.status or "unread",
        )
        db.add(db_literature)
        await db.commit()
        await db.refresh(db_literature)
        return db_literature

    @staticmethod
    async def update_literature(db: AsyncSession, db_literature: Literature, literature_in: LiteratureUpdate) -> Literature:
        if literature_in.status is not None:
            db_literature.status = literature_in.status
        await db.commit()
        await db.refresh(db_literature)
        return db_literature

    @staticmethod
    async def get_literatures_by_user(
        db: AsyncSession,
        user_id: str,
        skip: int = 0,
        limit: int = 20,
        title: Optional[str] = None,
        status: Optional[str] = None,
        sort_by_year: Optional[str] = None,
    ):
        query = select(Literature).where(Literature.user_id == user_id)
        count_query = select(func.count(Literature.id)).where(Literature.user_id == user_id)

        if title:
            query = query.where(Literature.title.ilike(f"%{title}%"))
            count_query = count_query.where(Literature.title.ilike(f"%{title}%"))

        if status:
            query = query.where(Literature.status == status)
            count_query = count_query.where(Literature.status == status)

        if sort_by_year == "asc":
            query = query.order_by(Literature.year.asc())
        elif sort_by_year == "desc":
            query = query.order_by(Literature.year.desc())
        else:
            query = query.order_by(Literature.created_at.desc())

        query = query.offset(skip).limit(limit)

        result = await db.execute(query)
        count_result = await db.execute(count_query)
        items = result.scalars().all()
        total = count_result.scalar()
        return total, items
