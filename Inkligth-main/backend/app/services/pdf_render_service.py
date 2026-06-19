import asyncio
import io
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Optional

import numpy as np
import fitz
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfinterp import PDFResourceManager
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfparser import PDFParser
from pdf2zh.converter import PDFConverterEx, TranslateConverter
from pdf2zh.pdfinterp import PDFPageInterpreterEx
from pymupdf import Font, Document

from app.core.ai_providers.translator import OpenAITranslator
from babeldoc.assets.assets import get_font_and_metadata
from app.utils.layout_model import get_layout_model

logger = logging.getLogger(__name__)

_NOTI_NAME = "noto"

_REFERENCE_PATTERNS = re.compile(
    r"^(?:references?\s*$|references?\s*and\s+notes?\s*$|bibliography\s*$|"
    r"literature\s*cited\s*$|reference\s*list\s*$|works\s*cited\s*$|"
    r"acknowledgments?\s*$|acknowledgements?\s*$|supplementary\s+materials?\s*$)",
    re.IGNORECASE,
)

_executor = ThreadPoolExecutor(max_workers=1)


class Pdf2ZhTranslatorAdapter:
    """适配器：将 InkLight 的异步 OpenAITranslator 包装为 PDFMathTranslate
    TranslateConverter 所需的同步接口。"""

    def __init__(self, ai_client, model, source_lang="en", target_lang="zh", cancel_check=None):
        self._translator = OpenAITranslator(
            client=ai_client, model=model, cancel_check=cancel_check
        )
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.lang_out = target_lang  # TranslateConverter 需要此属性

    def translate(self, text: str) -> str:
        """同步翻译方法，供 TranslateConverter 的线程池调用。"""
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(
                self._translator.translate(text, self.source_lang, self.target_lang)
            )
        finally:
            loop.close()

    def cleanup(self):
        self._translator = None


class InkLightTranslateConverter(TranslateConverter):
    """继承 TranslateConverter，但跳过基类的 translator 自动发现逻辑（service 匹配），
    直接使用外部传入的 translator 实例。
    同时覆盖 vfont 去掉 .*Ital，避免摘要等斜体文字被误判为公式跳过翻译。"""

    def __init__(self, rsrcmgr, *, translator, thread=0, layout=None,
                 noto_name="", noto=None):
        PDFConverterEx.__init__(self, rsrcmgr)
        # 去掉 .*Ital，避免摘要等斜体文字被误判为公式
        self.vfont = r"(CM[^R]|MS.M|XY|MT|BL|RM|EU|LA|RS|LINE|LCIRCLE|TeX-|rsfs|txsy|wasy|stmary|.*Mono|.*Code|.*Sym|.*Math)"
        self.vchar = None
        self.thread = thread
        self.layout = {} if layout is None else layout
        self.noto_name = noto_name
        self.noto = noto
        self.translator = translator
        if not self.translator:
            raise ValueError("translator is required")


