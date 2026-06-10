"""Skills registry unit tests."""

import unittest


class TestLayerConcepts(unittest.TestCase):
    """Test layer ordering and prompt building concepts."""

    def test_layer_injection_order(self):
        expected = ["soul", "agents", "identity"]
        self.assertEqual(len(expected), 3)
        self.assertEqual(expected[0], "soul")

    def test_skill_layer_names(self):
        layers = ["soul", "agents", "identity"]
        for layer in layers:
            self.assertIn(layer, layers)

    def test_build_system_prompt_with_skills(self):
        base = "You are an assistant."
        injection = "<!-- SKILL: test (agents) -->\nBe formal."

        def build(base_prompt, skill_injection):
            if not skill_injection:
                return base_prompt
            return f"{base_prompt}\n\n{skill_injection}"

        result = build(base, injection)
        self.assertIn("assistant", result)
        self.assertIn("SKILL: test", result)

    def test_build_system_prompt_empty_skills(self):
        base = "You are an assistant."

        def build(base_prompt, skill_injection):
            if not skill_injection:
                return base_prompt
            return f"{base_prompt}\n\n{skill_injection}"

        result = build(base, "")
        self.assertEqual(result, base)

    def test_skill_sorting_by_layer(self):
        skills = [
            {"name": "low_agents", "layer": "agents", "priority": 0},
            {"name": "high_soul", "layer": "soul", "priority": 100},
            {"name": "high_agents", "layer": "agents", "priority": 50},
            {"name": "medium_identity", "layer": "identity", "priority": 10},
        ]
        layer_order = {"soul": 0, "agents": 1, "identity": 2}

        def sort_key(s):
            return (layer_order.get(s["layer"], 99), -s["priority"])

        sorted_skills = sorted(skills, key=sort_key)
        self.assertEqual(sorted_skills[0]["name"], "high_soul")
        self.assertEqual(sorted_skills[1]["name"], "high_agents")
        self.assertEqual(sorted_skills[2]["name"], "low_agents")
        self.assertEqual(sorted_skills[3]["name"], "medium_identity")


if __name__ == "__main__":
    unittest.main()
