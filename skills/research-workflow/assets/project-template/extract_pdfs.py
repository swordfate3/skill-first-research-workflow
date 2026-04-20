from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Callable, TextIO


ROOT = Path(__file__).resolve().parent
WORKSPACE = "workspace"
PAPERS = "papers"
EXTRACTED = "extracted"

Extractor = Callable[[Path], str]


def extract_all(
    root: Path = ROOT,
    extractor: Extractor | None = None,
    force: bool = False,
) -> dict:
    root = Path(root)
    summary = {"extracted": [], "changed": [], "skipped": [], "failed": []}

    for pdf in discover_pdfs(root):
        relative_path = pdf.relative_to(papers_root(root)).as_posix()
        digest = hash_file(pdf)
        output_dir = extracted_dir(root, relative_path)
        manifest = load_manifest(output_dir)

        if not force and manifest.get("source_hash") == digest:
            summary["skipped"].append(relative_path)
            continue

        was_extracted = bool(manifest)
        try:
            text = extractor(pdf) if extractor is not None else extract_pdf_text(pdf)
            write_extracted_documents(output_dir, relative_path, digest, text)
        except Exception as exc:  # pragma: no cover - exercised by real PDF tools.
            write_failure_manifest(output_dir, relative_path, digest, exc)
            summary["failed"].append(relative_path)
            continue

        if was_extracted:
            summary["changed"].append(relative_path)
        else:
            summary["extracted"].append(relative_path)

    return summary


def extract_pdf_text(pdf: Path) -> str:
    try:
        return extract_with_pdftotext(pdf)
    except (FileNotFoundError, RuntimeError):
        return extract_with_pypdf(pdf)


def extract_with_pdftotext(pdf: Path) -> str:
    result = subprocess.run(
        ["pdftotext", "-layout", str(pdf), "-"],
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        message = result.stderr.strip() or "pdftotext failed"
        raise RuntimeError(message)
    return result.stdout


def extract_with_pypdf(pdf: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("No PDF text extractor is available. Install poppler-utils or pypdf.") from exc

    reader = PdfReader(str(pdf))
    pages = []
    for index, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""
        pages.append(f"\n\n--- Page {index} ---\n\n{page_text.strip()}")
    return "\n".join(pages).strip()


def write_extracted_documents(
    output_dir: Path,
    relative_path: str,
    digest: str,
    text: str,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    table_lines = extract_table_lines(text)
    equation_lines = extract_equation_lines(text)
    figure_lines = extract_figure_lines(text)

    files = {
        "text.md": render_text(relative_path, text),
        "tables.md": render_section(
            "Extracted Tables",
            relative_path,
            table_lines,
            "No obvious table lines were detected. Check the source PDF if results or baselines matter.",
        ),
        "equations.md": render_section(
            "Extracted Equations",
            relative_path,
            equation_lines,
            "No obvious equation lines were detected. Check the source PDF if formulas drive the method.",
        ),
        "figures.md": render_section(
            "Extracted Figures",
            relative_path,
            figure_lines,
            "No figure or caption lines were detected. Check the source PDF if diagrams explain the method.",
        ),
    }
    for name, content in files.items():
        (output_dir / name).write_text(content, encoding="utf-8")

    manifest = {
        "source": relative_path,
        "source_hash": digest,
        "status": "extracted",
        "strategy": "pdftotext-layout-or-pypdf-with-heuristics",
        "files": sorted(files),
        "uncertainty": {
            "tables": "best-effort text/layout heuristic; verify important numeric results",
            "equations": "best-effort text heuristic; verify symbols, subscripts, and matrices",
            "figures": "captions only; image content is not interpreted",
        },
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_failure_manifest(
    output_dir: Path,
    relative_path: str,
    digest: str,
    error: Exception,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "source": relative_path,
        "source_hash": digest,
        "status": "failed",
        "error": str(error),
        "files": [],
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def render_text(relative_path: str, text: str) -> str:
    body = text.strip() or "No text was extracted. The PDF may be scanned or image-only."
    return f"# Extracted Text\n\nSource: `{relative_path}`\n\n{body}\n"


def render_section(
    title: str,
    relative_path: str,
    lines: list[str],
    empty_message: str,
) -> str:
    body = "\n".join(f"- {line}" for line in lines) if lines else empty_message
    return f"# {title}\n\nSource: `{relative_path}`\n\n{body}\n"


def extract_table_lines(text: str) -> list[str]:
    lines = clean_lines(text)
    results: list[str] = []
    include_next = 0
    for line in lines:
        lower = line.lower()
        looks_like_table = lower.startswith("table ") or lower.startswith("tab.")
        looks_like_numeric_row = count_numbers(line) >= 2 and len(line.split()) >= 3
        if looks_like_table:
            results.append(line)
            include_next = 4
            continue
        if include_next > 0 or looks_like_numeric_row:
            results.append(line)
            include_next = max(0, include_next - 1)
    return dedupe(results)


def extract_equation_lines(text: str) -> list[str]:
    equation_pattern = re.compile(r"\b(eq\.?|equation)\b|\([0-9]+\)", re.IGNORECASE)
    math_symbols = ("=", "+", "-", "*", "/", "^", "||", "<=", ">=", "sum", "min", "max", "log")
    results = []
    for line in clean_lines(text):
        symbol_count = sum(1 for symbol in math_symbols if symbol in line)
        if equation_pattern.search(line) and symbol_count >= 1:
            results.append(line)
        elif symbol_count >= 3 and count_numbers(line) >= 1:
            results.append(line)
    return dedupe(results)


def extract_figure_lines(text: str) -> list[str]:
    figure_pattern = re.compile(r"^(fig\.?|figure)\s+[0-9ivx]+[:.\s-]", re.IGNORECASE)
    return dedupe([line for line in clean_lines(text) if figure_pattern.search(line)])


def clean_lines(text: str) -> list[str]:
    return [" ".join(line.split()) for line in text.splitlines() if line.strip()]


def count_numbers(line: str) -> int:
    return len(re.findall(r"[-+]?\d+(?:\.\d+)?%?", line))


def dedupe(lines: list[str]) -> list[str]:
    seen = set()
    results = []
    for line in lines:
        if line in seen:
            continue
        seen.add(line)
        results.append(line)
    return results


def discover_pdfs(root: Path) -> list[Path]:
    folder = papers_root(root)
    if not folder.exists():
        return []
    return sorted(path for path in folder.rglob("*.pdf") if path.is_file())


def load_manifest(output_dir: Path) -> dict:
    path = output_dir / "manifest.json"
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def extracted_dir(root: Path, relative_path: str) -> Path:
    return extracted_root(root) / Path(relative_path).with_suffix("")


def papers_root(root: Path) -> Path:
    return Path(root) / WORKSPACE / PAPERS


def extracted_root(root: Path) -> Path:
    return Path(root) / WORKSPACE / EXTRACTED


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main(argv: list[str] | None = None, stdout: TextIO | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python extract_pdfs.py")
    parser.add_argument("--root", default=str(ROOT), help="project root")
    parser.add_argument("--force", action="store_true", help="extract even when PDF hash is unchanged")
    args = parser.parse_args(argv)

    payload = extract_all(Path(args.root), force=args.force)
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    if stdout is None:
        print(text)
    else:
        stdout.write(text)
        stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