class PdfRenderService:

    @staticmethod
    def _detect_reference_page(pages_info: list[dict]) -> int:
        """Returns the page index (0-based) where references begin, or -1."""
        for i, info in enumerate(pages_info):
            text_sample = info.get("text_sample", "")
            if _REFERENCE_PATTERNS.match(text_sample):
                return i
        return -1

    def _extract_page_text_sample(self, page: fitz.Page) -> str:
        blocks = page.get_text("blocks")
        for b in blocks:
            if b[6] == 0:
                text = b[4].strip().lower()
                if 3 < len(text) < 120:
                    return text
        text = page.get_text("text")
        return text[:200].strip().lower()

    async def build_translated_pdf(
        self,
        source_pdf_path: str,
        ai_client,
        model: str,
        source_lang: str = "en",
        target_lang: str = "zh",
        output_mode: str = "mono",
        progress_callback: Optional[Callable[[int, str], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
    ) -> bytes:
        async def report(pct: int, msg: str):
            if progress_callback:
                await progress_callback(pct, msg)

        def _cancelled() -> bool:
            return bool(cancel_check and cancel_check())

        doc = fitz.open(source_pdf_path)
        total_pages = doc.page_count

        page_text_samples = []
        for pno in range(total_pages):
            sample = self._extract_page_text_sample(doc[pno])
            page_text_samples.append({"page": pno, "text_sample": sample})
        ref_page = self._detect_reference_page(page_text_samples)

        doc.close()

        await report(5, "加载布局模型...")
        layout_model = await get_layout_model()

        await report(10, "准备字体...")

        def _resolve_font_name(lang: str) -> str:
            lang = lang.lower()
            LANG_FONT_MAP = {
                "zh-cn": "SourceHanSerifCN-Regular.ttf",
                "zh-hans": "SourceHanSerifCN-Regular.ttf",
                "zh": "SourceHanSerifCN-Regular.ttf",
                "zh-tw": "SourceHanSerifTW-Regular.ttf",
                "zh-hant": "SourceHanSerifTW-Regular.ttf",
                "ja": "SourceHanSerifJP-Regular.ttf",
                "ko": "SourceHanSerifKR-Regular.ttf",
            }
            return LANG_FONT_MAP.get(lang, "GoNotoKurrent-Regular.ttf")

        font_name = _resolve_font_name(target_lang)

        def _load_font():
            font_path, _ = get_font_and_metadata(font_name)
            return font_path.as_posix()

        loop = asyncio.get_event_loop()
        font_path = await loop.run_in_executor(_executor, _load_font)
        noto_font = Font(_NOTI_NAME, font_path)

        await report(15, "准备文档...")
        doc = fitz.open(source_pdf_path)
        stream = io.BytesIO()
        doc.save(stream)
        doc.close()
        stream.seek(0)

        doc_zh = Document(stream=stream)
        font_list = [("tiro", None), (_NOTI_NAME, font_path)]
        font_id = {}
        for page in doc_zh:
            for name, fp in font_list:
                font_id[name] = page.insert_font(name, fp)

        xreflen = doc_zh.xref_length()
        for xref in range(1, xreflen):
            for label in ["Resources/", ""]:
                try:
                    font_res = doc_zh.xref_get_key(xref, f"{label}Font")
                    target_key_prefix = f"{label}Font/"
                    if font_res[0] == "xref":
                        resource_xref_id = re.search(r"(\d+) 0 R", font_res[1]).group(1)
                        xref = int(resource_xref_id)
                        font_res = ("dict", doc_zh.xref_object(xref))
                        target_key_prefix = ""

                    if font_res[0] == "dict":
                        for name, _fp in font_list:
                            target_key = f"{target_key_prefix}{name}"
                            font_exist = doc_zh.xref_get_key(xref, target_key)
                            if font_exist[0] == "null":
                                doc_zh.xref_set_key(
                                    xref, target_key, f"{font_id[name]} 0 R",
                                )
                except Exception:
                    pass

        fp = io.BytesIO()
        doc_zh.save(fp)
        fp.seek(0)

        await report(17, "创建翻译器...")

        translator_adapter = Pdf2ZhTranslatorAdapter(
            ai_client=ai_client,
            model=model,
            source_lang=source_lang,
            target_lang=target_lang,
            cancel_check=_cancelled,
        )

        rsrcmgr = PDFResourceManager()
        layout = {}
        device = InkLightTranslateConverter(
            rsrcmgr,
            translator=translator_adapter,
            thread=4,
            layout=layout,
            noto_name=_NOTI_NAME,
            noto=noto_font,
        )

        obj_patch = {}
        interpreter = PDFPageInterpreterEx(rsrcmgr, device, obj_patch)

        parser = PDFParser(fp)
        pdf_doc = PDFDocument(parser)

        for pageno, page in enumerate(PDFPage.create_pages(pdf_doc)):
            if _cancelled():
                raise asyncio.CancelledError("任务已取消")

            pct = 18 + int(75 * pageno / total_pages)
            await report(pct, f"处理第 {pageno + 1}/{total_pages} 页...")

            page.pageno = pageno
            pix = doc_zh[pageno].get_pixmap()
            image = np.frombuffer(pix.samples, np.uint8).reshape(
                pix.height, pix.width, 3
            )[:, :, ::-1]

            page_layout = layout_model.predict(image, imgsz=int(pix.height / 32) * 32)[0]

            box = np.ones((pix.height, pix.width))
            h, w = box.shape
            vcls = ["abandon", "figure", "table", "isolate_formula", "formula_caption"]

            for i, d in enumerate(page_layout.boxes):
                if page_layout.names[int(d.cls)] not in vcls:
                    x0, y0, x1, y1 = d.xyxy.squeeze()
                    x0, y0, x1, y1 = (
                        np.clip(int(x0 - 1), 0, w - 1),
                        np.clip(int(h - y1 - 1), 0, h - 1),
                        np.clip(int(x1 + 1), 0, w - 1),
                        np.clip(int(h - y0 + 1), 0, h - 1),
                    )
                    box[y0:y1, x0:x1] = i + 2

            for i, d in enumerate(page_layout.boxes):
                if page_layout.names[int(d.cls)] in vcls:
                    x0, y0, x1, y1 = d.xyxy.squeeze()
                    x0, y0, x1, y1 = (
                        np.clip(int(x0 - 1), 0, w - 1),
                        np.clip(int(h - y1 - 1), 0, h - 1),
                        np.clip(int(x1 + 1), 0, w - 1),
                        np.clip(int(h - y0 + 1), 0, h - 1),
                    )
                    box[y0:y1, x0:x1] = 0

            if ref_page >= 0 and pageno >= ref_page:
                box[:, :] = 0

            layout[pageno] = box
            page.page_xref = doc_zh.get_new_xref()
            doc_zh.update_object(page.page_xref, "<<>>")
            doc_zh.update_stream(page.page_xref, b"")
            doc_zh[pageno].set_contents(page.page_xref)
            await loop.run_in_executor(_executor, interpreter.process_page, page)

        device.close()

        await report(95, "应用翻译...")
        for obj_id, ops_new in obj_patch.items():
            doc_zh.update_stream(obj_id, ops_new.encode())

        await report(98, "字体子集化...")
        try:
            doc_zh.subset_fonts(fallback=True)
        except Exception as e:
            logger.warning("Font subsetting failed: %s", e)

        output = doc_zh.write(deflate=True, garbage=3, use_objstms=1)
        doc_zh.close()

        await report(100, "完成")
        translator_adapter.cleanup()
        return output


pdf_render_service = PdfRenderService()