import logging
import os
import time
import uuid
import threading
from typing import Optional

from captcha.image import ImageCaptcha

logger = logging.getLogger(__name__)

_cleanup_lock = threading.Lock()
_pending_cleanup = False

TTL_SECONDS = 300
_store: dict[str, tuple[str, float]] = {}


def _schedule_cleanup():
    global _pending_cleanup
    with _cleanup_lock:
        if _pending_cleanup:
            return
        _pending_cleanup = True

    def _do_cleanup():
        global _pending_cleanup
        now = time.time()
        to_pop = [k for k, (_, ts) in _store.items() if now - ts > TTL_SECONDS]
        for k in to_pop:
            _store.pop(k, None)
        if to_pop:
            logger.debug(f"Captcha cache cleanup: removed {len(to_pop)} expired entries")
        with _cleanup_lock:
            _pending_cleanup = False

    timer = threading.Timer(60.0, _do_cleanup)
    timer.daemon = True
    timer.start()


_fonts_dir = os.path.join(os.path.dirname(__file__), "..", "..", "fonts")
_fonts = []
if os.path.isdir(_fonts_dir):
    for fname in os.listdir(_fonts_dir):
        if fname.lower().endswith((".ttf", ".otf")):
            _fonts.append(os.path.join(_fonts_dir, fname))
if not _fonts:
    _fonts = None


def generate_captcha(length: int = 6) -> dict:
    import random
    import string
    import io
    import base64

    chars = string.ascii_uppercase + string.digits
    chars = chars.replace("O", "").replace("0", "").replace("I", "").replace("1", "").replace("L", "")
    code = "".join(random.choices(chars, k=length))

    captcha_id = str(uuid.uuid4())
    _store[captcha_id] = (code.lower(), time.time())
    _schedule_cleanup()

    try:
        img_captcha = ImageCaptcha(width=240, height=80, fonts=_fonts)
        buf = io.BytesIO()
        img_captcha.write(code, buf)
        buf.seek(0)
        image_base64 = base64.b64encode(buf.read()).decode("utf-8")
    except Exception as e:
        logger.error(f"Failed to generate captcha image: {e}")
        image_base64 = ""

    return {
        "captcha_id": captcha_id,
        "image_base64": image_base64,
    }


def verify_captcha(captcha_id: str, answer: str) -> bool:
    entry = _store.get(captcha_id)
    if entry is None:
        return False

    stored_code, stored_ts = entry
    if time.time() - stored_ts > TTL_SECONDS:
        _store.pop(captcha_id, None)
        return False

    is_valid = stored_code == answer.strip().lower()

    _store.pop(captcha_id, None)

    if is_valid:
        logger.info(f"Captcha verified: {captcha_id}")
    else:
        logger.warning(f"Captcha verification failed: {captcha_id}")

    return is_valid
