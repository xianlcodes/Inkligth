import asyncio
import os
import re
import time
import uuid
import shutil
import logging
from typing import Optional
from xml.etree import ElementTree as ET

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete

from app.models.literature import Literature
from app.models.ai_analysis import AIAnalysis
from app.models.note import Note
from app.models.literature_chunk import LiteratureChunk
from app.models.reading_record import ReadingRecord
from app.models.presentation import Presentation
from app.models.tag import literature_tags
from app.schemas.literature import LiteratureCreate, LiteratureUpdate

logger = logging.getLogger(__name__)

UPLOAD_DIR = "/app/uploads"

# Metadata cache: {key: (timestamp, data)}, TTL = 24 hours
_metadata_cache: dict[str, tuple[float, dict]] = {}
_metadata_cache_ttl = 86400

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
AUTHOR_NAME_PATTERN = re.compile(r"[A-Z][a-z]+\s+(?:[A-Z]\.\s+)?[A-Z][a-z]+")
SUPERSCRIPT_PATTERN = re.compile(r"[A-Za-z]+\s+[A-Za-z]+[\d∗*†‡§¶]")
AFFILIATION_MARKER_PATTERN = re.compile(r"^\d+\s*[A-Z]")
FUNCTION_WORDS = frozenset([
    "a", "an", "the", "this", "that", "these", "those",
    "we", "in", "on", "at", "for", "with", "by", "from", "to", "of",
    "and", "or", "but", "not", "is", "are", "was", "were", "be", "been",
    "it", "its", "has", "have", "had", "can", "may", "will", "would",
    "based", "using", "via", "new", "towards", "toward", "between",
    "through", "during", "within", "without", "into", "over", "under",
    "A", "An", "The",
])
AUTHOR_INDICATOR_WORDS = frozenset([
    "university", "institute", "college", "school", "department",
    "laboratory", "lab", "center", "centre", "research", "technology",
    "science", "engineering", "academy", "china", "usa", "france",
    "germany", "japan", "uk", "canada", "australia", "inc", "ltd",
    "corporation", "corp", "google", "microsoft", "facebook", "amazon",
    "deepmind", "openai", "meta", "apple", "ibm",
])


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
                    text += page.get_text("text", sort=True)
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
        cache_key = f"crossref:{doi}"
        cached = LiteratureService._cache_get(cache_key)
        if cached:
            logger.info(f"Crossref cache hit for DOI: {doi}")
            return cached

        url = f"https://api.crossref.org/works/{doi}"
        return await LiteratureService._fetch_with_retry(
            url=url,
            cache_key=cache_key,
            source="Crossref",
            params={"mailto": "inklight@example.com"},
            headers={"User-Agent": "InkLight/0.1.0 (mailto:inklight@example.com)"},
            parser=lambda data: LiteratureService._parse_crossref_response(data, doi),
        )

    @staticmethod
    def _parse_crossref_response(data: dict, doi: str) -> dict:
        msg = data.get("message", {})
        authors_list = msg.get("author", [])
        authors = ", ".join(
            [f"{a.get('given', '')} {a.get('family', '')}".strip() for a in authors_list]
        )
        published_print = msg.get("published-print", {})
        published_online = msg.get("published-online", {})
        year = None
        if published_print:
            parts = published_print.get("date-parts", [[None]])[0]
            year = str(parts[0]) if parts and parts[0] else None
        if not year and published_online:
            parts = published_online.get("date-parts", [[None]])[0]
            year = str(parts[0]) if parts and parts[0] else None

        return {
            "title": (msg.get("title") or [None])[0],
            "authors": authors if authors else None,
            "abstract": msg.get("abstract") or None,
            "year": year,
            "journal": (msg.get("container-title") or [None])[0],
            "doi": doi,
        }

    @staticmethod
    async def fetch_arxiv_metadata(arxiv_id: str) -> dict:
        cache_key = f"arxiv:{arxiv_id}"
        cached = LiteratureService._cache_get(cache_key)
        if cached:
            logger.info(f"arXiv cache hit for ID: {arxiv_id}")
            return cached

        url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
        return await LiteratureService._fetch_with_retry(
            url=url,
            cache_key=cache_key,
            source="arXiv",
            parser=lambda data: LiteratureService._parse_arxiv_response(data, arxiv_id),
            is_xml=True,
        )

    @staticmethod
    def _parse_arxiv_response(text: str, arxiv_id: str) -> dict:
        root = ET.fromstring(text)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        entry = root.find("atom:entry", ns)
        if entry is None:
            return {}

        title_elem = entry.find("atom:title", ns)
        title = title_elem.text.strip() if title_elem is not None and title_elem.text else None

        authors_elems = entry.findall("atom:author/atom:name", ns)
        authors = ", ".join([a.text for a in authors_elems if a.text]) if authors_elems else None

        summary_elem = entry.find("atom:summary", ns)
        abstract = summary_elem.text.strip() if summary_elem is not None and summary_elem.text else None

        published_elem = entry.find("atom:published", ns)
        year = published_elem.text[:4] if published_elem is not None and published_elem.text else None

        return {
            "title": title,
            "authors": authors,
            "abstract": abstract,
            "year": year,
            "journal": "arXiv",
            "doi": None,
        }

    @staticmethod
    async def _fetch_with_retry(
        url: str,
        cache_key: str,
        source: str,
        parser,
        params: dict = None,
        headers: dict = None,
        is_xml: bool = False,
        max_retries: int = 5,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
    ) -> dict:
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.get(url, params=params, headers=headers)

                if resp.status_code == 200:
                    data = resp.json() if not is_xml else resp.text
                    result = parser(data)
                    LiteratureService._cache_set(cache_key, result)
                    return result

                if resp.status_code == 404:
                    logger.info(f"{source} returned 404, no metadata available")
                    result = {}
                    LiteratureService._cache_set(cache_key, result, ttl=3600)
                    return result

                if resp.status_code in (429, 503, 502):
                    if attempt < max_retries:
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        logger.warning(
                            f"{source} rate-limited ({resp.status_code}), "
                            f"retry {attempt + 1}/{max_retries} after {delay:.1f}s"
                        )
                        await asyncio.sleep(delay)
                        continue
                    last_error = f"{source} HTTP {resp.status_code} after {max_retries} retries"
                else:
                    last_error = f"{source} HTTP {resp.status_code}"
                    break

            except (httpx.TimeoutException, httpx.ConnectError) as e:
                if attempt < max_retries:
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    logger.warning(
                        f"{source} connection error: {e}, "
                        f"retry {attempt + 1}/{max_retries} after {delay:.1f}s"
                    )
                    await asyncio.sleep(delay)
                    continue
                last_error = str(e)
            except Exception as e:
                last_error = str(e)
                break

        logger.error(f"{source} fetch failed: {last_error}")
        result = {}
        LiteratureService._cache_set(cache_key, result, ttl=600)
        return result

    @staticmethod
    def _cache_get(key: str) -> Optional[dict]:
        if key in _metadata_cache:
            ts, data = _metadata_cache[key]
            if time.time() - ts < _metadata_cache_ttl:
                return data
            del _metadata_cache[key]
        return None

    @staticmethod
    def _cache_set(key: str, data: dict, ttl: int = None):
        ttl = ttl if ttl is not None else _metadata_cache_ttl
        _metadata_cache[key] = (time.time(), data)

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
    def _is_likely_author_line(line: str) -> bool:
        """Check whether a line looks more like author names than a title.

        Uses multiple signals: comma-separated short-name patterns,
        super-script affiliation markers, function-word density,
        proper-name density, and institutional keyword presence.
        """
        stripped = line.strip()
        if not stripped:
            return False

        words = stripped.split()
        word_count = len(words)
        if word_count < 2:
            return False

        # Signal 1: comma-separated short fragments (classic author list)
        if "," in stripped:
            fragments = [f.strip() for f in stripped.split(",") if f.strip()]
            if len(fragments) >= 2:
                # Check if fragments look like person names (short, no long words)
                short_frags = [f for f in fragments if len(f.split()) <= 3 and len(f) < 40]
                if len(short_frags) >= len(fragments) * 0.7:
                    return True

        # Signal 2: superscript digit / symbol markers (author affiliation refs)
        if SUPERSCRIPT_PATTERN.search(stripped):
            return True

        # Signal 3: affiliation marker at line start ("1 Department of ...")
        if AFFILIATION_MARKER_PATTERN.match(stripped):
            return True

        # Signal 4: very high density of capitalized proper-noun-like words,
        # combined with very low density of function words.
        func_word_count = sum(1 for w in words if w in FUNCTION_WORDS)
        capitalized_count = sum(1 for w in words if w and w[0].isupper() and len(w) > 1)
        func_ratio = func_word_count / max(word_count, 1)
        cap_ratio = capitalized_count / max(word_count, 1)

        # Titles typically have function words (articles, prepositions, conjunctions).
        # Author lines have almost none.
        if func_ratio < 0.05 and cap_ratio > 0.8 and word_count >= 3:
            return True

        # Signal 5: lines with institutional/affiliation keywords
        lower = stripped.lower()
        inst_hits = sum(1 for kw in AUTHOR_INDICATOR_WORDS if kw in lower)
        if inst_hits >= 2:
            return True

        return False

    @staticmethod
    def extract_title_from_text(text: str) -> Optional[str]:
        """Extract the most probable title from the first 50 lines of text.

        Uses multi-signal scoring, re-ranks candidates by position,
        and applies post-validation to filter out author-like false positives.
        """
        raw_lines = text.splitlines()[:50]
        lines = [line.strip() for line in raw_lines if line.strip()]
        if not lines:
            return None

        # ------------------------------------------------------------------
        # Phase 1: score every line
        # ------------------------------------------------------------------
        candidates = []
        for i, line in enumerate(lines):
            score = 0
            word_count = len(line.split())

            # --- Size preferences (titles are 5-25 words) ---
            if 6 <= word_count <= 25:
                score += 5
            elif 4 <= word_count < 6:
                score += 2
            elif 26 <= word_count <= 35:
                score += 1

            # --- Penalize common sentence starters ---
            if COMMON_START_WORDS.match(line):
                score -= 3

            # --- Markdown-header bonus ---
            if line.startswith("# "):
                score += 5
                line = line.lstrip("# ").strip()

            # --- Length penalties ---
            if len(line) < 10:
                score -= 4
            if len(line) > 250:
                score -= 3

            # --- Alpha-ratio check (titles are mostly letters) ---
            alpha_ratio = sum(c.isalpha() or c.isspace() for c in line) / max(len(line), 1)
            if alpha_ratio < 0.75:
                score -= 4

            # --- Penalize very-first-line (often journal / conference header) ---
            if i == 0 and word_count <= 8:
                score -= 4
            elif i == 0:
                score -= 2

            # --- Sentences ending with "." are unlikely titles ---
            if line.strip().endswith(".") and word_count > 4:
                score -= 5

            # --- PDF / header / footer noise ---
            lower_line = line.lower()
            if any(kw in lower_line for kw in ["pdf", "arxiv", "license", "creative commons", "copyright"]):
                score -= 8
            if lower_line.startswith("http"):
                score -= 10

            # --- Function-word density: titles have ~20-50% function words ---
            words_in_line = line.split()
            func_count = sum(1 for w in words_in_line if w in FUNCTION_WORDS)
            func_ratio = func_count / max(len(words_in_line), 1)
            if 0.10 <= func_ratio <= 0.60:
                score += 4
            elif func_ratio < 0.05:
                score -= 6

            # --- Author-like pattern penalty ---
            if LiteratureService._is_likely_author_line(line):
                score -= 20

            # --- Institutional keyword density ---
            inst_hits = sum(1 for kw in AUTHOR_INDICATOR_WORDS if kw in lower_line)
            if inst_hits >= 2:
                score -= 8

            # --- Neighbor context ---
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                next_lower = next_line.lower()

                # Next line is author-looking → strong title bonus
                if LiteratureService._is_likely_author_line(next_line):
                    score += 8

                # Next line has abstract / affiliation keywords → moderate title bonus
                elif any(k in next_lower for k in ["abstract", "keywords", "introduction", "@",
                                                     "university", "institute", "department", "lab"]):
                    score += 3

            # Previous line is short / blank-like → title often follows separator
            if i > 0 and len(lines[i - 1]) < 25:
                score += 2

            # --- Position bonus: titles are usually in the first 10 non-empty lines ---
            if i <= 8:
                score += 3
            elif i <= 15:
                score += 1

            # --- DOI / arXiv / URL penalty ---
            if DOI_PATTERN.search(line) or ARXIV_URL_PATTERN.search(line) or ARXIV_ID_PATTERN.search(line):
                score -= 8

            # --- Abstract / section-header penalty ---
            if re.search(r"\b(Abstract|Summary|Introduction|Background|Keywords|References|Acknowledgments?)\b", line, re.IGNORECASE):
                score -= 30

            # --- Email-address penalty ---
            if "@" in line and "." in line.split("@")[-1]:
                score -= 25

            # --- Uppercase ratio: ALL-CAPS lines are usually section headers, not titles ---
            upper_count = sum(1 for w in words_in_line if w.isupper() and len(w) > 1)
            upper_ratio = upper_count / max(len(words_in_line), 1)
            if upper_ratio > 0.7:
                score -= 5

            # --- Multi-sentence penalty (titles are single-phrase) ---
            if line.count(".") >= 2 and word_count > 10:
                score -= 12

            candidates.append((score, line, i))

        # ------------------------------------------------------------------
        # Phase 2: if no candidates, fall back to first reasonable line
        # ------------------------------------------------------------------
        if not candidates:
            fallback = lines[0][:100] if lines else None
            logger.warning(f"Title extraction fallback used: {fallback}")
            return fallback

        # Sort descending by score
        candidates.sort(key=lambda x: x[0], reverse=True)

        # ------------------------------------------------------------------
        # Phase 3: post-validation skip of author-like top candidates
        # ------------------------------------------------------------------
        chosen = None
        chosen_score = None
        chosen_idx = None

        for score, cand_line, idx in candidates:
            # Skip this candidate if it is an author-like line AND there
            # exists a higher-ranked candidate after it that is NOT author-like.
            is_author_like = LiteratureService._is_likely_author_line(cand_line)

            if is_author_like:
                # Look ahead: is there a better non-author candidate?
                better_found = any(
                    s2 > (score * 0.5) and not LiteratureService._is_likely_author_line(cl)
                    for s2, cl, _ in candidates
                )
                if better_found:
                    logger.info(
                        f"Title candidate skipped (likely author): "
                        f"\"{cand_line[:80]}\" score={score}"
                    )
                    continue

            chosen = cand_line
            chosen_score = score
            chosen_idx = idx
            break

        if not chosen:
            # All candidates look like authors — take the best-positioned one
            # near the top of the document.
            candidates.sort(key=lambda x: x[2])
            for score, cl, idx in candidates:
                if not LiteratureService._is_likely_author_line(cl):
                    chosen, chosen_score, chosen_idx = cl, score, idx
                    break
            if not chosen:
                chosen, chosen_score, chosen_idx = candidates[0][1], candidates[0][0], candidates[0][2]

        best_score = chosen_score
        best_line = chosen
        best_idx = chosen_idx

        # ------------------------------------------------------------------
        # Phase 4: merge adjacent title-like lines (multi-line titles)
        # ------------------------------------------------------------------
        title_parts = [best_line]

        # Look backward: merge if previous line is title-like and not author-like
        for idx in range(best_idx - 1, -1, -1):
            prev_line = lines[idx]
            if LiteratureService._is_likely_author_line(prev_line):
                break
            if AFFILIATION_MARKER_PATTERN.match(prev_line):
                break
            if any(k in prev_line.lower() for k in ["conference", "proceedings", "journal of", "transactions on", "symposium"]):
                break
            if "," in prev_line and len(prev_line.split(",")) >= 2:
                break
            if len(prev_line) > 6 and not prev_line.strip().endswith("."):
                title_parts.insert(0, prev_line)
            else:
                break

        # Look forward: merge if next line is title-like
        for idx in range(best_idx + 1, len(lines)):
            next_line = lines[idx]
            if LiteratureService._is_likely_author_line(next_line):
                break
            if AFFILIATION_MARKER_PATTERN.match(next_line):
                break
            if any(k in next_line.lower() for k in ["abstract", "keywords", "university",
                                                         "institute", "college", "department", "lab", "@"]):
                break
            if "," in next_line and len(next_line.split(",")) >= 2:
                break
            if len(next_line) < 5 or next_line.strip().endswith("."):
                break
            if re.search(r"\b(Abstract|Summary|Introduction)\b", next_line, re.IGNORECASE):
                break
            title_parts.append(next_line)

        title = " ".join(title_parts).strip()

        # ------------------------------------------------------------------
        # Phase 5: final cleanup — truncate at first author/affiliation marker
        # ------------------------------------------------------------------
        sup_match = SUPERSCRIPT_PATTERN.search(title)
        if sup_match:
            title = title[:sup_match.start()].strip()

        aff_match = AFFILIATION_MARKER_PATTERN.search(title)
        if aff_match and aff_match.start() > 5:
            title = title[:aff_match.start()].strip()

        # Truncate at first comma if what follows looks like pure author list
        comma_idx = title.find(",")
        if comma_idx > 10:
            after_comma = title[comma_idx + 1:].strip()
            after_words = after_comma.split()
            if after_words and len(after_words) >= 2:
                afunc = sum(1 for w in after_words if w in FUNCTION_WORDS) / max(len(after_words), 1)
                if afunc < 0.06:
                    title = title[:comma_idx].strip()

        return title[:300] if title else None

    # ------------------------------------------------------------------
    # Layer 3: Authors & Abstract extraction from text
    # ------------------------------------------------------------------
    @staticmethod
    def extract_authors_from_text(text: str, title: Optional[str] = None) -> Optional[str]:
        """Heuristic extraction of authors from text.

        Searches a window of lines near the title for author-name patterns.
        """
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            return None

        # Find the line containing the title to anchor our search window
        start_idx = 0
        if title:
            best_match_idx = -1
            best_match_len = 0
            title_lower = title.lower()
            for i, line in enumerate(lines):
                line_lower = line.lower()
                # Look for substantial overlap between line and title
                overlap = 0
                title_words = set(title_lower.split())
                line_words = set(line_lower.split())
                common = title_words & line_words
                overlap = len(common) / max(len(title_words), 1)
                if overlap > 0.3 and len(common) > best_match_len:
                    best_match_len = len(common)
                    best_match_idx = i
            if best_match_idx >= 0:
                start_idx = best_match_idx + 1
            else:
                # Fallback: substring match
                for i, line in enumerate(lines):
                    if title_lower in line_lower or line_lower in title_lower:
                        start_idx = i + 1
                        break

        # Collect author candidates from a window of lines after title position
        author_lines = []
        seen_abstract = False

        for line in lines[start_idx:start_idx + 12]:
            lower = line.lower()

            # Stop at section boundaries
            if re.search(r"\b(Abstract|Summary|Introduction|Background|Keywords|References?)\b", lower):
                if re.match(r"^(Abstract|Summary|Introduction|Background|Keywords|References?)\s*", lower):
                    if not seen_abstract and re.match(r"^Abstract", lower, re.IGNORECASE):
                        seen_abstract = True
                        continue
                    break
                seen_abstract = True
                continue

            # Skip URLs
            if line.startswith("http") or line.startswith("www"):
                continue

            # Skip email lines
            if "@" in line:
                continue

            # Skip affiliation lines
            if AFFILIATION_MARKER_PATTERN.match(line):
                continue
            inst_hits = sum(1 for kw in AUTHOR_INDICATOR_WORDS if kw in lower)
            if inst_hits >= 1:
                continue

            # Skip lines that are too long (likely abstract or title continuation)
            if len(line) > 250:
                continue

            # Use the author detector: if it's clearly an author line, collect it
            if LiteratureService._is_likely_author_line(line):
                cleaned = EMAIL_PATTERN.sub("", line)
                cleaned = PAREN_UNIT_PATTERN.sub("", cleaned)
                cleaned = DIGIT_MARKER_PATTERN.sub("", cleaned)
                cleaned = SUPERSCRIPT_PATTERN.sub("", cleaned)
                cleaned = cleaned.strip(" ,;*†‡§¶")
                if cleaned and len(cleaned) > 2:
                    author_lines.append(cleaned)
                continue

            # Also collect lines that are not clearly NOT authors
            # (fallback for single-name / unusual formats)
            if len(line) < 5:
                continue

            cleaned = EMAIL_PATTERN.sub("", line)
            cleaned = PAREN_UNIT_PATTERN.sub("", cleaned)
            cleaned = DIGIT_MARKER_PATTERN.sub("", cleaned)
            cleaned = SUPERSCRIPT_PATTERN.sub("", cleaned)
            cleaned = cleaned.strip(" ,;*†‡§¶")
            if cleaned and 2 < len(cleaned) < 200:
                author_lines.append(cleaned)

            if seen_abstract:
                break

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
            "- title: The COMPLETE paper title (NOT author names). A title is a descriptive phrase\n"
            "  with 6-30 words, often containing prepositions, colons, or technical terms.\n"
            "  Author name lines contain commas, short fragments, superscript digits/asterisks.\n"
            "  DO NOT output an author name line as the title.\n"
            "- authors: Comma-separated list of author names (omit affiliations/superscripts).\n"
            "  If no author information is clearly visible, use null.\n"
            "- abstract: The abstract text (first 500 chars is enough)\n"
            "- year: Publication year (4 digits), use null if unclear\n"
            "- journal: Journal or conference name, use null if unclear\n"
            "- doi: DOI if present, use null otherwise\n\n"
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
        """Multi-tier metadata extraction: identifiers → local rules → AI.

        Tier 1: Extract DOI/arXiv and query external APIs (with cache + retry).
        Tier 2: If no title from APIs, use local heuristic extraction.
        Tier 3: If still no title and AI is available, use AI extraction.
        """
        metadata = {"title": None, "authors": None, "abstract": None, "year": None, "journal": None, "doi": None}

        # Tier 1: Identifier-based extraction
        ids = LiteratureService.extract_identifiers(text)
        logger.info(f"Extracted identifiers: {ids}")

        if ids["doi"]:
            logger.info(f"Tier 1: Fetching Crossref metadata for DOI: {ids['doi']}")
            metadata = await LiteratureService.fetch_crossref_metadata(ids["doi"])
            metadata["doi"] = ids["doi"]
        elif ids["arxiv"]:
            logger.info(f"Tier 1: Fetching arXiv metadata for ID: {ids['arxiv']}")
            metadata = await LiteratureService.fetch_arxiv_metadata(ids["arxiv"])

        # Tier 2: Local rule-based extraction for missing fields
        if not metadata.get("title"):
            logger.info("Tier 2: Local heuristic title extraction")
            title = LiteratureService.extract_title_from_text(text)
            if title:
                metadata["title"] = title
            else:
                first_line = text.strip().splitlines()[0][:100] if text.strip() else None
                metadata["title"] = first_line
                logger.warning(f"Absolute title fallback used: {first_line}")

        if not metadata.get("authors"):
            metadata["authors"] = LiteratureService.extract_authors_from_text(text, metadata.get("title"))
        if not metadata.get("abstract"):
            metadata["abstract"] = LiteratureService.extract_abstract_from_text(text)

        # Tier 3: AI extraction (only if still no meaningful title and AI is available)
        if ai_client and model and (
            not metadata.get("title")
            or metadata.get("title") == (text.strip().splitlines()[0][:100] if text.strip() else None)
        ):
            logger.info("Tier 3: Attempting AI-based metadata extraction")
            try:
                ai_metadata = await asyncio.wait_for(
                    LiteratureService.extract_metadata_by_ai(text, ai_client, model),
                    timeout=30.0,
                )
                if ai_metadata.get("title"):
                    # Post-validation: reject AI title if it looks like an author line
                    if not LiteratureService._is_likely_author_line(ai_metadata["title"]):
                        metadata.update({k: v for k, v in ai_metadata.items() if v is not None})
                        logger.info("Tier 3: AI extraction successful")
                    else:
                        logger.warning(
                            f"Tier 3: AI title rejected (likely author): \"{ai_metadata['title'][:80]}\""
                        )
                        # Keep AI-extracted year/journal/doi if they look sane
                        for field in ("year", "journal", "doi"):
                            if ai_metadata.get(field):
                                metadata[field] = ai_metadata[field]
            except asyncio.TimeoutError:
                logger.warning("Tier 3: AI extraction timed out after 30s")
            except Exception as e:
                logger.error(f"Tier 3: AI extraction failed: {e}")

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
            file_size=literature_in.file_size,
            raw_text=literature_in.raw_text,
            status=literature_in.status or "unread",
            folder_id=literature_in.folder_id,
        )
        db.add(db_literature)
        await db.commit()
        await db.refresh(db_literature)
        return db_literature

    @staticmethod
    async def update_literature(db: AsyncSession, db_literature: Literature, literature_in: LiteratureUpdate) -> Literature:
        if literature_in.title is not None:
            db_literature.title = literature_in.title
        if literature_in.authors is not None:
            db_literature.authors = literature_in.authors
        if literature_in.abstract is not None:
            db_literature.abstract = literature_in.abstract
        if literature_in.year is not None:
            db_literature.year = literature_in.year
        if literature_in.journal is not None:
            db_literature.journal = literature_in.journal
        if literature_in.doi is not None:
            db_literature.doi = literature_in.doi
        if literature_in.status is not None:
            db_literature.status = literature_in.status
        if literature_in.folder_id is not None:
            db_literature.folder_id = literature_in.folder_id
        if literature_in.raw_text is not None:
            db_literature.raw_text = literature_in.raw_text
        await db.commit()
        await db.refresh(db_literature)
        return db_literature

    @staticmethod
    async def delete_literature(db: AsyncSession, literature: Literature) -> None:
        literature_id = literature.id
        file_path = literature.file_path

        await db.execute(delete(AIAnalysis).where(AIAnalysis.literature_id == literature_id))
        await db.execute(delete(Note).where(Note.literature_id == literature_id))
        await db.execute(delete(LiteratureChunk).where(LiteratureChunk.literature_id == literature_id))
        await db.execute(delete(ReadingRecord).where(ReadingRecord.literature_id == literature_id))
        await db.execute(
            Presentation.__table__.update()
            .where(Presentation.literature_id == literature_id)
            .values(literature_id=None)
        )
        await db.execute(delete(literature_tags).where(literature_tags.c.literature_id == literature_id))
        await db.delete(literature)
        await db.commit()

        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Deleted PDF file: {file_path}")
            except OSError as e:
                logger.warning(f"Failed to delete PDF file {file_path}: {e}")

    @staticmethod
    async def get_literatures_by_user(
        db: AsyncSession,
        user_id: str,
        skip: int = 0,
        limit: int = 20,
        title: Optional[str] = None,
        status: Optional[str] = None,
        sort_by_year: Optional[str] = None,
        folder_id: Optional[str] = None,
    ):
        query = select(Literature).where(Literature.user_id == user_id)
        count_query = select(func.count(Literature.id)).where(Literature.user_id == user_id)

        if title:
            query = query.where(Literature.title.ilike(f"%{title}%"))
            count_query = count_query.where(Literature.title.ilike(f"%{title}%"))

        if status:
            query = query.where(Literature.status == status)
            count_query = count_query.where(Literature.status == status)

        if folder_id is not None:
            if folder_id == "__none__":
                query = query.where(Literature.folder_id == None)
                count_query = count_query.where(Literature.folder_id == None)
            else:
                query = query.where(Literature.folder_id == folder_id)
                count_query = count_query.where(Literature.folder_id == folder_id)

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
