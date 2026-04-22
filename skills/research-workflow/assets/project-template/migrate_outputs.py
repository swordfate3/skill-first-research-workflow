from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import TextIO


ROOT = Path(__file__).resolve().parent
WORKSPACE = "workspace"
OUTPUTS = "outputs"
STATE_FILE = "state.json"
INDEX_FILE = "index.json"
OUTPUT_TYPE_DIRECTORIES = {
    "paper_card": "paper-cards",
    "collision": "collisions",
    "direction": "directions",
}


def migrate_outputs(root: Path = ROOT) -> dict:
    root = Path(root)
    outputs_root = output_root(root)
    outputs_root.mkdir(parents=True, exist_ok=True)
    ensure_output_directories(outputs_root)

    moved: list[dict[str, str]] = []
    moved_map: dict[str, str] = {}

    for path in sorted(outputs_root.glob("*.md")):
        metadata, body = split_frontmatter(path.read_text(encoding="utf-8", errors="replace"))
        doc_type = metadata.get("type") or infer_type_from_name(path.name)
        target_dir_name = OUTPUT_TYPE_DIRECTORIES.get(doc_type)
        if not target_dir_name:
            continue
        target = outputs_root / target_dir_name / path.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(path), str(target))
        relative_target = relative_output_path(root, target)
        moved.append({"name": path.name, "path": relative_target, "type": doc_type})
        moved_map[path.name] = relative_target
        moved_map[f"{WORKSPACE}/{OUTPUTS}/{path.name}"] = relative_target
        moved_map[path.name] = relative_target
        if body is None:
            continue

    update_state_output_paths(root, moved_map)
    documents = scan_output_documents(root)
    write_output_index(root, documents)
    return {
        "status": "migrated",
        "moved_count": len(moved),
        "moved": moved,
        "index_path": f"{WORKSPACE}/{OUTPUTS}/{INDEX_FILE}",
    }


def ensure_output_directories(outputs_root: Path) -> None:
    for directory in OUTPUT_TYPE_DIRECTORIES.values():
        (outputs_root / directory).mkdir(parents=True, exist_ok=True)


def scan_output_documents(root: Path = ROOT) -> list[dict]:
    root = Path(root)
    outputs_root = output_root(root)
    documents = []
    for path in sorted(outputs_root.rglob("*.md")):
        if path.name == ".gitkeep":
            continue
        metadata, body = split_frontmatter(path.read_text(encoding="utf-8", errors="replace"))
        documents.append(
            {
                "name": path.name,
                "path": relative_output_path(root, path),
                "title": metadata.get("title") or infer_title(body) or path.stem,
                "type": metadata.get("type") or infer_type_from_name(path.name),
                "status": metadata.get("status") or "unknown",
                "source_papers": parse_source_papers(metadata),
            }
        )

    documents.sort(
        key=lambda item: (
            document_order(item["type"]),
            item["name"],
        )
    )
    return documents


def write_output_index(root: Path, documents: list[dict]) -> Path:
    path = output_root(root) / INDEX_FILE
    payload = {"version": 1, "documents": documents}
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def load_output_index(root: Path = ROOT) -> list[dict] | None:
    path = output_root(root) / INDEX_FILE
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    documents = payload.get("documents")
    if not isinstance(documents, list):
        return None
    normalized = []
    for item in documents:
        if not isinstance(item, dict):
            return None
        if not isinstance(item.get("name"), str) or not isinstance(item.get("path"), str):
            return None
        normalized.append(item)
    return normalized


def resolve_output_path(root: Path, relative_path: str) -> Path:
    return Path(root) / relative_path


def update_state_output_paths(root: Path, moved_map: dict[str, str]) -> None:
    state_path = Path(root) / WORKSPACE / STATE_FILE
    if not state_path.exists():
        return
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return
    if not isinstance(state, dict):
        return

    changed = False
    for paper in state.get("papers", {}).values():
        if not isinstance(paper, dict):
            continue
        current = paper.get("paper_card")
        if current in moved_map:
            paper["paper_card"] = moved_map[current]
            changed = True

    for collision in state.get("collisions", {}).values():
        if not isinstance(collision, dict):
            continue
        current = collision.get("output")
        if current in moved_map:
            collision["output"] = moved_map[current]
            changed = True

    for direction in state.get("directions", {}).values():
        if not isinstance(direction, dict):
            continue
        current = direction.get("output")
        if current in moved_map:
            direction["output"] = moved_map[current]
            changed = True

    if changed:
        state_path.write_text(
            json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def parse_source_papers(metadata: dict[str, str]) -> list[str]:
    raw = metadata.get("source_papers")
    if raw:
        return [raw]
    return []


def split_frontmatter(content: str) -> tuple[dict[str, str], str]:
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, content

    metadata: dict[str, str] = {}
    body_start = 0
    current_key = ""
    current_items: list[str] = []
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            if current_key and current_items:
                metadata[current_key] = "\n".join(current_items)
            body_start = index + 1
            break
        if ":" in line and not line.startswith(" "):
            if current_key and current_items:
                metadata[current_key] = "\n".join(current_items)
            key, value = line.split(":", 1)
            current_key = key.strip()
            current_items = []
            if value.strip():
                metadata[current_key] = value.strip()
                current_key = ""
            continue
        if current_key and line.lstrip().startswith("- "):
            current_items.append(line.lstrip()[2:].strip())
    else:
        return {}, content

    return metadata, "\n".join(lines[body_start:])


def infer_title(body: str) -> str:
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return ""


def infer_type_from_name(name: str) -> str:
    if "paper-card" in name:
        return "paper_card"
    if "collision" in name:
        return "collision"
    if "direction" in name:
        return "direction"
    return "note"


def document_order(doc_type: str) -> int:
    order = {
        "paper_card": 0,
        "collision": 1,
        "direction": 2,
    }
    return order.get(doc_type, len(order))


def output_root(root: Path) -> Path:
    return Path(root) / WORKSPACE / OUTPUTS


def relative_output_path(root: Path, path: Path) -> str:
    return path.relative_to(Path(root)).as_posix()


def main(argv: list[str] | None = None, stdout: TextIO | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python migrate_outputs.py")
    parser.add_argument("--root", default=str(ROOT), help="project root")
    args = parser.parse_args(argv)

    payload = migrate_outputs(Path(args.root))
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    if stdout is None:
        print(text)
    else:
        stdout.write(text)
        stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
