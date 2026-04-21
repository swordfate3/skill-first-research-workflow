from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import TextIO


ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import extract_pdfs
import state


def prepare_workspace(
    root: Path = ROOT,
    extractor: extract_pdfs.Extractor | None = None,
) -> dict:
    root = Path(root)
    scan = state.scan_workspace(root)
    pdf_extraction = extract_pdfs.extract_all(root, extractor=extractor)

    papers_to_memory = scan["papers_to_memory"]
    papers_to_card = build_papers_to_card(root, scan)
    pending_collisions = scan["pending_collisions"]
    pending_directions = scan["pending_directions"]
    failed_pdfs = pdf_extraction["failed"]

    return {
        "papers_to_memory": papers_to_memory,
        "papers_to_card": papers_to_card,
        "pending_collisions": pending_collisions,
        "pending_directions": pending_directions,
        "pdf_extraction": pdf_extraction,
        "next_actions": build_next_actions(
            papers_to_memory,
            papers_to_card,
            pending_collisions,
            pending_directions,
            failed_pdfs,
        ),
    }


def build_next_actions(
    papers_to_memory: list[dict],
    papers_to_card: list[str],
    pending_collisions: list[dict],
    pending_directions: list[dict],
    failed_pdfs: list[str],
) -> list[str]:
    actions = []
    if papers_to_memory:
        count = len(papers_to_memory)
        label = "record" if count == 1 else "records"
        actions.append(f"Create {count} paper memory {label} before collision scoring.")
    if papers_to_card:
        count = len(papers_to_card)
        label = "paper" if count == 1 else "papers"
        actions.append(f"Create paper cards for {count} {label} needing cards.")
    if pending_collisions:
        count = len(pending_collisions)
        label = "document" if count == 1 else "documents"
        actions.append(f"Generate {count} pending collision {label}.")
    if pending_directions:
        count = len(pending_directions)
        label = "direction" if count == 1 else "directions"
        actions.append(f"Draft {count} high-priority research {label}.")
    if failed_pdfs:
        actions.append(f"Ask for OCR or manual text for {len(failed_pdfs)} failed PDFs.")
    if not actions:
        actions.append("No new memory records, paper cards, collisions, or directions are needed.")
    return actions


def build_papers_to_card(root: Path, scan: dict) -> list[str]:
    del scan
    current_state = state.load_state(root)
    queued = []
    for paper_path, paper in current_state.get("papers", {}).items():
        if not isinstance(paper, dict):
            continue
        if paper.get("paper_memory") and not paper.get("paper_card"):
            queued.append(paper_path)
    return sorted(set(queued))


def main(argv: list[str] | None = None, stdout: TextIO | None = None) -> int:
    parser = argparse.ArgumentParser(prog="uv run python workflow.py")
    parser.add_argument("--root", default=str(ROOT), help="project root")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("prepare")
    args = parser.parse_args(argv)

    payload = prepare_workspace(Path(args.root))
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    if stdout is None:
        print(text)
    else:
        stdout.write(text)
        stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
