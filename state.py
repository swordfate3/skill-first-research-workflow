from __future__ import annotations

import argparse
import hashlib
import json
from itertools import combinations
from pathlib import Path
from typing import TextIO


ROOT = Path(__file__).resolve().parent
WORKSPACE = "workspace"
PAPERS = "papers"
STATE_FILE = "state.json"
SUPPORTED_PAPER_SUFFIXES = {".pdf", ".md", ".txt"}


def load_state(root: Path = ROOT) -> dict:
    path = state_path(root)
    if not path.exists():
        return {"version": 1, "papers": {}, "collisions": {}}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return {"version": 1, "papers": {}, "collisions": {}}
    payload.setdefault("version", 1)
    payload.setdefault("papers", {})
    payload.setdefault("collisions", {})
    return payload


def save_state(root: Path, state: dict) -> None:
    path = state_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def scan_workspace(root: Path = ROOT) -> dict:
    root = Path(root)
    state = load_state(root)
    papers = state.setdefault("papers", {})
    collisions = state.setdefault("collisions", {})
    new_papers: list[dict] = []
    changed_papers: list[dict] = []
    unchanged_papers: list[dict] = []

    for path in discover_papers(root):
        relative_path = path.relative_to(papers_root(root)).as_posix()
        digest = hash_file(path)
        existing = papers.get(relative_path)
        if existing is None:
            papers[relative_path] = {"hash": digest, "status": "new"}
            new_papers.append({"path": relative_path, "hash": digest})
            continue
        if existing.get("hash") != digest:
            papers[relative_path] = {
                "hash": digest,
                "previous_hash": existing.get("hash", ""),
                "status": "changed",
            }
            remove_collisions_for_paper(collisions, relative_path)
            changed_papers.append({"path": relative_path, "hash": digest})
            continue
        unchanged_papers.append({"path": relative_path, "hash": digest})

    pending_collisions = build_pending_collisions(state)
    save_state(root, state)
    return {
        "new_papers": new_papers,
        "changed_papers": changed_papers,
        "unchanged_papers": unchanged_papers,
        "pending_collisions": pending_collisions,
    }


def mark_paper_card(root: Path, paper_path: str, output_path: str) -> dict:
    state = load_state(root)
    papers = state.setdefault("papers", {})
    paper = papers.setdefault(paper_path, {})
    paper["paper_card"] = output_path
    paper["status"] = "card_created"
    save_state(root, state)
    return paper


def mark_collision(root: Path, paper_a: str, paper_b: str, output_path: str) -> dict:
    state = load_state(root)
    collisions = state.setdefault("collisions", {})
    key = collision_key(paper_a, paper_b)
    collisions[key] = {
        "papers": sorted([paper_a, paper_b]),
        "output": output_path,
        "status": "created",
    }
    save_state(root, state)
    return collisions[key]


def build_pending_collisions(state: dict) -> list[dict]:
    paper_paths = sorted(
        path
        for path, paper in state.get("papers", {}).items()
        if isinstance(paper, dict) and paper.get("paper_card")
    )
    existing = state.get("collisions", {})
    pending = []
    for paper_a, paper_b in combinations(paper_paths, 2):
        key = collision_key(paper_a, paper_b)
        if key not in existing:
            pending.append({"papers": [paper_a, paper_b], "key": key})
    return pending


def remove_collisions_for_paper(collisions: dict, paper_path: str) -> None:
    for key in list(collisions):
        collision = collisions.get(key)
        if isinstance(collision, dict) and paper_path in collision.get("papers", []):
            del collisions[key]


def discover_papers(root: Path) -> list[Path]:
    folder = papers_root(root)
    if not folder.exists():
        return []
    return sorted(
        path
        for path in folder.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_PAPER_SUFFIXES
    )


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def collision_key(paper_a: str, paper_b: str) -> str:
    return "::".join(sorted([paper_a, paper_b]))


def papers_root(root: Path) -> Path:
    return Path(root) / WORKSPACE / PAPERS


def state_path(root: Path) -> Path:
    return Path(root) / WORKSPACE / STATE_FILE


def main(
    argv: list[str] | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    del stderr
    parser = argparse.ArgumentParser(prog="python state.py")
    parser.add_argument("--root", default=str(ROOT), help="project root")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("scan")

    mark_card = subparsers.add_parser("mark-card")
    mark_card.add_argument("paper_path")
    mark_card.add_argument("output_path")

    mark_pair = subparsers.add_parser("mark-collision")
    mark_pair.add_argument("paper_a")
    mark_pair.add_argument("paper_b")
    mark_pair.add_argument("output_path")

    args = parser.parse_args(argv)
    root = Path(args.root)
    stream = stdout

    if args.command == "scan":
        payload = scan_workspace(root)
    elif args.command == "mark-card":
        payload = mark_paper_card(root, args.paper_path, args.output_path)
    else:
        payload = mark_collision(root, args.paper_a, args.paper_b, args.output_path)

    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    if stream is None:
        print(text)
    else:
        stream.write(text)
        stream.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
