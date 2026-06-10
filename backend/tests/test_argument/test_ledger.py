"""Ledger dual-LLM pipeline unit tests."""

import json
import unittest
from app.argument.ledger import (
    ExtractedPromise,
    LedgerBuildEvent,
    extract_promises,
    check_discharge,
    anchor_quotes,
    run_ledger_build,
    _extract_section,
    _parse_llm_json_array,
    _parse_llm_json_object,
)


class TestLedgerExtractPromises(unittest.TestCase):
    """Test promise extraction from full text"""

    def test_extract_empty_text(self):
        """Empty text yields no promises"""
        events = list(extract_promises(""))
        self.assertTrue(all(e.event != "promise_extracted" for e in events))

    def test_extract_no_abstract_intro(self):
        """Text without abstract/intro yields no promises"""
        events = list(extract_promises("Some random text without sections."))
        self.assertTrue(all(e.event != "promise_extracted" for e in events))

    def test_extract_with_mock_llm(self):
        """Mock LLM returning JSON array produces promises"""
        def mock_llm(prompt, system=""):
            return json.dumps([
                {"claim_text": "We propose a novel method", "severity": "error", "section_hint": "Abstract"},
                {"claim_text": "Our approach achieves 95% accuracy", "severity": "warning", "section_hint": "Introduction"},
            ])

        text = "Abstract\nWe propose a novel method.\nIntroduction\nOur approach achieves 95% accuracy."
        events = list(extract_promises(text, call_llm=mock_llm))

        extracted = [e for e in events if e.event == "promise_extracted"]
        self.assertEqual(len(extracted), 2)
        self.assertEqual(extracted[0].data["claim_text"], "We propose a novel method")
        self.assertEqual(extracted[0].data["severity"], "error")

    def test_extract_llm_error(self):
        """LLM failure yields no promises"""
        def mock_llm(prompt, system=""):
            raise RuntimeError("LLM unavailable")

        text = "Abstract\nSomething."
        events = list(extract_promises(text, call_llm=mock_llm))
        self.assertTrue(all(e.event != "promise_extracted" for e in events))
        self.assertTrue(any(e.event == "error" for e in events))


class TestLedgerCheckDischarge(unittest.TestCase):
    """Test discharge checking"""

    def test_check_empty_promises(self):
        """Empty promises list produces no checked events"""
        events = list(check_discharge("some text", []))
        self.assertTrue(all(e.event != "promise_checked" for e in events))

    def test_check_with_mock_llm(self):
        """Mock LLM returning discharge status"""
        def mock_llm(prompt, system=""):
            return json.dumps({
                "status": "paid",
                "discharge_text": "Our method achieves 95% accuracy on GLUE.",
                "reason": "Explicitly stated in Experiments",
            })

        promises = [ExtractedPromise(claim_text="We achieve 95% accuracy")]
        text = "Experiments\nOur method achieves 95% accuracy on GLUE."
        events = list(check_discharge(text, promises, call_llm=mock_llm))

        checked = [e for e in events if e.event == "promise_checked"]
        self.assertGreaterEqual(len(checked), 1)
        # The original promise should be updated
        self.assertEqual(promises[0].status, "paid")

    def test_check_multiple_promises(self):
        """Multiple promises produce progress events"""
        def mock_llm(prompt, system=""):
            return json.dumps({"status": "unpaid", "discharge_text": "", "reason": "Not found"})

        promises = [
            ExtractedPromise(claim_text="Promise A"),
            ExtractedPromise(claim_text="Promise B"),
            ExtractedPromise(claim_text="Promise C"),
        ]
        events = list(check_discharge("some text", promises, call_llm=mock_llm))

        progress_events = [e for e in events if e.event == "progress" and e.data.get("step") == "check"]
        self.assertGreaterEqual(len(progress_events), 1)


