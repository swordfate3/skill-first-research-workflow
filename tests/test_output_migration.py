from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_migration_module():
    module_path = ROOT / "migrate_outputs.py"
    spec = importlib.util.spec_from_file_location("skill_first_migrate_outputs", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_document(path: Path, *, title: str, doc_type: str, status: str = "pending") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""---
title: {title}
type: {doc_type}
status: {status}
source_papers:
  - paper-a.pdf
---
# {title}
""",
        encoding="utf-8",
    )


class OutputMigrationTests(unittest.TestCase):
    def test_migrate_outputs_moves_flat_files_and_builds_index(self):
        migrate_outputs = load_migration_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            outputs_root = root / "workspace" / "outputs"
            outputs_root.mkdir(parents=True)
            write_document(outputs_root / "001-paper-card-a.md", title="Card A", doc_type="paper_card")
            write_document(outputs_root / "003-collision-a-b.md", title="Collision A B", doc_type="collision")
            write_document(outputs_root / "004-direction-a-b.md", title="Direction A B", doc_type="direction")

            result = migrate_outputs.migrate_outputs(root)
            index = json.loads((outputs_root / "index.json").read_text(encoding="utf-8"))
            self.assertEqual(result["moved_count"], 3)
            self.assertTrue((outputs_root / "paper-cards" / "001-paper-card-a.md").exists())
            self.assertTrue((outputs_root / "collisions" / "003-collision-a-b.md").exists())
            self.assertTrue((outputs_root / "directions" / "004-direction-a-b.md").exists())
            self.assertEqual(len(index["documents"]), 3)
            self.assertEqual(
                [item["type"] for item in index["documents"]],
                ["paper_card", "collision", "direction"],
            )


if __name__ == "__main__":
    unittest.main()
