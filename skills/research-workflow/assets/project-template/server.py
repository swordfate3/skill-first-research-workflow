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
            self._send_json(list_documents())
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


def list_documents() -> list[dict]:
    OUTPUTS_ROOT.mkdir(parents=True, exist_ok=True)
    documents = []
    for path in sorted(OUTPUTS_ROOT.glob("*.md")):
        content = path.read_text(encoding="utf-8", errors="replace")
        metadata, body = split_frontmatter(content)
        documents.append(
            {
                "name": path.name,
                "title": metadata.get("title") or infer_title(body) or path.stem,
                "type": metadata.get("type") or "note",
                "status": metadata.get("status") or "unknown",
            }
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
    path = OUTPUTS_ROOT / name
    if not path.exists() or path.suffix != ".md":
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
