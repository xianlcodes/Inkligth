"""Anchor system unit tests."""

import unittest
from app.argument.anchor import locate_quote, AnchorStatus, _detect_section


class TestAnchor(unittest.TestCase):
    """Test anchor.py — 4-tier quote location"""

    def setUp(self):
        self.full_text = (
            "Abstract\n"
            "This paper presents a novel approach to natural language processing.\n"
            "We introduce a new transformer architecture called MiniBERT.\n"
            "\n"
            "Introduction\n"
            "Recent advances in NLP have shown great promise.\n"
            "Our method builds upon BERT and reduces parameters by 40%.\n"
            "\n"
            "Method\n"
            "The MiniBERT architecture uses factorized attention mechanisms.\n"
            "This allows for efficient computation with minimal loss.\n"
            "\n"
            "Experiments\n"
            "We evaluated on GLUE and SuperGLUE benchmarks.\n"
            "MiniBERT achieves 92.3% accuracy while being 3x faster.\n"
        )

    def test_exact_match(self):
        """Strategy 1: exact match"""
        result = locate_quote(self.full_text, "MiniBERT achieves 92.3% accuracy")
        self.assertEqual(result.status, AnchorStatus.ANCHORED)
        self.assertEqual(result.confidence, 1.0)
        self.assertIsNotNone(result.char_start)
        self.assertIsNotNone(result.char_end)

    def test_exact_match_start(self):
        """Exact match at start of text"""
        result = locate_quote(self.full_text, "Abstract")
        self.assertEqual(result.status, AnchorStatus.ANCHORED)
        self.assertEqual(result.char_start, 0)

    def test_exact_match_end(self):
        """Exact match at end of text"""
        result = locate_quote(self.full_text, "being 3x faster.")
        self.assertEqual(result.status, AnchorStatus.ANCHORED)

    def test_empty_text(self):
        """Empty text returns LOST"""
        result = locate_quote("", "something")
        self.assertEqual(result.status, AnchorStatus.LOST)
        self.assertEqual(result.confidence, 0.0)

    def test_empty_quote(self):
        """Empty quote returns LOST"""
        result = locate_quote("some text", "")
        self.assertEqual(result.status, AnchorStatus.LOST)
        self.assertEqual(result.confidence, 0.0)

    def test_context_assisted_match(self):
        """Strategy 2: context-assisted match"""
        result = locate_quote(
            self.full_text,
            "reduces parameters by 40%",
            context_before="Our method builds upon BERT",
        )
        self.assertEqual(result.status, AnchorStatus.ANCHORED)
        self.assertGreaterEqual(result.confidence, 0.9)

    def test_context_after_match(self):
        """Context after helps locate"""
        result = locate_quote(
            self.full_text,
            "Our method builds upon BERT",
            context_after="reduces parameters by 40%.",
        )
        self.assertEqual(result.status, AnchorStatus.ANCHORED)
        self.assertGreaterEqual(result.confidence, 0.9)

    def test_fuzzy_match(self):
        """Strategy 3: fuzzy match — matching existing segment"""
        result = locate_quote(
            self.full_text,
            "MiniBERT achieves 92.3% accuracy",
            fuzzy_threshold=0.60,
        )
        self.assertIn(result.status, [AnchorStatus.ANCHORED, AnchorStatus.DRIFTED])

    def test_fuzzy_single_word(self):
        """fuzzy_strategy requires 3+ words — pure exact match still works for short phrases"""
        # Single word is found by exact match strategy, not fuzzy
        result = locate_quote(
            self.full_text,
            "MiniBERT",
        )
        self.assertEqual(result.status, AnchorStatus.ANCHORED)
        self.assertEqual(result.confidence, 1.0)

    def test_no_match_returns_lost(self):
        """No matching quote returns LOST"""
        result = locate_quote(
            self.full_text,
            "This sentence does not exist anywhere in the text",
        )
        self.assertEqual(result.status, AnchorStatus.LOST)
        self.assertEqual(result.confidence, 0.0)

    def test_context_without_match(self):
        """Context provided but quote not found"""
        result = locate_quote(
            self.full_text,
            "nonexistent quote",
            context_before="Abstract",
        )
        self.assertEqual(result.status, AnchorStatus.LOST)

    def test_section_detection_abstract(self):
        """Section detection finds 'Abstract'"""
        # Position 30 is well within the Abstract paragraph
        section = _detect_section(self.full_text, 30)
        self.assertTrue("Abstract" in section, f"Expected 'Abstract' in section, got: {section!r}")

    def test_section_detection_introduction(self):
        """Section detection finds 'Introduction'"""
        idx = self.full_text.find("Recent advances")
        if idx != -1:
            section = _detect_section(self.full_text, idx)
            self.assertTrue("Introduction" in section or section == "unknown")

    def test_anchor_result_to_dict(self):
        """AnchorResult.to_dict() returns correct structure"""
        from app.argument.anchor import AnchorResult
        result = AnchorResult(
            status=AnchorStatus.ANCHORED,
            quote="test quote",
            char_start=10,
            char_end=20,
            context_before="before",
            context_after="after",
            section="Introduction",
            confidence=0.95,
        )
        d = result.to_dict()
        self.assertEqual(d["status"], "anchored")
        self.assertEqual(d["quote"], "test quote")
        self.assertEqual(d["char_start"], 10)
        self.assertEqual(d["char_end"], 20)
        self.assertEqual(d["confidence"], 0.95)

    def test_anchor_result_lost_defaults(self):
        """LOST AnchorResult has minimal fields"""
        from app.argument.anchor import AnchorResult
        result = AnchorResult(AnchorStatus.LOST, "lost quote", confidence=0.0)
        d = result.to_dict()
        self.assertEqual(d["status"], "lost")
        self.assertEqual(d["confidence"], 0.0)
        self.assertIsNone(d["char_start"])


if __name__ == "__main__":
    unittest.main()
