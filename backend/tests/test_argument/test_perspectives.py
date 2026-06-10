"""Perspectives module unit tests."""

import json
import unittest
from app.argument.perspectives import (
    ReviewPointData,
    run_perspective_review,
    run_parallel_review,
    _parse_llm_json_array,
    SYSTEM_PROMPTS,
)


class TestReviewPointData(unittest.TestCase):
    """Test ReviewPointData dataclass"""

    def test_default_values(self):
        """Defaults are applied correctly"""
        point = ReviewPointData(category="methodology", severity="major", title="Test", description="Desc")
        self.assertEqual(point.suggestion, "")
        self.assertEqual(point.anchor_ref, "")

    def test_full_construction(self):
        """All fields can be set"""
        point = ReviewPointData(
            category="experiment",
            severity="critical",
            title="Missing ablation",
            description="No ablation study conducted",
            suggestion="Add ablation experiments",
            anchor_ref="Section 4.2",
        )
        self.assertEqual(point.category, "experiment")
        self.assertEqual(point.severity, "critical")
        self.assertEqual(point.suggestion, "Add ablation experiments")


class TestRunPerspectiveReview(unittest.TestCase):
    """Test single perspective review"""

    def test_mock_llm_returns_points(self):
        """Mock LLM returning review points"""
        def mock_llm(prompt, system=""):
            return json.dumps([
                {"severity": "major", "title": "Unclear methodology",
                 "description": "The method section lacks detail", "suggestion": "Add more details"},
                {"severity": "minor", "title": "Missing reference",
                 "description": "A key reference is missing", "suggestion": ""},
            ])

        points = run_perspective_review(
            "methodology",
            "This is a paper about machine learning.",
            call_llm=mock_llm,
        )

        self.assertEqual(len(points), 2)
        self.assertEqual(points[0].category, "methodology")
        self.assertEqual(points[0].severity, "major")
        self.assertEqual(points[1].suggestion, "")

    def test_mock_llm_empty_result(self):
        """Empty result from LLM produces no points"""
        def mock_llm(prompt, system=""):
            return "[]"

        points = run_perspective_review("methodology", "Some text", call_llm=mock_llm)
        self.assertEqual(len(points), 0)

    def test_llm_error_returns_empty(self):
        """LLM failure returns empty list gracefully"""
        def mock_llm(prompt, system=""):
            raise RuntimeError("API error")

        points = run_perspective_review("experiment", "Some text", call_llm=mock_llm)
        self.assertEqual(len(points), 0)

    def test_invalid_category_still_works(self):
        """Unknown category still runs (no system prompt but still works)"""
        def mock_llm(prompt, system=""):
            return "[]"

        points = run_perspective_review("unknown_category", "text", call_llm=mock_llm)
        self.assertEqual(len(points), 0)


class TestRunParallelReview(unittest.TestCase):
    """Test parallel multi-perspective review"""

    def test_all_four_perspectives(self):
        """All 4 perspectives produce results"""
        call_count = [0]

        def mock_llm(prompt, system=""):
            call_count[0] += 1
            return json.dumps([
                {"severity": "minor", "title": f"Point from call {call_count[0]}",
                 "description": "Description"}
            ])

        results = run_parallel_review(
            "Paper text here",
            perspectives=["methodology", "experiment", "writing", "devils_advocate"],
            call_llm=mock_llm,
        )

        self.assertEqual(len(results), 4)
        for category in ["methodology", "experiment", "writing", "devils_advocate"]:
            self.assertIn(category, results)
            self.assertGreaterEqual(len(results[category]), 1)

    def test_filter_invalid_perspectives(self):
        """Invalid perspective names are filtered out"""
        def mock_llm(prompt, system=""):
            return "[]"

        results = run_parallel_review(
            "text",
            ["methodology", "nonexistent_perspective"],
            call_llm=mock_llm,
        )
        self.assertIn("methodology", results)
        # nonexistent should be filtered out
        self.assertNotIn("nonexistent_perspective", results)

    def test_empty_perspectives_list(self):
        """Empty perspectives list returns empty results"""
        def mock_llm(prompt, system=""):
            return "[]"

        results = run_parallel_review("text", [], call_llm=mock_llm)
        self.assertEqual(len(results), 0)


class TestSystemPrompts(unittest.TestCase):
    """System prompts are well-formed"""

    def test_all_perspectives_have_prompts(self):
        """All 4 perspective system prompts are defined"""
        self.assertIn("methodology", SYSTEM_PROMPTS)
        self.assertIn("experiment", SYSTEM_PROMPTS)
        self.assertIn("writing", SYSTEM_PROMPTS)
        self.assertIn("devils_advocate", SYSTEM_PROMPTS)

    def test_prompts_are_non_empty(self):
        """All system prompts have content"""
        for name, prompt in SYSTEM_PROMPTS.items():
            with self.subTest(perspective=name):
                self.assertGreater(len(prompt), 50)


class TestParseHelpers(unittest.TestCase):
    """Test JSON parsing helpers"""

    def test_parse_empty(self):
        """Empty string returns empty list"""
        self.assertEqual(_parse_llm_json_array(""), [])

    def test_parse_code_block(self):
        """Parse JSON in markdown code block"""
        result = _parse_llm_json_array('```json\n[{"a": 1}]\n```')
        self.assertEqual(result, [{"a": 1}])

    def test_parse_plain_array(self):
        """Parse plain JSON array"""
        result = _parse_llm_json_array('[1, 2, 3]')
        self.assertEqual(result, [1, 2, 3])

    def test_parse_invalid(self):
        """Invalid JSON returns empty"""
        self.assertEqual(_parse_llm_json_array("{broken"), [])


if __name__ == "__main__":
    unittest.main()
