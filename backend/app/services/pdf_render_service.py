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

from app.core.ai_providers.translator import NoUsableTranslationError, OpenAITranslator
from babeldoc.assets.assets import get_font_and_metadata
from app.utils.layout_model import get_layout_model

logger = logging.getLogger(__name__)

_NOTI_NAME = "noto"

_REFERENCE_PATTERNS = re.compile(
    r"^(?:references?\s*$|references?\s+and\s+notes?\s*$|bibliography\s*$|"
    r"literature\s*cited\s*$|reference\s*list\s*$|works\s*cited\s*$|"
    r"acknowledgments?\s*$|acknowledgements?\s*$|supplementary\s+materials?\s*$)",
    re.IGNORECASE,
)

# output_mode 取值归一化：前端（PdfTranslateDialog）传 mono / dual，这里额外兼容历史写法
_DUAL_MODE_ALIASES = {"dual", "bilingual", "dual_page", "side_by_side", "compare"}
_MONO_MODE_ALIASES = {"mono", "translated", "translation_only", "chinese_only"}

# 译文大面积失败（多半是模型/密钥配置问题）时中止任务，避免继续烧额度并输出未翻译的 PDF
_DEGRADED_MIN_CALLS = 6
_DEGRADED_FAILURE_RATIO = 0.5

_executor = ThreadPoolExecutor(max_workers=1)


def normalize_output_mode(output_mode: str | None) -> str:
    """把 output_mode 归一化为 mono / dual。

    前端传的是 mono|dual；这里兼容 bilingual / dual_page 等写法，
    避免因为命名不一致而静默退化成纯译文。
    """
    mode = (output_mode or "").strip().lower()
    if mode in _DUAL_MODE_ALIASES:
        return "dual"
    if not mode or mode in _MONO_MODE_ALIASES:
        return "mono"
    logger.warning("未知的 output_mode '%s'，按 mono 处理", output_mode)
    return "mono"


