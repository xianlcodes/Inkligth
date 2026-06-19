"""Layout-aware PDF text extraction that filters out figures, tables, formulas.

Adapted from the PDFMathTranslate approach:
1. Render each page to an image
2. Run DocLayout-YOLO model to detect layout regions
3. Create a mask excluding figures, tables, formulas
4. Extract words from the page and keep only those in non-excluded regions
5. Skip reference pages entirely
"""

import logging
import re

import fitz
import numpy as np

from app.utils.layout_model import get_layout_model

logger = logging.getLogger(__name__)

# Layout classes to exclude from translation (matching PDFMathTranslate)
EXCLUDED_CLASSES = frozenset(
    {"abandon", "figure", "table", "isolate_formula", "formula_caption"}
)

# Patterns to detect reference/bibliography section start
REFERENCE_PATTERNS = re.compile(
    r"^(?:references?\s*$|references?\s*and\s+notes?\s*$|bibliography\s*$|"
    r"literature\s*cited\s*$|reference\s*list\s*$|works\s*cited\s*$|"
    r"acknowledgments?\s*$|acknowledgements?\s*$|supplementary\s+materials?\s*$)",
    re.IGNORECASE,
)


def _create_layout_mask(height: int, width: int, page_layout) -> np.ndarray:
    """Create a binary mask where 0 = excluded regions, 1 = text/background.

    PDFMathTranslate approach: zero-out bounding boxes classified as
    figure, table, isolate_formula, formula_caption, or abandon.
    """
    mask = np.ones((height, width))
    for d in page_layout.boxes:
        if page_layout.names[int(d.cls)] in EXCLUDED_CLASSES:
            x0, y0, x1, y1 = d.xyxy
            x0 = np.clip(int(x0 - 1), 0, width - 1)
            y0 = np.clip(int(y0 - 1), 0, height - 1)
            x1 = np.clip(int(x1 + 1), 0, width - 1)
            y1 = np.clip(int(y1 + 1), 0, height - 1)
            mask[y0:y1, x0:x1] = 0
    return mask


def _detect_reference_page(doc: fitz.Document) -> int:
    """Return the 0-based page index where references begin, or -1."""
    for i in range(doc.page_count):
        text = doc[i].get_text("text")[:200].strip().lower()
        if REFERENCE_PATTERNS.match(text):
            return i
    return -1


async def extract_filtered_text(pdf_path: str) -> str:
    """Extract text from a PDF, excluding figures, tables, and formulas.

    Uses the DocLayout-YOLO model (same as PDFMathTranslate) to detect
    layout regions on each page, then filters out words that fall within
    excluded regions.  Reference/bibliography pages are skipped entirely.
    """
    model = await get_layout_model()

    doc = fitz.open(pdf_path)
    try:
        ref_page = _detect_reference_page(doc)
        filtered_pages = []

        for pageno in range(doc.page_count):
            if ref_page >= 0 and pageno >= ref_page:
                logger.info("Skipping reference page %s", pageno + 1)
                break

            page = doc[pageno]

            # Render page to image for layout detection
            pix = page.get_pixmap()
            img = np.frombuffer(pix.samples, np.uint8).reshape(
                pix.height, pix.width, 3
            )[:, :, ::-1]

            # Predict layout (imgsz aligned to stride)
            page_layout = model.predict(img, imgsz=int(pix.height / 32) * 32)[0]

            # Build exclusion mask
            mask = _create_layout_mask(pix.height, pix.width, page_layout)

            # Extract words with positions: (x0, y0, x1, y1, word, block_no, line_no)
            words = page.get_text("words")

            # Filter words in excluded regions by checking their center point
            filtered_words = []
            for w in words:
                cx = int((w[0] + w[2]) / 2)
                cy = int((w[1] + w[3]) / 2)
                cx = np.clip(cx, 0, pix.width - 1)
                cy = np.clip(cy, 0, pix.height - 1)
                if mask[cy, cx] != 0:
                    filtered_words.append(w[4])

            page_text = " ".join(filtered_words)
            filtered_pages.append(page_text)

        return "\n\n".join(filtered_pages)
    finally:
        doc.close()
