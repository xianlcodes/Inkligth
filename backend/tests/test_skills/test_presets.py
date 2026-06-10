"""预置技能单元测试"""

import unittest


class TestPresets(unittest.TestCase):
    """测试预置技能模板"""

    def test_presets_count(self):
        """验证预置技能数量"""
        from app.skills.presets import get_presets
        presets = get_presets()
        self.assertEqual(len(presets), 5)

    def test_presets_have_required_fields(self):
        """验证预置技能有必需字段"""
        from app.skills.presets import get_presets
        for preset in get_presets():
            self.assertTrue(preset.name)
            self.assertTrue(preset.description)
            self.assertTrue(preset.layer)
            self.assertTrue(preset.content)
            self.assertIn(preset.layer, ["soul", "agents", "identity"])

    def test_get_preset_by_name(self):
        """测试按名称获取预置技能"""
        from app.skills.presets import get_preset
        preset = get_preset("academic_writing")
        self.assertIsNotNone(preset)
        self.assertEqual(preset.name, "academic_writing")

    def test_get_nonexistent_preset(self):
        """测试获取不存在的预置技能"""
        from app.skills.presets import get_preset
        preset = get_preset("nonexistent_skill")
        self.assertIsNone(preset)

    def test_presets_unique_names(self):
        """验证预置技能名称唯一"""
        from app.skills.presets import get_presets
        names = [p.name for p in get_presets()]
        self.assertEqual(len(names), len(set(names)))

    def test_preset_layers(self):
        """验证预置技能层级分布"""
        from app.skills.presets import get_presets
        layers = {p.name: p.layer for p in get_presets()}
        self.assertEqual(layers["academic_writing"], "agents")
        self.assertEqual(layers["paper_review"], "agents")
        self.assertEqual(layers["citation_format"], "agents")
        self.assertEqual(layers["chinese_academic"], "identity")
        self.assertEqual(layers["methodology_critique"], "agents")


if __name__ == "__main__":
    unittest.main()