class Pdf2ZhTranslatorAdapter:
    """适配器：将 InkLight 的异步 OpenAITranslator 包装为 PDFMathTranslate
    TranslateConverter 所需的同步接口。

    注意：pdf2zh 会在线程池中调用 translate()，并在方法内部创建全新的事件循环。
    httpx 连接池绑定创建时的事件循环，跨循环复用 AsyncOpenAI 客户端会挂起请求。
    因此这里保存原始凭据（api_key / base_url），每次 translate() 都新建客户端。

    另外 pdf2zh 的 TranslateConverter 用 @retry(wait=wait_fixed(1)) 包住
    translate()，tenacity 默认 stop=stop_never（无限重试任何异常），从适配器里
    把异常抛出去会让整个任务卡死在当前页。所以这里把所有失败降级为「保留原文」，
    并通过 is_degraded() 把失败率交给 build_translated_pdf 判断是否中止任务。
    """

    def __init__(self, api_key, base_url, model,
                 source_lang="en", target_lang="zh", cancel_check=None,
                 timeout=300.0):
        self._api_key = api_key
        self._base_url = base_url
        self._model = model
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.lang_out = target_lang  # TranslateConverter 需要此属性
        self._cancel_check = cancel_check
        self._timeout = timeout
        self.total_calls = 0   # 请求翻译的段落数
        self.failed_calls = 0  # 未能返回可用译文的段落数

    def translate(self, text: str) -> str:
        """同步翻译方法，供 TranslateConverter 的线程池调用。
        每次调用都创建独立的事件循环与 AsyncOpenAI 客户端，避免跨循环挂起。"""
        from openai import AsyncOpenAI

        self.total_calls += 1
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)

            client = AsyncOpenAI(
                base_url=self._base_url,
                api_key=self._api_key,
                timeout=self._timeout,
            )
            translator = OpenAITranslator(
                client=client,
                model=self._model,
                cancel_check=self._cancel_check,
            )
            return loop.run_until_complete(
                translator.translate(text, self.source_lang, self.target_lang)
            )
        except Exception as e:
            self.failed_calls += 1
            if isinstance(e, NoUsableTranslationError):
                reason = f"模型未返回译文（思考过程可能占满了输出）：{e}"
                hint = "建议改用非推理模型"
            else:
                reason = f"{type(e).__name__}: {str(e)[:200]}"
                hint = "请检查 AI 引擎配置"
            if self.failed_calls <= 5:
                logger.warning("PDF 段落翻译失败，该段保留原文（%s）：%s", hint, reason)
            else:
                logger.debug("PDF 段落翻译失败，该段保留原文：%s", reason)
            return text
        finally:
            try:
                loop.run_until_complete(loop.shutdown_asyncgens())
            except Exception:
                pass
            loop.close()

    def is_degraded(self) -> bool:
        """失败率过高时返回 True，由调用方中止任务。"""
        if self.total_calls < _DEGRADED_MIN_CALLS:
            return False
        return self.failed_calls / max(self.total_calls, 1) >= _DEGRADED_FAILURE_RATIO

    def degraded_reason(self) -> str:
        return (
            f"AI 翻译失败率过高（{self.failed_calls}/{self.total_calls} 段未返回译文），"
            "已中止以避免输出未翻译的 PDF，请检查 AI 引擎的模型配置后重试"
        )

    def cleanup(self):
        self._api_key = None


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
        api_key: str,
        base_url: str,
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

        # mono：纯译文；dual：原文页 + 译文页逐页交错
        mode = normalize_output_mode(output_mode)

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
            api_key=api_key,
            base_url=base_url,
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
            if translator_adapter.is_degraded():
                raise RuntimeError(translator_adapter.degraded_reason())

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

        if translator_adapter.is_degraded():
            raise RuntimeError(translator_adapter.degraded_reason())
        if translator_adapter.failed_calls:
            logger.warning(
                "PDF 翻译完成，但 %d/%d 段未返回译文（这些段落保留原文）",
                translator_adapter.failed_calls, translator_adapter.total_calls,
            )

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
        translator_adapter.cleanup()

        # 双语对照模式：把原文页与译文页逐页交错合并（原文1 → 译文1 → 原文2 → 译文2 …）
        if mode == "dual":
            await report(99, "合并双语对照页面...")
            output = await loop.run_in_executor(
                _executor, self._merge_dual_pdf, source_pdf_path, output,
            )

        await report(100, "完成")
        return output

    @staticmethod
    def _merge_dual_pdf(original_pdf_path: str, translated_pdf_bytes: bytes) -> bytes:
        """把原文 PDF 与译文 PDF 逐页交错合并成双语对照文件。

        页序：原文 1 → 译文 1 → 原文 2 → 译文 2 …
        译文页数异常（少于/多于原文）时按现有页数尽可能合并，并记录告警。
        """
        src = fitz.open(original_pdf_path)
        try:
            trans = fitz.open(stream=translated_pdf_bytes, filetype="pdf")
            try:
                if trans.page_count != src.page_count:
                    logger.warning(
                        "Dual PDF page count mismatch: original=%d translated=%d",
                        src.page_count, trans.page_count,
                    )

                merged = fitz.open()
                try:
                    for pno in range(max(src.page_count, trans.page_count)):
                        if pno < src.page_count:
                            merged.insert_pdf(src, from_page=pno, to_page=pno)
                        if pno < trans.page_count:
                            merged.insert_pdf(trans, from_page=pno, to_page=pno)

                    try:
                        # 保留原文的标题/作者等元信息；目录页码在交错后不再准确，故不复制
                        metadata = src.metadata
                        if metadata:
                            merged.set_metadata(metadata)
                    except Exception as e:
                        logger.debug("Copy PDF metadata failed: %s", e)

                    return merged.write(deflate=True, garbage=3, use_objstms=1)
                finally:
                    merged.close()
            finally:
                trans.close()
        finally:
            src.close()


pdf_render_service = PdfRenderService()