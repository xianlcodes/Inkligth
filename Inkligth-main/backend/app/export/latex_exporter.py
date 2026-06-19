"""
LaTeX / PDF 导出器
将 Markdown 转换为 LaTeX (.tex) 并可选编译为 PDF。

依赖:
    - Pandoc (>= 2.0): Markdown → LaTeX 转换
    - latexmk (可选): LaTeX → PDF 编译
    - Jinja2: LaTeX 模板渲染
"""

import os
import re
import logging
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

logger = logging.getLogger(__name__)

# ── 模板目录 ──
TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"


def _get_template_engine() -> Environment:
    """获取 Jinja2 模板引擎"""
    return Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
        variable_start_string="[[",
        variable_end_string="]]",
    )


def _escape_latex(text: str) -> str:
    """转义 LaTeX 特殊字符"""
    replacements = {
        "\\": "\\textbackslash{}",
        "&": "\\&",
        "%": "\\%",
        "$": "\\$",
        "#": "\\#",
        "_": "\\_",
        "{": "\\{",
        "}": "\\}",
        "~": "\\textasciitilde{}",
        "^": "\\textasciicircum{}",
    }
    for char, escaped in replacements.items():
        text = text.replace(char, escaped)
    return text


def _pandoc_available() -> bool:
    """检查 Pandoc 是否可用"""
    try:
        subprocess.run(["pandoc", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def _compiler_available() -> tuple[bool, str]:
    """检查 LaTeX 编译器是否可用，返回 (可用, 编译器名称)"""
    for compiler in ["tectonic", "latexmk", "pdflatex"]:
        try:
            subprocess.run([compiler, "--version"], capture_output=True, check=True)
            return True, compiler
        except (subprocess.SubprocessError, FileNotFoundError):
            continue
    return False, ""


def markdown_to_latex(
    markdown_text: str,
    output_path: str,
    *,
    template: str = "generic",
    title: str = "",
    authors: list[str] = None,
    abstract: str = "",
) -> str:
    """
    将 Markdown 文本转换为 LaTeX (.tex) 文件。

    Args:
        markdown_text: Markdown 源文本
        output_path: 输出 .tex 文件路径
        template: 模板名称 (ieee|acm|neurips|lncs|generic)
        title: 文档标题
        authors: 作者列表
        abstract: 摘要

    Returns:
        输出文件路径

    Raises:
        NotImplementedError: Pandoc 不可用时抛出
    """
    if not _pandoc_available():
        raise NotImplementedError(
            "Pandoc is required for LaTeX export. "
            "Install it with: apt-get install pandoc"
        )

    authors = authors or []

    # 第一步：用 Pandoc 将 Markdown 转为基础 LaTeX
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, encoding="utf-8"
    ) as f:
        f.write(markdown_text)
        md_path = f.name

    try:
        result = subprocess.run(
            [
                "pandoc",
                md_path,
                "--to", "latex",
                "--wrap", "preserve",
                "--output", output_path,
                "--pdf-engine-opt=-output-directory=" + str(Path(output_path).parent),
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            logger.warning("Pandoc stderr: %s", result.stderr[:500])
            # 如果失败，尝试无复杂选项
            result = subprocess.run(
                ["pandoc", md_path, "--to", "latex", "--output", output_path],
                capture_output=True, text=True, timeout=60,
            )
            if result.returncode != 0:
                raise RuntimeError(f"Pandoc conversion failed: {result.stderr[:500]}")

        # 第二步：读取 Pandoc 输出，包装为模板文档
        with open(output_path, "r", encoding="utf-8") as f:
            body_content = f.read()

    finally:
        os.unlink(md_path)

    # 第三步：用 Jinja2 模板包装
    env = _get_template_engine()
    tmpl_name = f"{template}.tex.j2"

    try:
        tmpl = env.get_template(tmpl_name)
    except Exception:
        logger.warning("Template '%s' not found, falling back to generic", tmpl_name)
        tmpl = env.get_template("generic.tex.j2")

    rendered = tmpl.render(
        title=_escape_latex(title) if title else "Untitled",
        authors=[_escape_latex(a) for a in authors],
        abstract=_escape_latex(abstract) if abstract else "",
        body=body_content,
    )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(rendered)

    logger.info("LaTeX file saved: %s", output_path)
    return output_path


def compile_latex_to_pdf(
    tex_path: str,
    output_dir: str,
) -> tuple[bool, str]:
    """
    编译 LaTeX 文件为 PDF。

    编译策略:
        1. tectonic（单命令，自动下载宏包）
        2. latexmk -xelatex（完整 TeX Live）
        3. pdflatex × 2（最小环境）

    Args:
        tex_path: .tex 文件路径
        output_dir: 输出目录

    Returns:
        (成功与否, 日志/PDF路径)
    """
    available, compiler = _compiler_available()
    if not available:
        raise NotImplementedError(
            "No LaTeX compiler found. Install tectonic, latexmk, or pdflatex."
        )

    tex_path = os.path.abspath(tex_path)
    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    log_lines = []

    if compiler == "tectonic":
        logger.info("Compiling with tectonic: %s", tex_path)
        try:
            result = subprocess.run(
                ["tectonic", "-X", "compile", tex_path, "--outdir", output_dir],
                capture_output=True, text=True, timeout=120,
            )
            log_lines.append(result.stdout)
            if result.stderr:
                log_lines.append("STDERR: " + result.stderr)

            pdf_path = os.path.join(output_dir, Path(tex_path).stem + ".pdf")
            if result.returncode == 0 and os.path.exists(pdf_path):
                return True, pdf_path
            log_lines.append(f"Tectonic exit code: {result.returncode}")
        except subprocess.TimeoutExpired:
            log_lines.append("Tectonic timed out after 120s")

    if compiler in ("latexmk", "pdflatex"):
        logger.info("Compiling with latexmk: %s", tex_path)
        try:
            result = subprocess.run(
                [
                    "latexmk",
                    "-xelatex",
                    "-output-directory=" + output_dir,
                    "-interaction=nonstopmode",
                    "-halt-on-error",
                    tex_path,
                ],
                capture_output=True, text=True, timeout=120,
            )
            log_lines.append(result.stdout[:2000])
            if result.stderr:
                log_lines.append("STDERR: " + result.stderr[:1000])

            pdf_path = os.path.join(output_dir, Path(tex_path).stem + ".pdf")
            if os.path.exists(pdf_path):
                return True, pdf_path
            log_lines.append("latexmk produced no PDF")
        except subprocess.TimeoutExpired:
            log_lines.append("latexmk timed out after 120s")

    # 最后尝试简单的 pdflatex × 2
    logger.info("Falling back to pdflatex × 2: %s", tex_path)
    try:
        for _ in range(2):
            result = subprocess.run(
                [
                    "pdflatex",
                    "-output-directory=" + output_dir,
                    "-interaction=nonstopmode",
                    tex_path,
                ],
                capture_output=True, text=True, timeout=60,
            )
            log_lines.append(result.stdout[-500:])  # 只保留最后部分

        pdf_path = os.path.join(output_dir, Path(tex_path).stem + ".pdf")
        if os.path.exists(pdf_path):
            return True, pdf_path
    except subprocess.TimeoutExpired:
        log_lines.append("pdflatex timed out")

    return False, "\n".join(log_lines)


def markdown_to_pdf(
    markdown_text: str,
    output_path: str,
    *,
    template: str = "generic",
    title: str = "",
    authors: list[str] = None,
    abstract: str = "",
) -> tuple[bool, str, str]:
    """
    一站式：Markdown → LaTeX → PDF。

    Args:
        参数同 markdown_to_latex()

    Returns:
        (成功与否, PDF路径/日志, 编译日志)
    """
    authors = authors or []
    # 先生成 .tex 文件
    tex_dir = tempfile.mkdtemp()
    tex_filename = "document.tex"
    tex_path = os.path.join(tex_dir, tex_filename)

    try:
        markdown_to_latex(
            markdown_text,
            tex_path,
            template=template,
            title=title,
            authors=authors,
            abstract=abstract,
        )

        # 编译 PDF
        success, pdf_or_log = compile_latex_to_pdf(tex_path, tex_dir)

        if success:
            # 复制到目标路径
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            shutil.copy2(pdf_or_log, output_path)
            logger.info("PDF saved: %s", output_path)
            return True, output_path, ""
        else:
            return False, "", pdf_or_log

    except Exception:
        logger.exception("PDF compilation failed")
        raise
    finally:
        shutil.rmtree(tex_dir, ignore_errors=True)
