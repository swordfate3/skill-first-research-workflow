from __future__ import annotations

import argparse
import hashlib
import json
import re
from itertools import combinations
from pathlib import Path
from typing import TextIO


ROOT = Path(__file__).resolve().parent
WORKSPACE = "workspace"
PAPERS = "papers"
MEMORY = "memory"
MEMORY_PAPERS = "papers"
STATE_FILE = "state.json"
SUPPORTED_PAPER_SUFFIXES = {".pdf", ".md", ".txt"}

MAX_COLLISIONS_PER_PAPER = 3
MAX_PENDING_COLLISIONS = 10
MIN_COLLISION_SCORE = 0.35
MIN_DIRECTION_SCORE = 0.65
MAX_PENDING_DIRECTIONS = 5

TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_+-]{3,}|[\u4e00-\u9fff]{2,}")


def load_state(root: Path = ROOT) -> dict:
    path = state_path(root)
    if not path.exists():
        return {"version": 2, "papers": {}, "collisions": {}, "directions": {}}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return {"version": 2, "papers": {}, "collisions": {}, "directions": {}}
    payload["version"] = max(int(payload.get("version", 1)), 2)
    payload.setdefault("papers", {})
    payload.setdefault("collisions", {})
    payload.setdefault("directions", {})
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
            remove_generated_state_for_paper(state, relative_path)
            changed_papers.append({"path": relative_path, "hash": digest})
            continue
        unchanged_papers.append({"path": relative_path, "hash": digest})

    papers_to_memory = build_papers_to_memory(state, new_papers, changed_papers)
    pending_collisions = build_pending_collisions(root, state)
    pending_directions = build_pending_directions(state)
    save_state(root, state)
    return {
        "new_papers": new_papers,
        "changed_papers": changed_papers,
        "unchanged_papers": unchanged_papers,
        "papers_to_memory": papers_to_memory,
        "pending_collisions": pending_collisions,
        "pending_directions": pending_directions,
    }


def mark_paper_memory(root: Path, paper_path: str, memory_path: str) -> dict:
    state = load_state(root)
    papers = state.setdefault("papers", {})
    paper = papers.setdefault(paper_path, {})
    paper["paper_memory"] = memory_path
    paper["status"] = "memory_created"
    save_state(root, state)
    return paper


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
    memories = load_paper_memories(root, state)
    score_data = score_collision_candidate(memories.get(paper_a, {}), memories.get(paper_b, {}))
    collisions[key] = {
        "papers": sorted([paper_a, paper_b]),
        "output": output_path,
        "score": score_data["score"],
        "reasons": score_data["reasons"],
        "status": "created",
    }
    save_state(root, state)
    return collisions[key]


def mark_direction(root: Path, collision_key_name: str, output_path: str) -> dict:
    state = load_state(root)
    directions = state.setdefault("directions", {})
    directions[collision_key_name] = {
        "collision_key": collision_key_name,
        "output": output_path,
        "status": "created",
    }
    save_state(root, state)
    return directions[collision_key_name]


def build_papers_to_memory(
    state: dict,
    new_papers: list[dict],
    changed_papers: list[dict],
) -> list[dict]:
    queued = {
        item["path"]
        for item in new_papers + changed_papers
        if "path" in item
    }
    for paper_path, paper in state.get("papers", {}).items():
        if isinstance(paper, dict) and not paper.get("paper_memory"):
            queued.add(paper_path)
    return [
        {"path": paper_path, "memory_path": suggested_memory_path(paper_path)}
        for paper_path in sorted(queued)
    ]


