"""Review engine unit tests."""

import json
import unittest
from app.argument.reviewer import (
    ReviewEvent,
    ReviewResult,
    ReviewPointData,
    run_review,
    _format_reviews_for_synthesis,
    _parse_llm_json_object,
)


class TestReviewEvent(unittest.TestCase):
    """Test ReviewEvent dataclass"""

    def test_default_data(self):
        """Default data is empty dict"""
        event = ReviewEvent("progress")
        self.assertEqual(event.data, {})

    def test_with_data(self):
        """Data is accessible"""
        event = ReviewEvent("complete", {"total": 5})
        self.assertEqual(event.data["total"], 5)


class TestReviewResult(unittest.TestCase):
    """Test ReviewResult dataclass"""

    def test_defaults(self):
        """Defaults are empty"""
        result = ReviewResult()
        self.assertEqual(result.points, [])
        self.assertEqual(result.overall_assessment, "")

    def test_with_points(self):
        """Points are stored"""
        points = [ReviewPointData(category="methodology", severity="major", title="Test", description="Desc")]
        result = ReviewResult(points=points, overall_assessment="major")
        self.assertEqual(len(result.points), 1)
        self.assertEqual(result.overall_assessment, "major")


class TestRunReview(unittest.TestCase):
    """Test the review pipeline"""

    def test_empty_text(self):
        """Empty text returns empty result"""
        def mock_llm(prompt, system=""):
            return "[]"

        events = list(run_review(
            "",
            perspectives=["methodology"],
            call_llm=mock_llm,
        ))
        self.assertGreater(len(events), 0)

    def test_review_with_mock(self):
        """Full review pipeline with mock returns points"""
        call_count = [0]

        def mock_llm(prompt, system=""):
            call_count[0] += 1
            if call_count[0] <= 4:
                return json.dumps([
                    {"severity": "major", "title": f"Issue {call_count[0]}",
                     "description": f"Description {call_count[0]}",
                     "suggestion": f"Suggestion {call_count[0]}"},
                ])
            return json.dumps({
                "overall_assessment": "major",
                "strengths": "Well-written paper",
                "top_issues": "- Issue 1\n- Issue 2",
            })

        events = list(run_review(
            "This is a paper about AI.",
            perspectives=["methodology", "experiment"],
            call_llm=mock_llm,
        ))

        review_points = [e for e in events if e.event == "review_point"]
        assessment_events = [e for e in events if e.event == "assessment"]
        complete_events = [e for e in events if e.event == "complete"]

        self.assertGreaterEqual(len(review_points), 1)
        self.assertGreaterEqual(len(complete_events), 1)

    def test_review_with_llm_failure(self):
        """LLM failure during review doesn't crash"""
        def mock_llm(prompt, system=""):
            raise RuntimeError("API failure")

        events = list(run_review(
            "Paper text",
            perspectives=["methodology"],
            call_llm=mock_llm,
        ))
        progress_events = [e for e in events if e.event == "progress"]
        self.assertGreaterEqual(len(progress_events), 1)
        review_points = [e for e in events if e.event == "review_point"]
        self.assertEqual(len(review_points), 0)

    def test_all_four_perspectives_in_review(self):
        """All 4 perspectives can run"""
        def mock_llm(prompt, system=""):
            return json.dumps([
                {"severity": "minor", "title": "Test point", "description": "Desc"}
            ])

        events = list(run_review(
            "Paper text",
            perspectives=["methodology", "experiment", "writing", "devils_advocate"],
            call_llm=mock_llm,
        ))

        review_points = [e for e in events if e.event == "review_point"]
        self.assertEqual(len(review_points), 4)

    def test_synthesis_format(self):
        """Format reviews for synthesis produces correct structure"""
        points = [
            ReviewPointData(category="methodology", severity="major", title="Unclear method",
                            description="Method section is vague", suggestion="Add details"),
            ReviewPointData(category="experiment", severity="minor", title="Missing baseline",
                            description="No baseline comparison"),
        ]
        formatted = _format_reviews_for_synthesis(points)
        self.assertIn("[methodology]", formatted)
        self.assertIn("Unclear method", formatted)
        self.assertIn("[experiment]", formatted)
        self.assertIn("Missing baseline", formatted)
        self.assertIn("Add details", formatted)


class TestParseHelpers(unittest.TestCase):
    """Test JSON parsing"""

    def test_parse_llm_object(self):
        """Parse JSON object"""
        result = _parse_llm_json_object('{"a": 1}')
        self.assertEqual(result, {"a": 1})

    def test_parse_with_code_block(self):
        """Parse JSON in code block"""
        result = _parse_llm_json_object('```json\n{"status": "ok"}\n```')
        self.assertEqual(result, {"status": "ok"})

    def test_parse_invalid(self):
        """Invalid JSON returns empty dict"""
        result = _parse_llm_json_object("not json")
        self.assertEqual(result, {})

    def test_parse_empty(self):
        """Empty string returns empty dict"""
        result = _parse_llm_json_object("")
        self.assertEqual(result, {})


if __name__ == "__main__":
    unittest.main()
