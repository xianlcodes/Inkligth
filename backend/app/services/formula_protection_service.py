import logging
import re
import unicodedata

logger = logging.getLogger(__name__)

LATEX_FONT_PATTERNS = re.compile(
    r"\\(CM[^R]|MS[AB]M|XY|MT|BL|RM|EU|LA|RS|LINE|Logo|"
    r"MSAM|MSBM|EUF|EUS|EUR|CMBSY|CMSY|CMEX|MTEX|MTMI|"
    r"CMR|CMMI|CMTI|CMSS|CMTT|CMCSC)",
    re.IGNORECASE,
)

LATEX_INLINE_MATH = re.compile(
    r"(?<!\\)\$(?!\$)(.+?)(?<!\\)\$(?!\$)"
)

LATEX_DISPLAY_MATH = re.compile(
    r"(?<!\\)\$\$(.+?)(?<!\\)\$\$|\\\[(.+?)\\\]",
    re.DOTALL,
)

LATEX_MATH_ENV = re.compile(
    r"\\begin\{(equation|align|gather|multline|eqnarray|matrix|pmatrix|bmatrix|Bmatrix|vmatrix|Vmatrix|cases|array)(\*?)\}(.+?)\\end\{\1\2\}",
    re.DOTALL,
)

INLINE_MATH_PAREN = re.compile(
    r"\\\((.+?)\\\)"
)

SUPERSCRIPT_PATTERN = re.compile(r"[a-zA-Z0-9](\^\{[^}]+\})")
SUBSCRIPT_PATTERN = re.compile(r"[a-zA-Z0-9](\_\{[^}]+\})")
FRAC_PATTERN = re.compile(r"\\frac\{[^}]*\}\{[^}]*\}")
SQRT_PATTERN = re.compile(r"\\sqrt(\[[^\]]*\])?\{[^}]*\}")
SUM_INT_PATTERN = re.compile(r"\\(sum|int|prod|lim|inf|sup|max|min)(\b|[_^])")
GREEK_PATTERN = re.compile(r"\\(alpha|beta|gamma|delta|epsilon|zeta|eta|theta|iota|kappa|lambda|mu|nu|xi|omicron|pi|rho|sigma|tau|upsilon|phi|chi|psi|omega|"
                           r"Alpha|Beta|Gamma|Delta|Epsilon|Zeta|Eta|Theta|Iota|Kappa|Lambda|Mu|Nu|Xi|Omicron|Pi|Rho|Sigma|Tau|Upsilon|Phi|Chi|Psi|Omega)")

FORMULA_INDICATOR_PATTERNS = [
    FRAC_PATTERN,
    SQRT_PATTERN,
    SUM_INT_PATTERN,
    GREEK_PATTERN,
    SUPERSCRIPT_PATTERN,
    SUBSCRIPT_PATTERN,
]

MATH_UNICODE_CATEGORIES = frozenset({"Sm", "Sk", "Lm", "Mn"})

GREEK_UNICODE_RANGES = [
    (0x0370, 0x03FF),
    (0x1F00, 0x1FFF),
]

MATH_ALPHANUM_RANGE = (0x1D400, 0x1D7FF)


def has_pdf_math_indicators(text: str) -> bool:
    if LATEX_FONT_PATTERNS.search(text):
        return True
    for ch in text:
        cat = unicodedata.category(ch)
        if cat in MATH_UNICODE_CATEGORIES:
            return True
        cp = ord(ch)
        for lo, hi in GREEK_UNICODE_RANGES:
            if lo <= cp <= hi:
                return True
        if MATH_ALPHANUM_RANGE[0] <= cp <= MATH_ALPHANUM_RANGE[1]:
            return True
    return False


