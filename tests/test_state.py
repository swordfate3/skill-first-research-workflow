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
            memory_dir = root / "workspace" / "memory" / "papers"
            papers.mkdir(parents=True)
            memory_dir.mkdir(parents=True)
            (papers / "paper-a.txt").write_text("alpha", encoding="utf-8")
            (papers / "paper-b.txt").write_text("beta", encoding="utf-8")

            state.scan_workspace(root)
            state.mark_paper_memory(root, "paper-a.txt", "workspace/memory/papers/paper-a.json")
            state.mark_paper_memory(root, "paper-b.txt", "workspace/memory/papers/paper-b.json")
            (memory_dir / "paper-a.json").write_text(
                json_memory_fixture("paper-a.txt", "aes neural differential"),
                encoding="utf-8",
            )
            (memory_dir / "paper-b.json").write_text(
                json_memory_fixture("paper-b.txt", "aes ciphertext neural"),
                encoding="utf-8",
            )
            state.mark_paper_card(root, "paper-a.txt", "001-paper-a.md")
            state.mark_paper_card(root, "paper-b.txt", "002-paper-b.md")
            before = state.scan_workspace(root)
            state.mark_collision(root, "paper-a.txt", "paper-b.txt", "003-collision.md")
            after = state.scan_workspace(root)

        self.assertEqual(len(before["pending_collisions"]), 1)
        self.assertEqual(before["pending_collisions"][0]["key"], "paper-a.txt::paper-b.txt")
        self.assertEqual(after["pending_collisions"], [])

    def test_scan_lists_papers_needing_memory_files(self):
        state = load_state_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            papers = root / "workspace" / "papers"
            papers.mkdir(parents=True)
            (papers / "paper-a.txt").write_text("alpha", encoding="utf-8")

            first = state.scan_workspace(root)
            state.mark_paper_memory(
                root,
                "paper-a.txt",
                "workspace/memory/papers/paper-a.json",
            )
            second = state.scan_workspace(root)

        self.assertEqual(
            first["papers_to_memory"],
            [
                {
                    "memory_path": "workspace/memory/papers/paper-a.json",
                    "path": "paper-a.txt",
                }
            ],
        )
        self.assertEqual(second["papers_to_memory"], [])

    def test_pending_collisions_respect_top_k_limit_per_paper(self):
        state = load_state_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            papers_dir = root / "workspace" / "papers"
            memory_dir = root / "workspace" / "memory" / "papers"
            papers_dir.mkdir(parents=True)
            memory_dir.mkdir(parents=True)

            for name, topic in [
                ("paper-a.txt", "aes differential neural distinguisher"),
                ("paper-b.txt", "aes ciphertext distinguisher neural"),
                ("paper-c.txt", "aes integral attack impossible differential"),
                ("paper-d.txt", "skinny boomerang distinguisher aes transfer"),
                ("paper-e.txt", "ascon neural trail search permutation"),
            ]:
                (papers_dir / name).write_text(topic, encoding="utf-8")
                state.scan_workspace(root)
                state.mark_paper_memory(
                    root,
                    name,
                    f"workspace/memory/papers/{Path(name).stem}.json",
                )
                (memory_dir / f"{Path(name).stem}.json").write_text(
                    json_memory_fixture(name, topic),
                    encoding="utf-8",
                )
                state.mark_paper_card(root, name, f"workspace/outputs/{Path(name).stem}.md")

            summary = state.scan_workspace(root)

        counts = {}
        for item in summary["pending_collisions"]:
            for paper in item["papers"]:
                counts[paper] = counts.get(paper, 0) + 1

        self.assertTrue(summary["pending_collisions"])
        self.assertTrue(all(count <= state.MAX_COLLISIONS_PER_PAPER for count in counts.values()))

    def test_created_high_score_collisions_become_pending_directions(self):
        state = load_state_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            papers_dir = root / "workspace" / "papers"
            memory_dir = root / "workspace" / "memory" / "papers"
            papers_dir.mkdir(parents=True)
            memory_dir.mkdir(parents=True)

            for name, topic in [
                ("paper-a.txt", "aes differential neural distinguisher"),
                ("paper-b.txt", "aes ciphertext distinguisher neural"),
            ]:
                (papers_dir / name).write_text(topic, encoding="utf-8")
                state.scan_workspace(root)
                state.mark_paper_memory(
                    root,
                    name,
                    f"workspace/memory/papers/{Path(name).stem}.json",
                )
                (memory_dir / f"{Path(name).stem}.json").write_text(
                    json_memory_fixture(name, topic),
                    encoding="utf-8",
                )
                state.mark_paper_card(root, name, f"workspace/outputs/{Path(name).stem}.md")

            state.mark_collision(
                root,
                "paper-a.txt",
                "paper-b.txt",
                "workspace/outputs/collision-a-b.md",
            )
            summary = state.scan_workspace(root)

        self.assertEqual(len(summary["pending_directions"]), 1)
        self.assertEqual(
            summary["pending_directions"][0]["collision_key"],
            "paper-a.txt::paper-b.txt",
        )

    def test_mark_direction_clears_pending_directions(self):
        state = load_state_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            papers_dir = root / "workspace" / "papers"
            memory_dir = root / "workspace" / "memory" / "papers"
            papers_dir.mkdir(parents=True)
            memory_dir.mkdir(parents=True)

            for name, topic in [
                ("paper-a.txt", "aes differential neural distinguisher"),
                ("paper-b.txt", "aes ciphertext distinguisher neural"),
            ]:
                (papers_dir / name).write_text(topic, encoding="utf-8")
                state.scan_workspace(root)
                state.mark_paper_memory(
                    root,
                    name,
                    f"workspace/memory/papers/{Path(name).stem}.json",
                )
                (memory_dir / f"{Path(name).stem}.json").write_text(
                    json_memory_fixture(name, topic),
                    encoding="utf-8",
                )
                state.mark_paper_card(root, name, f"workspace/outputs/{Path(name).stem}.md")

            state.mark_collision(
                root,
                "paper-a.txt",
                "paper-b.txt",
                "workspace/outputs/collision-a-b.md",
            )
            before = state.scan_workspace(root)
            state.mark_direction(
                root,
                "paper-a.txt::paper-b.txt",
                "workspace/outputs/direction-a-b.md",
            )
            after = state.scan_workspace(root)

        self.assertEqual(len(before["pending_directions"]), 1)
        self.assertEqual(after["pending_directions"], [])


def json_memory_fixture(name: str, topic: str) -> str:
    stem = Path(name).stem
    return f"""{{
  "meta": {{
    "title": "{stem}",
    "source_file": "{name}"
  }},
  "classification": {{
    "primary_tags": ["block-cipher", "aes"],
    "keywords": {json_keywords(topic)}
  }},
  "content": {{
    "problem": "{topic}",
    "method": "{topic}",
    "limitations": ["needs better generalization", "limited rounds"]
  }},
  "innovation_seeds": {{
    "transferable_techniques": [
      {{
        "technique": "{topic}",
        "potential_targets": ["aes", "distinguisher"],
        "reasoning": "shared target"
      }}
    ],
    "open_problems": ["cross-setting transfer"],
    "weakness_opportunities": ["limited evidence"]
  }}
}}
"""


def json_keywords(topic: str) -> str:
    values = [word for word in topic.split() if word]
    return "[" + ", ".join(f'"{value}"' for value in values) + "]"


if __name__ == "__main__":
    unittest.main()
