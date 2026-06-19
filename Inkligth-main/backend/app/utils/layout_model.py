"""Shared layout model singleton for PDF layout analysis.

Provides a single OnnxModel instance shared across all services that need
document layout detection (figures, tables, formulas, etc.).
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from babeldoc.docvision.doclayout import OnnxModel

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=1)
_lock = asyncio.Lock()
_model: Optional[OnnxModel] = None


async def get_layout_model() -> OnnxModel:
    """Get or create the shared OnnxModel singleton (thread-safe, lazy-loaded)."""
    global _model
    if _model is not None:
        return _model
    async with _lock:
        if _model is not None:
            return _model
        loop = asyncio.get_event_loop()
        _model = await loop.run_in_executor(_executor, OnnxModel.from_pretrained)
        logger.info("Layout model loaded successfully")
        return _model
