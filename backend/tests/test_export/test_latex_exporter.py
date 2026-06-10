"""LaTeX/PDF 导出器单元测试"""

import os
import tempfile
import unittest


class TestLatexExporter(unittest.TestCase):
    """测试 Markdown → LaTeX 转换"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.sample_md = (
            "# Introduction\n\n"
            "This is a test paper.\n\n"
            "## Methods\n\n"
            "We used a novel approach.\n\n"
            "## Results\n\n"
            "The results are promising.\n\n"
            "## Conclusion\n\n"
            "We have demonstrated great results."
        )

    def test_latex_basic_conversion(self):
        """最基本的 LaTeX 转换"""
        from app.export.latex_exporter import markdown_to_latex
        out = os.path.join(self.tmpdir, "test.tex")
        path = markdown_to_latex(self.sample_md, out, title="Test Paper")
        self.assertTrue(os.path.exists(path))
        self.assertGreater(os.path.getsize(path), 0)
        with open(path) as f:
            content = f.read()
        self.assertIn("\\title{Test Paper}", content)
        self.assertIn("\\maketitle", content)

    def test_latex_with_template(self):
        """所有模板生成测试"""
        from app.export.latex_exporter import markdown_to_latex
        for tmpl in ["generic", "ieee", "acm", "lncs", "neurips"]:
            out = os.path.join(self.tmpdir, f"test_{tmpl}.tex")
            path = markdown_to_latex(
                self.sample_md, out,
                template=tmpl,
                title=f"{tmpl.upper()} Paper",
                authors=["Author A"],
                abstract="Test abstract.",
            )
            self.assertTrue(os.path.exists(path), f"Template {tmpl} failed")

    def test_latex_with_authors(self):
        """作者列表渲染"""
        from app.export.latex_exporter import markdown_to_latex
        out = os.path.join(self.tmpdir, "authors.tex")
        path = markdown_to_latex(
            self.sample_md, out,
            title="Multi-Author Paper",
            authors=["Alice", "Bob", "Charlie"],
        )
        self.assertTrue(os.path.exists(path))

    def test_latex_with_abstract(self):
        """摘要渲染"""
        from app.export.latex_exporter import markdown_to_latex
        out = os.path.join(self.tmpdir, "abstract.tex")
        path = markdown_to_latex(
            self.sample_md, out,
            title="Paper with Abstract",
            abstract="This is the abstract content.",
        )
        self.assertTrue(os.path.exists(path))
        with open(path) as f:
            content = f.read()
        self.assertIn("abstract", content)

    def test_latex_special_chars(self):
        """特殊字符转义"""
        from app.export.latex_exporter import markdown_to_latex
        md = "# Test\n\nSpecial chars: & % $ # _ ~ ^"
        out = os.path.join(self.tmpdir, "special.tex")
        path = markdown_to_latex(md, out, title="Special Chars")
        self.assertTrue(os.path.exists(path))

    def test_latex_table(self):
        """表格渲染测试"""
        from app.export.latex_exporter import markdown_to_latex
        md = (
            "| Header 1 | Header 2 |\n"
            "|----------|----------|\n"
            "| Cell 1   | Cell 2   |"
        )
        out = os.path.join(self.tmpdir, "table.tex")
        path = markdown_to_latex(md, out, title="Table Test")
        self.assertTrue(os.path.exists(path))


class TestPdfCompiler(unittest.TestCase):
    """测试 LaTeX → PDF 编译"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def test_pdf_compile(self):
        """PDF 编译测试（需要 latexmk）"""
        from app.export.latex_exporter import markdown_to_latex, compile_latex_to_pdf

        md = "# Hello\n\nPDF test document."
        tex_path = os.path.join(self.tmpdir, "test.tex")
        markdown_to_latex(md, tex_path, title="PDF Test")

        success, pdf_or_log = compile_latex_to_pdf(tex_path, self.tmpdir)
        self.assertTrue(success, f"PDF compilation failed: {pdf_or_log[:200] if not success else ''}")
        self.assertTrue(os.path.exists(pdf_or_log))
        self.assertGreater(os.path.getsize(pdf_or_log), 0)

    def test_one_step_pipeline(self):
        """一站式 Markdown → PDF"""
        from app.export.latex_exporter import markdown_to_pdf
        md = "# Pipeline Test\n\nTesting the full pipeline."
        out = os.path.join(self.tmpdir, "final.pdf")
        success, path, log = markdown_to_pdf(md, out, title="Pipeline Test")
        self.assertTrue(success, f"Pipeline failed: {log[:200] if not success else ''}")
        self.assertTrue(os.path.exists(path))


if __name__ == "__main__":
    unittest.main()
