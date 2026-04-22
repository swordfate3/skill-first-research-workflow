from __future__ import annotations

import http.client
import importlib.util
import json
import tempfile
import threading
import time
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
    def start_test_server(self, server_module):
        httpd = server_module.ThreadingHTTPServer(("127.0.0.1", 0), server_module.ResearchWorkflowHandler)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        return httpd, thread

    def encode_multipart(self, files: list[tuple[str, bytes]], boundary: str = "BOUNDARY") -> bytes:
        lines: list[bytes] = []
        for name, payload in files:
            lines.extend(
                [
                    f"--{boundary}".encode("utf-8"),
                    (
                        f'Content-Disposition: form-data; name="files"; filename="{name}"'
                    ).encode("utf-8"),
                    b"Content-Type: application/pdf",
                    b"",
                    payload,
                ]
            )
        lines.append(f"--{boundary}--".encode("utf-8"))
        lines.append(b"")
        return b"\r\n".join(lines)

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

    def test_upload_papers_saves_files_and_reports_batch_status(self):
        server = load_server_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            outputs_root = root / "workspace" / "outputs"
            outputs_root.mkdir(parents=True)
            papers_root = root / "workspace" / "papers"
            papers_root.mkdir(parents=True)

            def fake_processor(run_root: Path) -> None:
                self.assertEqual(run_root, root)
                time.sleep(0.05)

            upload_manager = server.UploadManager(root, processor=fake_processor)
            with patch.object(server, "ROOT", root), patch.object(server, "OUTPUTS_ROOT", outputs_root), patch.object(
                server, "PAPERS_ROOT", papers_root
            ), patch.object(server, "UPLOAD_MANAGER", upload_manager):
                httpd, thread = self.start_test_server(server)
                try:
                    body = self.encode_multipart(
                        [("paper-a.pdf", b"fake-pdf-a"), ("paper-b.pdf", b"fake-pdf-b")]
                    )
                    connection = http.client.HTTPConnection("127.0.0.1", httpd.server_port, timeout=5)
                    connection.request(
                        "POST",
                        "/api/upload-papers",
                        body=body,
                        headers={"Content-Type": "multipart/form-data; boundary=BOUNDARY"},
                    )
                    response = connection.getresponse()
                    payload = json.loads(response.read().decode("utf-8"))
                    connection.close()

                    self.assertEqual(response.status, 201)
                    self.assertTrue(payload["batch_id"])
                    self.assertEqual(
                        [item["status"] for item in payload["files"]],
                        ["queued", "queued"],
                    )
                    self.assertEqual((papers_root / "paper-a.pdf").read_bytes(), b"fake-pdf-a")
                    self.assertEqual((papers_root / "paper-b.pdf").read_bytes(), b"fake-pdf-b")

                    for _ in range(20):
                        snapshot = upload_manager.snapshot()
                        if snapshot["files"] and all(
                            item["status"] == "completed" for item in snapshot["files"]
                        ):
                            break
                        time.sleep(0.02)
                    else:
                        self.fail("upload batch did not reach completed state")
                finally:
                    httpd.shutdown()
                    thread.join(timeout=1)
                    httpd.server_close()

    def test_upload_papers_rejects_non_pdf_files(self):
        server = load_server_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            outputs_root = root / "workspace" / "outputs"
            outputs_root.mkdir(parents=True)
            papers_root = root / "workspace" / "papers"
            papers_root.mkdir(parents=True)

            upload_manager = server.UploadManager(root, processor=lambda _: None)
            with patch.object(server, "ROOT", root), patch.object(server, "OUTPUTS_ROOT", outputs_root), patch.object(
                server, "PAPERS_ROOT", papers_root
            ), patch.object(server, "UPLOAD_MANAGER", upload_manager):
                httpd, thread = self.start_test_server(server)
                try:
                    body = self.encode_multipart([("notes.txt", b"not-pdf")])
                    connection = http.client.HTTPConnection("127.0.0.1", httpd.server_port, timeout=5)
                    connection.request(
                        "POST",
                        "/api/upload-papers",
                        body=body,
                        headers={"Content-Type": "multipart/form-data; boundary=BOUNDARY"},
                    )
                    response = connection.getresponse()
                    payload = json.loads(response.read().decode("utf-8"))
                    connection.close()

                    self.assertEqual(response.status, 400)
                    self.assertIn("PDF", payload["error"])
                finally:
                    httpd.shutdown()
                    thread.join(timeout=1)
                    httpd.server_close()

    def test_upload_papers_overwrites_existing_file(self):
        server = load_server_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            outputs_root = root / "workspace" / "outputs"
            outputs_root.mkdir(parents=True)
            papers_root = root / "workspace" / "papers"
            papers_root.mkdir(parents=True)
            (papers_root / "paper-a.pdf").write_bytes(b"old-content")

            upload_manager = server.UploadManager(root, processor=lambda _: None)
            with patch.object(server, "ROOT", root), patch.object(server, "OUTPUTS_ROOT", outputs_root), patch.object(
                server, "PAPERS_ROOT", papers_root
            ), patch.object(server, "UPLOAD_MANAGER", upload_manager):
                httpd, thread = self.start_test_server(server)
                try:
                    body = self.encode_multipart([("paper-a.pdf", b"new-content")])
                    connection = http.client.HTTPConnection("127.0.0.1", httpd.server_port, timeout=5)
                    connection.request(
                        "POST",
                        "/api/upload-papers",
                        body=body,
                        headers={"Content-Type": "multipart/form-data; boundary=BOUNDARY"},
                    )
                    response = connection.getresponse()
                    response.read()
                    connection.close()

                    self.assertEqual(response.status, 201)
                    self.assertEqual((papers_root / "paper-a.pdf").read_bytes(), b"new-content")
                finally:
                    httpd.shutdown()
                    thread.join(timeout=1)
                    httpd.server_close()

    def test_upload_status_endpoint_returns_current_batch_state(self):
        server = load_server_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            outputs_root = root / "workspace" / "outputs"
            outputs_root.mkdir(parents=True)
            papers_root = root / "workspace" / "papers"
            papers_root.mkdir(parents=True)

            hold = threading.Event()

            def slow_processor(_: Path) -> None:
                hold.wait(timeout=1)

            upload_manager = server.UploadManager(root, processor=slow_processor)
            with patch.object(server, "ROOT", root), patch.object(server, "OUTPUTS_ROOT", outputs_root), patch.object(
                server, "PAPERS_ROOT", papers_root
            ), patch.object(server, "UPLOAD_MANAGER", upload_manager):
                httpd, thread = self.start_test_server(server)
                try:
                    body = self.encode_multipart([("paper-a.pdf", b"fake-pdf-a")])
                    connection = http.client.HTTPConnection("127.0.0.1", httpd.server_port, timeout=5)
                    connection.request(
                        "POST",
                        "/api/upload-papers",
                        body=body,
                        headers={"Content-Type": "multipart/form-data; boundary=BOUNDARY"},
                    )
                    response = connection.getresponse()
                    response.read()
                    connection.close()

                    for _ in range(20):
                        snapshot = upload_manager.snapshot()
                        if snapshot["is_processing"]:
                            break
                        time.sleep(0.02)
                    else:
                        self.fail("upload batch did not enter processing state")

                    connection = http.client.HTTPConnection("127.0.0.1", httpd.server_port, timeout=5)
                    connection.request("GET", "/api/upload-status")
                    response = connection.getresponse()
                    payload = json.loads(response.read().decode("utf-8"))
                    connection.close()

                    self.assertEqual(response.status, 200)
                    self.assertTrue(payload["active_batch_id"])
                    self.assertTrue(payload["is_processing"])
                    self.assertEqual(payload["files"][0]["status"], "processing")
                finally:
                    hold.set()
                    httpd.shutdown()
                    thread.join(timeout=1)
                    httpd.server_close()


if __name__ == "__main__":
    unittest.main()
