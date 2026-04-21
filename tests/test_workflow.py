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
            workflow.state.mark_paper_memory(
                root, "paper-a.txt", "workspace/memory/papers/paper-a.json"
            )
            workflow.state.mark_paper_memory(
                root, "paper-b.pdf", "workspace/memory/papers/paper-b.json"
            )
            memory_dir = root / "workspace" / "memory" / "papers"
            memory_dir.mkdir(parents=True, exist_ok=True)
            (memory_dir / "paper-a.json").write_text(
                '{"meta":{"title":"paper-a"},"classification":{"primary_tags":["aes"],"keywords":["aes","neural"]},"content":{"limitations":["limited rounds"]},"innovation_seeds":{"transferable_techniques":[{"technique":"neural distinguisher","potential_targets":["aes"],"reasoning":"shared target"}],"open_problems":["generalization"],"weakness_opportunities":["better evidence"]}}',
                encoding="utf-8",
            )
            (memory_dir / "paper-b.json").write_text(
                '{"meta":{"title":"paper-b"},"classification":{"primary_tags":["aes"],"keywords":["aes","ciphertext"]},"content":{"limitations":["ciphertext-only"]},"innovation_seeds":{"transferable_techniques":[{"technique":"ciphertext distinguisher","potential_targets":["aes"],"reasoning":"shared target"}],"open_problems":["new metrics"],"weakness_opportunities":["hybrid models"]}}',
                encoding="utf-8",
            )
            workflow.state.mark_paper_card(root, "paper-a.txt", "001-paper-card-paper-a.md")
            workflow.state.mark_paper_card(root, "paper-b.pdf", "002-paper-card-paper-b.md")
            second = workflow.prepare_workspace(root, extractor=fake_extractor)
            workflow.state.mark_collision(
                root, "paper-a.txt", "paper-b.pdf", "003-collision.md"
            )
            third = workflow.prepare_workspace(root, extractor=fake_extractor)
            workflow.state.mark_direction(
                root, "paper-a.txt::paper-b.pdf", "004-direction.md"
            )
            fourth = workflow.prepare_workspace(root, extractor=fake_extractor)

        self.assertEqual(
            first["papers_to_memory"],
            [
                {"memory_path": "workspace/memory/papers/paper-a.json", "path": "paper-a.txt"},
                {"memory_path": "workspace/memory/papers/paper-b.json", "path": "paper-b.pdf"},
            ],
        )
        self.assertEqual(first["papers_to_card"], [])
        self.assertEqual(first["pdf_extraction"]["extracted"], ["paper-b.pdf"])
        self.assertEqual(
            first["next_actions"][0],
            "Create 2 paper memory records before collision scoring.",
        )
        self.assertEqual(len(second["pending_collisions"]), 1)
        self.assertEqual(second["pending_collisions"][0]["key"], "paper-a.txt::paper-b.pdf")
        self.assertEqual(second["next_actions"][0], "Generate 1 pending collision document.")
        self.assertEqual(len(third["pending_directions"]), 1)
        self.assertEqual(third["next_actions"][0], "Draft 1 high-priority research direction.")
        self.assertEqual(fourth["pending_directions"], [])
        self.assertNotIn("Draft 1 high-priority research direction.", fourth["next_actions"])

    def test_prepare_workspace_keeps_uncarded_scanned_papers_in_work_queue(self):
        workflow = load_workflow_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            papers = root / "workspace" / "papers"
            papers.mkdir(parents=True)
            (papers / "paper-a.txt").write_text("alpha", encoding="utf-8")

            workflow.state.scan_workspace(root)
            prepared = workflow.prepare_workspace(root)

        self.assertEqual(prepared["papers_to_card"], [])
        self.assertEqual(
            prepared["papers_to_memory"],
            [{"memory_path": "workspace/memory/papers/paper-a.json", "path": "paper-a.txt"}],
        )


if __name__ == "__main__":
    unittest.main()