class TestLedgerAnchorQuotes(unittest.TestCase):
    """Test anchor step"""

    def test_anchor_all_promises(self):
        """Each promise with claim_text produces anchored event"""
        promises = [
            ExtractedPromise(claim_text="novel approach", status="unpaid"),
            ExtractedPromise(claim_text="95% accuracy", status="paid", discharge_text="95% accuracy on GLUE"),
        ]
        text = "Abstract\nWe propose a novel approach.\nExperiments\n95% accuracy on GLUE."
        events = list(anchor_quotes(text, promises))

        anchored = [e for e in events if e.event == "anchored"]
        self.assertGreaterEqual(len(anchored), 1)

    def test_anchor_empty_claims(self):
        """Promises without claim text are skipped"""
        promises = [ExtractedPromise(claim_text="", status="unpaid")]
        events = list(anchor_quotes("some text", promises))
        anchored = [e for e in events if e.event == "anchored"]
        self.assertEqual(len(anchored), 0)


class TestLedgerFullPipeline(unittest.TestCase):
    """Test the complete run_ledger_build pipeline"""

    def test_full_pipeline_empty_text(self):
        """Empty text produces complete event with 0 promises"""
        events = []
        result = None
        for event in run_ledger_build(""):
            events.append(event)
            if event.event == "complete":
                result = event.data

        self.assertIsNotNone(result)
        self.assertEqual(result.get("total"), 0)

    def test_full_pipeline_with_mock(self):
        """Full pipeline with mock LLM produces complete results"""
        call_count = [0]

        def mock_llm(prompt, system=""):
            call_count[0] += 1
            if call_count[0] == 1:
                # Extract step
                return json.dumps([
                    {"claim_text": "We propose a novel transformer", "severity": "error", "section_hint": "Abstract"},
                ])
            else:
                # Check step
                return json.dumps({
                    "status": "paid",
                    "discharge_text": "Novel transformer achieves SOTA results",
                    "reason": "Found in experiments",
                })

        text = "Abstract\nWe propose a novel transformer.\nExperiments\nNovel transformer achieves SOTA results.\n"
        events = list(run_ledger_build(text, call_llm=mock_llm))
        self.assertTrue(any(e.event == "complete" for e in events))


class TestLedgerHelpers(unittest.TestCase):
    """Test internal helper functions"""

    def test_extract_section_abstract(self):
        """Extract abstract section"""
        text = "Abstract\nThis is the abstract content.\nIntroduction\nMore content."
        section = _extract_section(text, "abstract")
        self.assertIn("abstract content", section)

    def test_extract_section_not_found(self):
        """Non-existent section returns empty"""
        section = _extract_section("No sections here", "nonexistent")
        self.assertEqual(section, "")

    def test_extract_section_empty_text(self):
        """Empty text returns empty"""
        self.assertEqual(_extract_section("", "abstract"), "")

    def test_parse_json_array(self):
        """Parse JSON array from LLM response"""
        text = '```json\n[{"key": "value"}]\n```'
        result = _parse_llm_json_array(text)
        self.assertEqual(result, [{"key": "value"}])

    def test_parse_json_array_no_code_block(self):
        """Parse plain JSON array"""
        result = _parse_llm_json_array('[{"a": 1}]')
        self.assertEqual(result, [{"a": 1}])

    def test_parse_json_array_invalid(self):
        """Invalid JSON returns empty list"""
        result = _parse_llm_json_array("not json at all")
        self.assertEqual(result, [])

    def test_parse_json_object(self):
        """Parse JSON object from LLM response"""
        text = '```json\n{"status": "paid"}\n```'
        result = _parse_llm_json_object(text)
        self.assertEqual(result, {"status": "paid"})

    def test_parse_json_object_no_code_block(self):
        """Parse plain JSON object"""
        result = _parse_llm_json_object('{"a": 1}')
        self.assertEqual(result, {"a": 1})

    def test_parse_json_object_invalid(self):
        """Invalid JSON returns empty dict"""
        result = _parse_llm_json_object("not json")
        self.assertEqual(result, {})

    def test_extracted_promise_defaults(self):
        """ExtractedPromise uses default values"""
        p = ExtractedPromise(claim_text="test")
        self.assertEqual(p.severity, "info")
        self.assertEqual(p.status, "unpaid")
        self.assertEqual(p.confidence, 0.8)

    def test_ledger_build_event_to_dict(self):
        """LedgerBuildEvent has correct fields"""
        event = LedgerBuildEvent("progress", {"step": "test", "message": "testing"})
        self.assertEqual(event.event, "progress")
        self.assertEqual(event.data["step"], "test")


if __name__ == "__main__":
    unittest.main()
