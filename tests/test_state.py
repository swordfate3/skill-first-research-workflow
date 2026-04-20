from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


def load_state_module():
    module_path = Path(__file__).resolve().parents[1] / "state.py"
    spec = importlib.util.spec_from_file_location("skill_first_state", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class SkillFirstStateTests(unittest.TestCase):
    def test_scan_detects_new_and_unchanged_papers(self):
        state = load_state_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            papers = root / "workspace" / "papers"
            papers.mkdir(parents=True)
            (papers / "paper-a.txt").write_text("alpha", encoding="utf-8")

            first = state.scan_workspace(root)
            second = state.scan_workspace(root)

        self.assertEqual([item["path"] for item in first["new_papers"]], ["paper-a.txt"])
        self.assertEqual(second["new_papers"], [])
        self.assertEqual([item["path"] for item in second["unchanged_papers"]], ["paper-a.txt"])

    def test_scan_detects_changed_paper_and_clears_outputs(self):
        state = load_state_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            papers = root / "workspace" / "papers"
            papers.mkdir(parents=True)
            paper = papers / "paper-a.txt"
            paper.write_text("alpha", encoding="utf-8")

            state.scan_workspace(root)
            state.mark_paper_card(root, "paper-a.txt", "001-paper-a.md")
            paper.write_text("beta", encoding="utf-8")
            summary = state.scan_workspace(root)
            stored = state.load_state(root)["papers"]["paper-a.txt"]

        self.assertEqual([item["path"] for item in summary["changed_papers"]], ["paper-a.txt"])
        self.assertNotIn("paper_card", stored)

    def test_scan_lists_pending_collision_pairs_for_carded_papers(self):
        state = load_state_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            papers = root / "workspace" / "papers"
            papers.mkdir(parents=True)
            (papers / "paper-a.txt").write_text("alpha", encoding="utf-8")
            (papers / "paper-b.txt").write_text("beta", encoding="utf-8")

            state.scan_workspace(root)
            state.mark_paper_card(root, "paper-a.txt", "001-paper-a.md")
            state.mark_paper_card(root, "paper-b.txt", "002-paper-b.md")
            before = state.scan_workspace(root)
            state.mark_collision(root, "paper-a.txt", "paper-b.txt", "003-collision.md")
            after = state.scan_workspace(root)

        self.assertEqual(
            before["pending_collisions"],
            [{"papers": ["paper-a.txt", "paper-b.txt"], "key": "paper-a.txt::paper-b.txt"}],
        )
        self.assertEqual(after["pending_collisions"], [])


if __name__ == "__main__":
    unittest.main()
