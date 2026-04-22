from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import json


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
            write_document(
                outputs_root / "b-paper-card.md",
                title="B Paper Card",
                doc_type="paper_card",
            )
            write_document(
                outputs_root / "a-paper-card.md",
                title="A Paper Card",
                doc_type="paper_card",
            )
            write_document(
                outputs_root / "c-collision.md",
                title="C Collision",
                doc_type="collision",
            )
            write_document(
                outputs_root / "a-direction.md",
                title="A Direction",
                doc_type="direction",
            )

            with patch.object(server, "OUTPUTS_ROOT", outputs_root):
                documents = server.list_documents()

        self.assertEqual(
            [doc["name"] for doc in documents],
            [
                "a-paper-card.md",
                "b-paper-card.md",
                "c-collision.md",
                "a-direction.md",
            ],
        )

    def test_list_documents_can_filter_by_type(self):
        server = load_server_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            outputs_root = Path(tmpdir) / "workspace" / "outputs"
            outputs_root.mkdir(parents=True)
            write_document(
                outputs_root / "a-paper-card.md",
                title="A Paper Card",
                doc_type="paper_card",
            )
            write_document(
                outputs_root / "b-collision.md",
                title="B Collision",
                doc_type="collision",
            )
            write_document(
                outputs_root / "c-direction.md",
                title="C Direction",
                doc_type="direction",
            )

            with patch.object(server, "OUTPUTS_ROOT", outputs_root):
                documents = server.list_documents(doc_type="direction")

        self.assertEqual([doc["name"] for doc in documents], ["c-direction.md"])

    def test_list_documents_treats_all_filter_as_unfiltered(self):
        server = load_server_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            outputs_root = Path(tmpdir) / "workspace" / "outputs"
            outputs_root.mkdir(parents=True)
            write_document(
                outputs_root / "a-paper-card.md",
                title="A Paper Card",
                doc_type="paper_card",
            )
            write_document(
                outputs_root / "b-collision.md",
                title="B Collision",
                doc_type="collision",
            )
            write_document(
                outputs_root / "c-direction.md",
                title="C Direction",
                doc_type="direction",
            )

            with patch.object(server, "OUTPUTS_ROOT", outputs_root):
                documents = server.list_documents(doc_type="all")

        self.assertEqual(
            [doc["type"] for doc in documents],
            ["paper_card", "collision", "direction"],
        )

    def test_list_documents_reads_nested_output_directories(self):
        server = load_server_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            outputs_root = Path(tmpdir) / "workspace" / "outputs"
            (outputs_root / "paper-cards").mkdir(parents=True)
            (outputs_root / "collisions").mkdir(parents=True)
            (outputs_root / "directions").mkdir(parents=True)
            write_document(
                outputs_root / "paper-cards" / "a-paper-card.md",
                title="A Paper Card",
                doc_type="paper_card",
            )
            write_document(
                outputs_root / "collisions" / "b-collision.md",
                title="B Collision",
                doc_type="collision",
            )
            write_document(
                outputs_root / "directions" / "c-direction.md",
                title="C Direction",
                doc_type="direction",
            )

            with patch.object(server, "OUTPUTS_ROOT", outputs_root):
                documents = server.list_documents(doc_type="all")

        self.assertEqual(
            [doc["name"] for doc in documents],
            ["a-paper-card.md", "b-collision.md", "c-direction.md"],
        )

    def test_list_documents_prefers_index_json_when_present_and_consistent(self):
        server = load_server_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            outputs_root = Path(tmpdir) / "workspace" / "outputs"
            outputs_root.mkdir(parents=True)
            (outputs_root / "paper-cards").mkdir(parents=True)
            write_document(
                outputs_root / "paper-cards" / "a-paper-card.md",
                title="A Paper Card",
                doc_type="paper_card",
            )
            (outputs_root / "index.json").write_text(
                json.dumps(
                    {
                        "version": 1,
                        "documents": [
                            {
                                "name": "a-paper-card.md",
                                "path": "workspace/outputs/paper-cards/a-paper-card.md",
                                "title": "Indexed Card Title",
                                "type": "paper_card",
                                "status": "pending",
                                "source_papers": ["paper-a.pdf"],
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            with patch.object(server, "OUTPUTS_ROOT", outputs_root):
                documents = server.list_documents(doc_type="all")

        self.assertEqual([doc["name"] for doc in documents], ["a-paper-card.md"])
        self.assertEqual(documents[0]["title"], "Indexed Card Title")

    def test_load_document_can_resolve_indexed_nested_path(self):
        server = load_server_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            outputs_root = Path(tmpdir) / "workspace" / "outputs"
            direction_dir = outputs_root / "directions"
            direction_dir.mkdir(parents=True)
            write_document(
                direction_dir / "c-direction.md",
                title="C Direction",
                doc_type="direction",
            )
            (outputs_root / "index.json").write_text(
                json.dumps(
                    {
                        "version": 1,
                        "documents": [
                            {
                                "name": "c-direction.md",
                                "path": "workspace/outputs/directions/c-direction.md",
                                "title": "C Direction",
                                "type": "direction",
                                "status": "draft",
                                "source_papers": ["paper-c.pdf"],
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            with patch.object(server, "OUTPUTS_ROOT", outputs_root):
                loaded = server.load_document("c-direction.md")

        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["type"], "direction")
        self.assertEqual(loaded["name"], "c-direction.md")


if __name__ == "__main__":
    unittest.main()