def build_pending_collisions(root: Path, state: dict) -> list[dict]:
    papers = state.get("papers", {})
    eligible_paths = sorted(
        path
        for path, paper in papers.items()
        if isinstance(paper, dict) and paper.get("paper_memory") and paper.get("paper_card")
    )
    if len(eligible_paths) < 2:
        return []

    memories = load_paper_memories(root, state)
    existing = state.get("collisions", {})
    selected_counts = collision_counts_by_paper(existing)
    candidates = []

    for paper_a, paper_b in combinations(eligible_paths, 2):
        key = collision_key(paper_a, paper_b)
        if key in existing:
            continue
        score_data = score_collision_candidate(memories.get(paper_a, {}), memories.get(paper_b, {}))
        if score_data["score"] < MIN_COLLISION_SCORE:
            continue
        candidates.append(
            {
                "papers": [paper_a, paper_b],
                "key": key,
                "score": score_data["score"],
                "reasons": score_data["reasons"],
            }
        )

    candidates.sort(
        key=lambda item: (-item["score"], item["papers"][0], item["papers"][1])
    )

    pending = []
    for candidate in candidates:
        paper_a, paper_b = candidate["papers"]
        if selected_counts.get(paper_a, 0) >= MAX_COLLISIONS_PER_PAPER:
            continue
        if selected_counts.get(paper_b, 0) >= MAX_COLLISIONS_PER_PAPER:
            continue
        pending.append(candidate)
        selected_counts[paper_a] = selected_counts.get(paper_a, 0) + 1
        selected_counts[paper_b] = selected_counts.get(paper_b, 0) + 1
        if len(pending) >= MAX_PENDING_COLLISIONS:
            break

    return pending


def build_pending_directions(state: dict) -> list[dict]:
    collisions = state.get("collisions", {})
    directions = state.get("directions", {})
    pending = []
    for collision_key_name, collision in collisions.items():
        if not isinstance(collision, dict):
            continue
        if collision.get("status") != "created":
            continue
        if collision.get("score", 0.0) < MIN_DIRECTION_SCORE:
            continue
        if collision_key_name in directions:
            continue
        pending.append(
            {
                "collision_key": collision_key_name,
                "papers": collision.get("papers", []),
                "score": collision.get("score", 0.0),
                "collision_output": collision.get("output", ""),
            }
        )
    pending.sort(key=lambda item: (-item["score"], item["collision_key"]))
    return pending[:MAX_PENDING_DIRECTIONS]


def remove_generated_state_for_paper(state: dict, paper_path: str) -> None:
    papers = state.setdefault("papers", {})
    paper = papers.setdefault(paper_path, {})
    paper.pop("paper_memory", None)
    paper.pop("paper_card", None)

    collisions = state.setdefault("collisions", {})
    directions = state.setdefault("directions", {})
    for key in list(collisions):
        collision = collisions.get(key)
        if isinstance(collision, dict) and paper_path in collision.get("papers", []):
            del collisions[key]
            directions.pop(key, None)


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


def suggested_memory_path(paper_path: str) -> str:
    relative = Path(paper_path).with_suffix(".json").as_posix()
    return f"{WORKSPACE}/{MEMORY}/{MEMORY_PAPERS}/{relative}"


def load_paper_memories(root: Path, state: dict) -> dict[str, dict]:
    results: dict[str, dict] = {}
    for paper_path, paper in state.get("papers", {}).items():
        if not isinstance(paper, dict) or not paper.get("paper_memory"):
            continue
        path = Path(root) / paper["paper_memory"]
        if not path.exists():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            results[paper_path] = payload
    return results


def collision_counts_by_paper(collisions: dict) -> dict[str, int]:
    counts: dict[str, int] = {}
    for collision in collisions.values():
        if not isinstance(collision, dict):
            continue
        for paper in collision.get("papers", []):
            counts[paper] = counts.get(paper, 0) + 1
    return counts


