from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import TextIO


SKILL_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_ROOT = SKILL_ROOT / "assets" / "project-template"


def iter_template_files() -> list[Path]:
    return sorted(path for path in TEMPLATE_ROOT.rglob("*") if path.is_file())


def bootstrap_project(destination: Path, force: bool = False) -> dict:
    destination = Path(destination).resolve()
    destination.mkdir(parents=True, exist_ok=True)

    template_files = iter_template_files()
    conflicts = []
    for source in template_files:
        relative_path = source.relative_to(TEMPLATE_ROOT)
        target = destination / relative_path
        if target.exists() and not force:
            conflicts.append(relative_path.as_posix())

    if conflicts:
        return {
            "status": "conflict",
            "destination": str(destination),
            "conflicts": conflicts,
            "message": "Destination already contains files from the project template.",
        }

    copied = []
    for source in template_files:
        relative_path = source.relative_to(TEMPLATE_ROOT)
        target = destination / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied.append(relative_path.as_posix())

    return {
        "status": "bootstrapped",
        "destination": str(destination),
        "copied": copied,
        "template_root": str(TEMPLATE_ROOT),
    }


def main(argv: list[str] | None = None, stdout: TextIO | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python bootstrap_project.py")
    parser.add_argument(
        "--dest",
        default=".",
        help="destination directory for the research workflow project template",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite existing files in the destination",
    )
    args = parser.parse_args(argv)

    payload = bootstrap_project(Path(args.dest), force=args.force)
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    if stdout is None:
        print(text)
    else:
        stdout.write(text)
        stdout.write("\n")
    return 0 if payload["status"] == "bootstrapped" else 1


if __name__ == "__main__":
    raise SystemExit(main())
