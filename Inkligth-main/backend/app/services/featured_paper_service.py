import logging
import xml.etree.ElementTree as ET
from datetime import date
from typing import Optional
from urllib.parse import urlparse, parse_qs

import httpx
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.featured_paper import FeaturedPaper

logger = logging.getLogger(__name__)

ARXIV_API_BASE = "https://export.arxiv.org/api/query"
ARXIV_ABS_BASE = "https://arxiv.org/abs"
REQUEST_TIMEOUT = 30.0
USER_AGENT = "InkLight/1.0 (Academic Literature Platform; mailto:contact@inklight.com)"

ARXIV_NAMESPACES = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}


def _clean_arxiv_title(raw: str) -> str:
    """arXiv API 返回的标题可能包含换行，清理成一行的同时保留基本结构。"""
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    return " ".join(lines)


def _extract_arxiv_id_from_url(url: str) -> str:
    """从 arXiv URL 提取纯 ID（去除版本号）。"""
    # URL 格式：http://arxiv.org/abs/2101.00001v1
    path = urlparse(url).path
    arxiv_id = path.rsplit("/", 1)[-1]
    # 去除版本后缀，如 v1, v2
    parts = arxiv_id.rsplit("v", 1)
    if len(parts) == 2 and parts[1].isdigit():
        arxiv_id = parts[0]
    return arxiv_id


async def fetch_papers_by_category(category: str, max_results: int = 5) -> list[dict]:
    """调用 arXiv API 获取指定分类的最新论文，返回规范化的 dict 列表。"""
    params = {
        "search_query": f"cat:{category}",
        "sortBy": "submittedDate",
        "sortOrder": "descending",
        "max_results": max_results,
    }

    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            resp = await client.get(
                ARXIV_API_BASE,
                params=params,
                headers={"User-Agent": USER_AGENT},
            )
            resp.raise_for_status()
    except httpx.TimeoutException:
        logger.warning("arXiv API timeout for category %s", category)
        return []
    except httpx.HTTPStatusError as e:
        logger.warning("arXiv API HTTP error for category %s: %s", category, e)
        return []
    except Exception as e:
        logger.error("arXiv API request failed for category %s: %s", category, e)
        return []

    try:
        root = ET.fromstring(resp.text)
    except ET.ParseError as e:
        logger.error("Failed to parse arXiv XML for category %s: %s", category, e)
        return []

    papers = []
    for entry in root.findall("atom:entry", ARXIV_NAMESPACES):
        paper = _parse_arxiv_entry(entry, category)
        if paper:
            papers.append(paper)

    return papers


def _parse_arxiv_entry(entry: ET.Element, category: str) -> Optional[dict]:
    """解析 arXiv Atom 的单个 <entry> 元素。"""
    # ID / URL
    id_elem = entry.find("atom:id", ARXIV_NAMESPACES)
    if id_elem is None or not id_elem.text:
        return None
    arxiv_url = id_elem.text.strip()
    arxiv_id = _extract_arxiv_id_from_url(arxiv_url)

    # Title
    title_elem = entry.find("atom:title", ARXIV_NAMESPACES)
    if title_elem is None or not title_elem.text:
        return None
    title = _clean_arxiv_title(title_elem.text)

    # Abstract
    summary_elem = entry.find("atom:summary", ARXIV_NAMESPACES)
    abstract = ""
    if summary_elem is not None and summary_elem.text:
        abstract = summary_elem.text.strip()

    # Authors
    authors = []
    for author_elem in entry.findall("atom:author", ARXIV_NAMESPACES):
        name_elem = author_elem.find("atom:name", ARXIV_NAMESPACES)
        if name_elem is not None and name_elem.text:
            authors.append(name_elem.text.strip())
    authors_str = ", ".join(authors)

    # Published date
    published_elem = entry.find("atom:published", ARXIV_NAMESPACES)
    published_date = date.today()
    if published_elem is not None and published_elem.text:
        try:
            published_date = date.fromisoformat(published_elem.text[:10])
        except ValueError:
            pass

    # 确保 URL 使用 https
    abs_url = f"{ARXIV_ABS_BASE}/{arxiv_id}"

    return {
        "arxiv_id": arxiv_id,
        "title": title,
        "authors": authors_str,
        "abstract": abstract,
        "arxiv_url": abs_url,
        "published_date": published_date,
        "category": category,
    }


async def fetch_and_store_featured_papers(
    db: AsyncSession,
    categories: Optional[list[str]] = None,
    papers_per_category: int = 5,
) -> int:
    """获取指定分类的最新论文，先清空旧数据再重新插入。

    返回本次插入的论文数量。
    """
    if categories is None:
        categories = ["cs.AI", "cs.CL", "eess.IV"]

    all_papers: list[dict] = []
    for category in categories:
        papers = await fetch_papers_by_category(category, max_results=papers_per_category)
        all_papers.extend(papers)
        logger.info("Fetched %d papers from arXiv category %s", len(papers), category)

    if not all_papers:
        logger.warning("No papers fetched from arXiv for any category")
        return 0

    # 跨分类去重
    seen_ids: set[str] = set()
    unique_papers: list[dict] = []
    for p in all_papers:
        aid = p["arxiv_id"]
        if aid not in seen_ids:
            seen_ids.add(aid)
            unique_papers.append(p)
    all_papers = unique_papers

    # 清空旧数据，只保留当天拉取的最新结果
    await db.execute(delete(FeaturedPaper))
    await db.flush()

    new_count = 0
    for paper_data in all_papers:
        paper = FeaturedPaper(
            arxiv_id=paper_data["arxiv_id"],
            title=paper_data["title"],
            authors=paper_data["authors"],
            abstract=paper_data["abstract"],
            arxiv_url=paper_data["arxiv_url"],
            published_date=paper_data["published_date"],
            category=paper_data["category"],
        )
        db.add(paper)
        new_count += 1

    await db.commit()
    logger.info("Replaced all featured papers: stored %d papers", new_count)

    return new_count


async def get_featured_papers(
    db: AsyncSession,
    limit: int = 15,
) -> list[FeaturedPaper]:
    """返回最新的 limit 条精选论文。"""
    result = await db.execute(
        select(FeaturedPaper)
        .order_by(FeaturedPaper.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