class FormulaProtectionService:

    PLACEHOLDER_PREFIX = "{v"
    PLACEHOLDER_SUFFIX = "}"
    PLACEHOLDER_REGEX = re.compile(r"\{v(\d+)\}")

    def __init__(self):
        self.formula_store: dict[str, str] = {}
        self._counter = 0

    def reset(self):
        self.formula_store.clear()
        self._counter = 0

    def _next_placeholder(self) -> str:
        self._counter += 1
        return f"{self.PLACEHOLDER_PREFIX}{self._counter - 1}{self.PLACEHOLDER_SUFFIX}"

    def protect_text(self, text: str) -> str:
        if not text:
            return text

        protected = text

        protected, _ = self._protect_sections(
            protected, LATEX_DISPLAY_MATH, "display_math"
        )
        protected, _ = self._protect_sections(
            protected, LATEX_MATH_ENV, "math_env"
        )
        protected, _ = self._protect_sections(
            protected, INLINE_MATH_PAREN, "inline_paren"
        )
        protected, _ = self._protect_sections(
            protected, LATEX_INLINE_MATH, "inline_dollar"
        )

        protected = self._protect_unicode_math(protected)

        protected = self._protect_standalone_macros(protected)

        return protected

    def _protect_sections(
        self, text: str, pattern: re.Pattern, section_type: str
    ) -> tuple[str, int]:
        count = 0
        matches = list(pattern.finditer(text))
        result = text
        for match in reversed(matches):
            formula_text = match.group(0)
            placeholder = self._next_placeholder()
            self.formula_store[placeholder] = formula_text
            result = result[:match.start()] + placeholder + result[match.end():]
            count += 1
        if count > 0:
            logger.debug("Protected %d %s formula sections", count, section_type)
        return result, count

    def _protect_unicode_math(self, text: str) -> str:
        segments = self._find_math_spans(text)
        if not segments:
            return text

        result = []
        last_end = 0
        for start, end in segments:
            result.append(text[last_end:start])
            span_text = text[start:end]
            if span_text.strip():
                placeholder = self._next_placeholder()
                self.formula_store[placeholder] = span_text
                result.append(placeholder)
            else:
                result.append(span_text)
            last_end = end
        result.append(text[last_end:])
        return "".join(result)

    def _find_math_spans(self, text: str) -> list[tuple[int, int]]:
        spans = []
        i = 0
        n = len(text)

        while i < n:
            ch = text[i]
            if self._is_math_char(ch):
                start = i
                i += 1
                while i < n and self._is_math_char(text[i]):
                    i += 1
                spans.append((start, i))
            else:
                i += 1
        return spans

    @staticmethod
    def _is_math_char(ch: str) -> bool:
        cat = unicodedata.category(ch)
        if cat in MATH_UNICODE_CATEGORIES:
            return True
        cp = ord(ch)
        for lo, hi in GREEK_UNICODE_RANGES:
            if lo <= cp <= hi:
                return True
        if MATH_ALPHANUM_RANGE[0] <= cp <= MATH_ALPHANUM_RANGE[1]:
            return True
        return False

    def _protect_standalone_macros(self, text: str) -> str:
        patterns_in_order = [
            ("\\frac", FRAC_PATTERN),
            ("\\sqrt", SQRT_PATTERN),
            ("\\sum", SUM_INT_PATTERN),
            ("\\int", SUM_INT_PATTERN),
            ("\\prod", SUM_INT_PATTERN),
            ("\\lim", SUM_INT_PATTERN),
            ("\\alpha", GREEK_PATTERN),
            ("\\beta", GREEK_PATTERN),
        ]
        seen_prefixes: set[str] = set()
        for prefix, pattern in patterns_in_order:
            if prefix in seen_prefixes:
                continue
            seen_prefixes.add(prefix)
            matches = list(pattern.finditer(text))
            for match in reversed(matches):
                formula_text = match.group(0)
                if formula_text in self.formula_store.values():
                    continue
                placeholder = self._next_placeholder()
                self.formula_store[placeholder] = formula_text
                text = text[:match.start()] + placeholder + text[match.end():]
        return text

    def restore_text(self, translated: str) -> str:
        if not translated:
            return translated

        def replacer(match):
            return self.formula_store.get(match.group(0), match.group(0))

        result = self.PLACEHOLDER_REGEX.sub(replacer, translated)

        ex_placeholder = re.compile(r"\{\\?v(\d+)\}")
        result = ex_placeholder.sub(
            lambda m: self.formula_store.get(f"{{v{m.group(1)}}}", m.group(0)),
            result,
        )

        return result

    def protect_paragraphs(self, paragraphs: list[str]) -> list[str]:
        self.reset()
        return [self.protect_text(p) for p in paragraphs]

    def restore_paragraphs(self, translated_paragraphs: list[str]) -> list[str]:
        return [self.restore_text(p) for p in translated_paragraphs]


formula_service = FormulaProtectionService()


def detect_formula_features(text: str) -> dict:
    features = {
        "has_display_math": bool(LATEX_DISPLAY_MATH.search(text)),
        "has_inline_dollar": bool(LATEX_INLINE_MATH.search(text)),
        "has_math_env": bool(LATEX_MATH_ENV.search(text)),
        "has_frac": bool(FRAC_PATTERN.search(text)),
        "has_sqrt": bool(SQRT_PATTERN.search(text)),
        "has_sum_int": bool(SUM_INT_PATTERN.search(text)),
        "has_greek_command": bool(GREEK_PATTERN.search(text)),
        "has_unicode_math": False,
        "has_latex_font": bool(LATEX_FONT_PATTERNS.search(text)),
        "total_formula_count": 0,
    }

    for ch in text:
        cat = unicodedata.category(ch)
        if cat in MATH_UNICODE_CATEGORIES:
            features["has_unicode_math"] = True
            break
    if not features["has_unicode_math"]:
        for ch in text:
            cp = ord(ch)
            for lo, hi in GREEK_UNICODE_RANGES:
                if lo <= cp <= hi:
                    features["has_unicode_math"] = True
                    break
            if features["has_unicode_math"]:
                break

    svc = FormulaProtectionService()
    svc.protect_text(text)
    features["total_formula_count"] = len(svc.formula_store)

    return features