from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


def load_server_module():
    module_path = Path(__file__).resolve().parents[1] / "server.py"
    spec = importlib.util.spec_from_file_location("skill_first_server", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_document(path: Path, *, title: str, doc_type: str, status: str = "draft") -> None:
    path.write_text(
        f"""---
title: {title}
type: {doc_type}
status: {status}
---
# {title}
""",
        encoding="utf-8",
    )


class ServerTests(unittest.TestCase):
    def test_list_documents_sorts_by_type_then_name(self):
        server = load_server_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            outputs_root = Path(tmpdir) / "workspace" / "outputs"
            outputs_root.mkdir(parents=True)
            write_document(outputs_root / "b-direction.md", title="B Direction", doc_type="direction")
            write_document(outputs_root / "z-direction.md", title="Z Direction", doc_type="direction")
            write_document(outputs_root / "a-note.md", title="A Note", doc_type="note")
            write_document(outputs_root / "m-note.md", title="M Note", doc_type="note")

            with patch.object(server, "OUTPUTS_ROOT", outputs_root):
                documents = server.list_documents()

        self.assertEqual(
            [doc["name"] for doc in documents],
            ["b-direction.md", "z-direction.md", "a-note.md", "m-note.md"],
        )

    def test_list_documents_can_filter_by_type(self):
        server = load_server_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            outputs_root = Path(tmpdir) / "workspace" / "outputs"
            outputs_root.mkdir(parents=True)
            write_document(outputs_root / "a-direction.md", title="A Direction", doc_type="direction")
            write_document(outputs_root / "b-note.md", title="B Note", doc_type="note")
            write_document(outputs_root / "c-direction.md", title="C Direction", doc_type="direction")

            with patch.object(server, "OUTPUTS_ROOT", outputs_root):
                documents = server.list_documents(type_filter="direction")

        self.assertEqual([doc["name"] for doc in documents], ["a-direction.md", "c-direction.md"])


if __name__ == "__main__":
    unittest.main()
