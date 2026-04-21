from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class LanguageDefaultTests(unittest.TestCase):
    def test_skill_requires_chinese_outputs_with_english_terms_preserved(self):
        skill = (ROOT / "skills" / "research-workflow" / "SKILL.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("默认使用中文", skill)
        self.assertIn("关键英文术语", skill)
        self.assertIn("术语对照", skill)

    def test_templates_use_chinese_section_titles(self):
        expected_titles = {
            "paper-card.md": "## 一句话总结",
            "collision-ideas.md": "## 候选方向 1",
            "prototype.md": "## 研究问题",
            "draft.md": "## 摘要",
            "direction.md": "## 为什么值得做",
        }

        for filename, title in expected_titles.items():
            with self.subTest(filename=filename):
                content = (ROOT / "templates" / filename).read_text(encoding="utf-8")
                self.assertIn(title, content)


if __name__ == "__main__":
    unittest.main()
