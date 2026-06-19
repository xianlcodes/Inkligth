import logging
import zlib
import json
from typing import Optional, Any

logger = logging.getLogger(__name__)

COMPRESSION_LEVEL = 6


def compress_json(data: Any) -> bytes:
    json_str = json.dumps(data, ensure_ascii=False)
    original_len = len(json_str)
    compressed = zlib.compress(json_str.encode("utf-8"), level=COMPRESSION_LEVEL)
    ratio = (1 - len(compressed) / max(original_len, 1)) * 100
    logger.debug("Compressed %d bytes → %d bytes (%.1f%% reduction)", original_len, len(compressed), ratio)
    return compressed


def decompress_json(data: Optional[bytes]) -> Optional[str]:
    if not data:
        return None
    try:
        decompressed = zlib.decompress(data)
        return decompressed.decode("utf-8")
    except zlib.error as e:
        logger.error("Decompression failed: %s", e)
        return None