def score_collision_candidate(memory_a: dict, memory_b: dict) -> dict:
    if not memory_a or not memory_b:
        return {"score": 0.0, "reasons": ["缺少结构化 paper memory。"]}

    tags_a = normalized_values(memory_a.get("classification", {}).get("primary_tags", []))
    tags_b = normalized_values(memory_b.get("classification", {}).get("primary_tags", []))
    keywords_a = normalized_values(memory_a.get("classification", {}).get("keywords", []))
    keywords_b = normalized_values(memory_b.get("classification", {}).get("keywords", []))
    terms_a = collect_memory_terms(memory_a)
    terms_b = collect_memory_terms(memory_b)
    transferable_a = normalized_values(
        flatten_values(memory_a.get("innovation_seeds", {}).get("transferable_techniques", []))
    )
    transferable_b = normalized_values(
        flatten_values(memory_b.get("innovation_seeds", {}).get("transferable_techniques", []))
    )
    limitations_a = normalized_values(memory_a.get("content", {}).get("limitations", []))
    limitations_b = normalized_values(memory_b.get("content", {}).get("limitations", []))
    open_a = normalized_values(memory_a.get("innovation_seeds", {}).get("open_problems", []))
    open_b = normalized_values(memory_b.get("innovation_seeds", {}).get("open_problems", []))

    score = 0.0
    reasons = []

    shared_tags = sorted(tags_a & tags_b)
    if shared_tags:
        score += 0.3
        reasons.append(f"共享研究对象/标签：{', '.join(shared_tags[:3])}")

    shared_keywords = sorted(keywords_a & keywords_b)
    if shared_keywords:
        score += min(0.2, 0.05 * len(shared_keywords))
        reasons.append(f"关键词重叠：{', '.join(shared_keywords[:4])}")

    bridge_a = sorted(transferable_a & (tags_b | keywords_b | terms_b))
    if bridge_a:
        score += 0.15
        reasons.append(f"A 的可迁移技术可对接 B：{', '.join(bridge_a[:4])}")

    bridge_b = sorted(transferable_b & (tags_a | keywords_a | terms_a))
    if bridge_b:
        score += 0.15
        reasons.append(f"B 的可迁移技术可对接 A：{', '.join(bridge_b[:4])}")

    limitation_bridge_a = sorted(limitations_a & terms_b)
    if limitation_bridge_a:
        score += 0.1
        reasons.append(f"B 可能补 A 的局限：{', '.join(limitation_bridge_a[:4])}")

    limitation_bridge_b = sorted(limitations_b & terms_a)
    if limitation_bridge_b:
        score += 0.1
        reasons.append(f"A 可能补 B 的局限：{', '.join(limitation_bridge_b[:4])}")

    open_bridge = sorted((open_a & terms_b) | (open_b & terms_a))
    if open_bridge:
        score += 0.1
        reasons.append(f"开放问题与对方方法存在交叉：{', '.join(open_bridge[:4])}")

    if not reasons:
        reasons.append("仅有弱相关，先不优先碰撞。")

    return {"score": round(min(score, 0.95), 2), "reasons": reasons}


def collect_memory_terms(memory: dict) -> set[str]:
    values = []
    values.extend(memory.get("classification", {}).get("primary_tags", []))
    values.extend(memory.get("classification", {}).get("keywords", []))
    values.extend(memory.get("content", {}).get("limitations", []))
    values.extend(memory.get("innovation_seeds", {}).get("open_problems", []))
    values.extend(memory.get("innovation_seeds", {}).get("weakness_opportunities", []))
    values.extend(flatten_values(memory.get("innovation_seeds", {}).get("transferable_techniques", [])))
    return normalized_values(values)


def flatten_values(values: list | dict | str) -> list[str]:
    if isinstance(values, str):
        return [values]
    if isinstance(values, dict):
        results: list[str] = []
        for value in values.values():
            results.extend(flatten_values(value))
        return results
    if isinstance(values, list):
        results: list[str] = []
        for value in values:
            results.extend(flatten_values(value))
        return results
    return []


def normalized_values(values: list | dict | str) -> set[str]:
    tokens = set()
    for value in flatten_values(values):
        for token in TOKEN_PATTERN.findall(str(value).lower()):
            tokens.add(token)
    return tokens


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

    mark_memory = subparsers.add_parser("mark-memory")
    mark_memory.add_argument("paper_path")
    mark_memory.add_argument("memory_path")

    mark_card = subparsers.add_parser("mark-card")
    mark_card.add_argument("paper_path")
    mark_card.add_argument("output_path")

    mark_pair = subparsers.add_parser("mark-collision")
    mark_pair.add_argument("paper_a")
    mark_pair.add_argument("paper_b")
    mark_pair.add_argument("output_path")

    mark_direction_parser = subparsers.add_parser("mark-direction")
    mark_direction_parser.add_argument("collision_key")
    mark_direction_parser.add_argument("output_path")

    args = parser.parse_args(argv)
    root = Path(args.root)
    stream = stdout

    if args.command == "scan":
        payload = scan_workspace(root)
    elif args.command == "mark-memory":
        payload = mark_paper_memory(root, args.paper_path, args.memory_path)
    elif args.command == "mark-card":
        payload = mark_paper_card(root, args.paper_path, args.output_path)
    elif args.command == "mark-collision":
        payload = mark_collision(root, args.paper_a, args.paper_b, args.output_path)
    else:
        payload = mark_direction(root, args.collision_key, args.output_path)

    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    if stream is None:
        print(text)
    else:
        stream.write(text)
        stream.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
