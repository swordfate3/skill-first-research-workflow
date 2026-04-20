from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


def load_workflow_module():
    module_path = Path(__file__).resolve().parents[1] / "workflow.py"
    spec = importlib.util.spec_from_file_location("skill_first_workflow", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class WorkflowTests(unittest.TestCase):
    def test_prepare_workspace_scans_extracts_and_lists_agent_work(self):
        workflow = load_workflow_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            papers = root / "workspace" / "papers"
            papers.mkdir(parents=True)
            (papers / "paper-a.txt").write_text("alpha", encoding="utf-8")
            (papers / "paper-b.pdf").write_bytes(b"fake pdf bytes")

            def fake_extractor(path: Path) -> str:
                return f"{path.name}\nTable 1: Result\nEquation (1): y = x + 1"

            first = workflow.prepare_workspace(root, extractor=fake_extractor)
            workflow.state.mark_paper_card(root, "paper-a.txt", "001-paper-card-paper-a.md")
            workflow.state.mark_paper_card(root, "paper-b.pdf", "002-paper-card-paper-b.md")
            second = workflow.prepare_workspace(root, extractor=fake_extractor)

        self.assertEqual(first["papers_to_card"], ["paper-a.txt", "paper-b.pdf"])
        self.assertEqual(first["pdf_extraction"]["extracted"], ["paper-b.pdf"])
        self.assertEqual(first["next_actions"][0], "Create paper cards for 2 papers needing cards.")
        self.assertEqual(
            second["pending_collisions"],
            [{"papers": ["paper-a.txt", "paper-b.pdf"], "key": "paper-a.txt::paper-b.pdf"}],
        )
        self.assertEqual(second["next_actions"][0], "Generate 1 pending collision document.")

    def test_prepare_workspace_keeps_uncarded_scanned_papers_in_work_queue(self):
        workflow = load_workflow_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            papers = root / "workspace" / "papers"
            papers.mkdir(parents=True)
            (papers / "paper-a.txt").write_text("alpha", encoding="utf-8")

            workflow.state.scan_workspace(root)
            prepared = workflow.prepare_workspace(root)

        self.assertEqual(prepared["papers_to_card"], ["paper-a.txt"])


if __name__ == "__main__":
    unittest.main()
