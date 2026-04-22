from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from state import load_state, scan_workspace

WEB_ROOT = ROOT / "web"
OUTPUTS_ROOT = ROOT / "workspace" / "outputs"
HOST = "127.0.0.1"
PORT = 8765
DOCUMENT_TYPE_ORDER = {
    "paper_card": 0,
    "collision": 1,
    "direction": 2,
}


class ResearchWorkflowHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._serve_file(WEB_ROOT / "index.html", "text/html; charset=utf-8")
            return
        if parsed.path == "/app.js":
            self._serve_file(WEB_ROOT / "app.js", "text/javascript; charset=utf-8")
            return
        if parsed.path == "/styles.css":
            self._serve_file(WEB_ROOT / "styles.css", "text/css; charset=utf-8")
            return
        if parsed.path == "/api/documents":
            query = parse_qs(parsed.query)
            doc_type = query.get("doc_type", query.get("type", [""]))[0] or None
            self._send_json(list_documents(doc_type=doc_type))
            return
        if parsed.path == "/api/state":
            self._send_json(build_state_summary())
            return
        if parsed.path == "/api/document":
            query = parse_qs(parsed.query)
            name = query.get("name", [""])[0]
            document = load_document(name)
            if document is None:
                self._send_json({"error": "document not found"}, status=404)
                return
            self._send_json(document)
            return
        self._send_json({"error": "not found"}, status=404)

    def log_message(self, format: str, *args) -> None:
        return

    def _serve_file(self, path: Path, content_type: str) -> None:
        if not path.exists():
            self._send_json({"error": "file not found"}, status=404)
            return
        payload = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _send_json(self, payload: object, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def list_documents(doc_type: str | None = None) -> list[dict]:
    OUTPUTS_ROOT.mkdir(parents=True, exist_ok=True)
    normalized_filter = None if doc_type in {None, "", "all"} else doc_type
    scanned_documents = [
        {
            "name": item["name"],
            "title": item.get("title") or item["name"],
            "type": item.get("type") or "note",
            "status": item.get("status") or "unknown",
        }
        for item in scan_output_documents_from_outputs_root(OUTPUTS_ROOT)
    ]
    indexed_documents = load_output_index_from_outputs_root(OUTPUTS_ROOT)
    if indexed_documents and same_document_names(indexed_documents, scanned_documents):
        documents = [
            {
                "name": item["name"],
                "title": item.get("title") or item["name"],
                "type": item.get("type") or "note",
                "status": item.get("status") or "unknown",
            }
            for item in indexed_documents
        ]
    else:
        documents = scanned_documents
    if normalized_filter:
        documents = [item for item in documents if item["type"] == normalized_filter]
    documents.sort(
        key=lambda item: (
            DOCUMENT_TYPE_ORDER.get(item["type"], len(DOCUMENT_TYPE_ORDER)),
            item["name"],
        )
    )
    return documents


def build_state_summary() -> dict:
    scan = scan_workspace(ROOT)
    state = load_state(ROOT)
    return {
        "paper_count": len(state.get("papers", {})),
        "memory_count": sum(
            1
            for paper in state.get("papers", {}).values()
            if isinstance(paper, dict) and paper.get("paper_memory")
        ),
        "collision_count": len(state.get("collisions", {})),
        "direction_count": len(state.get("directions", {})),
        "new_papers": scan["new_papers"],
        "changed_papers": scan["changed_papers"],
        "papers_to_memory": scan["papers_to_memory"],
        "pending_collisions": scan["pending_collisions"],
        "pending_directions": scan["pending_directions"],
    }


def load_document(name: str) -> dict | None:
    if not name or "/" in name or "\\" in name:
        return None
    path = resolve_document_name(name)
    if path is None:
        return None
    content = path.read_text(encoding="utf-8", errors="replace")
    metadata, body = split_frontmatter(content)
    return {
        "name": path.name,
        "title": metadata.get("title") or infer_title(body) or path.stem,
        "type": metadata.get("type") or "note",
        "status": metadata.get("status") or "unknown",
        "metadata": metadata,
        "body": body.strip(),
    }


def resolve_document_name(name: str) -> Path | None:
    indexed_documents = load_output_index_from_outputs_root(OUTPUTS_ROOT)
    if indexed_documents:
        for item in indexed_documents:
            if item.get("name") != name:
                continue
            path = resolve_indexed_path(OUTPUTS_ROOT, item["path"])
            if path.exists() and path.suffix == ".md":
                return path

    for item in scan_output_documents_from_outputs_root(OUTPUTS_ROOT):
        if item.get("name") != name:
            continue
        path = resolve_indexed_path(OUTPUTS_ROOT, item["path"])
        if path.exists() and path.suffix == ".md":
            return path
    return None


def load_output_index_from_outputs_root(outputs_root: Path) -> list[dict] | None:
    path = outputs_root / "index.json"
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict) or not isinstance(payload.get("documents"), list):
        return None
    return [item for item in payload["documents"] if isinstance(item, dict)]


def scan_output_documents_from_outputs_root(outputs_root: Path) -> list[dict]:
    documents = []
    for path in sorted(outputs_root.rglob("*.md")):
        if path.name == ".gitkeep":
            continue
        content = path.read_text(encoding="utf-8", errors="replace")
        metadata, body = split_frontmatter(content)
        documents.append(
            {
                "name": path.name,
                "path": relative_document_path(outputs_root, path),
                "title": metadata.get("title") or infer_title(body) or path.stem,
                "type": metadata.get("type") or "note",
                "status": metadata.get("status") or "unknown",
            }
        )
    documents.sort(
        key=lambda item: (
            DOCUMENT_TYPE_ORDER.get(item["type"], len(DOCUMENT_TYPE_ORDER)),
            item["name"],
        )
    )
    return documents


def resolve_indexed_path(outputs_root: Path, relative_path: str) -> Path:
    marker = "workspace/outputs/"
    if relative_path.startswith(marker):
        return outputs_root / relative_path[len(marker) :]
    return outputs_root / relative_path


def relative_document_path(outputs_root: Path, path: Path) -> str:
    return f"workspace/outputs/{path.relative_to(outputs_root).as_posix()}"


def same_document_names(indexed_documents: list[dict], scanned_documents: list[dict]) -> bool:
    return {item.get("name") for item in indexed_documents} == {
        item.get("name") for item in scanned_documents
    }


def split_frontmatter(content: str) -> tuple[dict[str, str], str]:
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, content

    metadata: dict[str, str] = {}
    body_start = 0
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            body_start = index + 1
            break
        if ":" in line and not line.startswith(" "):
            key, value = line.split(":", 1)
            metadata[key.strip()] = value.strip()
    else:
        return {}, content

    return metadata, "\n".join(lines[body_start:])


def infer_title(body: str) -> str:
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return ""


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), ResearchWorkflowHandler)
    print(f"Serving skill-first research workflow at http://{HOST}:{PORT}")
    print(f"Reading markdown outputs from {OUTPUTS_ROOT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
