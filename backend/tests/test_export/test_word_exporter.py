"""Word 导出器单元测试"""

import os
import tempfile
import unittest

from app.export.word_exporter import markdown_to_docx


class TestWordExporter(unittest.TestCase):
    """测试 Markdown → docx 转换"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def _convert(self, md: str, title: str = "Test") -> str:
        """辅助：将 Markdown 转为 docx 并返回路径"""
        out = os.path.join(self.tmpdir, "output.docx")
        return markdown_to_docx(md, out, title=title)

    def test_basic_conversion(self):
        """最基本的 Markdown 转换"""
        path = self._convert("# Hello\n\nWorld paragraph.")
        self.assertTrue(os.path.exists(path))
        self.assertGreater(os.path.getsize(path), 0)

    def test_chinese_content(self):
        """中文内容排版测试"""
        md = (
            "# 中文标题\n\n"
            "这是一段中文正文，用于测试宋体排版效果。\n\n"
            "## 二级标题\n\n"
            "另一段正文内容。"
        )
        path = self._convert(md, title="中文文档")
        self.assertTrue(os.path.exists(path))
        self.assertGreater(os.path.getsize(path), 0)

    def test_headings(self):
        """标题层级渲染测试"""
        md = "# H1\n\n## H2\n\n### H3\n\n正文"
        path = self._convert(md)
        self.assertTrue(os.path.exists(path))

    def test_code_block(self):
        """代码块渲染测试"""
        md = "```python\nprint('hello')\nx = 1 + 2\n```"
        path = self._convert(md)
        self.assertTrue(os.path.exists(path))

    def test_blockquote(self):
        """引用块渲染测试"""
        md = "> This is a blockquote\n\nNormal text."
        path = self._convert(md)
        self.assertTrue(os.path.exists(path))

    def test_bullet_list(self):
        """无序列表渲染测试"""
        md = "- Item 1\n- Item 2\n- Item 3"
        path = self._convert(md)
        self.assertTrue(os.path.exists(path))

    def test_numbered_list(self):
        """有序列表渲染测试"""
        md = "1. First\n2. Second\n3. Third"
        path = self._convert(md)
        self.assertTrue(os.path.exists(path))

    def test_inline_formatting(self):
        """内联格式（粗体/斜体/代码）渲染测试"""
        md = "This is **bold**, *italic*, and `code`."
        path = self._convert(md)
        self.assertTrue(os.path.exists(path))

    def test_horizontal_rule(self):
        """水平分割线渲染测试"""
        md = "Before\n\n---\n\nAfter"
        path = self._convert(md)
        self.assertTrue(os.path.exists(path))

    def test_table(self):
        """表格渲染测试"""
        md = (
            "| Header 1 | Header 2 |\n"
            "|----------|----------|\n"
            "| Cell 1   | Cell 2   |\n"
            "| Cell 3   | Cell 4   |"
        )
        path = self._convert(md)
        self.assertTrue(os.path.exists(path))

    def test_with_toc(self):
        """带目录的文档渲染测试"""
        md = "# Chapter 1\n\nContent\n\n# Chapter 2\n\nMore content"
        path = markdown_to_docx(md, os.path.join(self.tmpdir, "toc.docx"),
                                title="With TOC", include_toc=True)
        self.assertTrue(os.path.exists(path))

    def test_large_document(self):
        """大型文档稳定性测试"""
        lines = []
        for i in range(20):
            lines.append(f"# Chapter {i}\n\nParagraph {i}.\n\n- item {i}.1\n- item {i}.2")
        path = self._convert("\n".join(lines))
        self.assertTrue(os.path.exists(path))


if __name__ == "__main__":
    unittest.main()
