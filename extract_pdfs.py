from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Callable, TextIO


ROOT = Path(__file__).resolve().parent
WORKSPACE = "workspace"
PAPERS = "papers"
EXTRACTED = "extracted"
DEFAULT_STRATEGY = "auto"
MINERU_WRAPPER = Path("/home/fate/.agents/skills/mineru-doc-to-md/scripts/mineru_to_md.sh")

Extractor = Callable[[Path], str]
MineruRunner = Callable[[Path, Path], None]


def extract_all(
    root: Path = ROOT,
    extractor: Extractor | None = None,
    force: bool = False,
    strategy: str = DEFAULT_STRATEGY,
    mineru_runner: MineruRunner | None = None,
) -> dict:
    root = Path(root)
    strategy = normalize_strategy(strategy)
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
            if strategy == "lightweight":
                text = extractor(pdf) if extractor is not None else extract_pdf_text(pdf)
                write_extracted_documents(
                    output_dir,
                    relative_path,
                    digest,
                    text,
                    strategy_name="pdftotext-layout-or-pypdf-with-heuristics",
                )
            elif strategy == "mineru":
                write_mineru_documents(
                    output_dir,
                    relative_path,
                    digest,
                    pdf,
                    runner=mineru_runner,
                    strategy_name="mineru-docker-wrapper",
                )
            else:
                try:
                    text = extractor(pdf) if extractor is not None else extract_pdf_text(pdf)
                    write_extracted_documents(
                        output_dir,
                        relative_path,
                        digest,
                        text,
                        strategy_name="pdftotext-layout-or-pypdf-with-heuristics",
                    )
                except Exception:
                    write_mineru_documents(
                        output_dir,
                        relative_path,
                        digest,
                        pdf,
                        runner=mineru_runner,
                        strategy_name="auto-fallback-to-mineru",
                    )
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


def write_mineru_documents(
    output_dir: Path,
    relative_path: str,
    digest: str,
    pdf: Path,
    runner: MineruRunner | None,
    strategy_name: str,
) -> None:
    mineru_payload = extract_with_mineru(pdf, runner=runner)
    output_dir.mkdir(parents=True, exist_ok=True)
    files = {
        "text.md": render_text(relative_path, mineru_payload["text"]),
        "tables.md": render_section(
            "Extracted Tables",
            relative_path,
            mineru_payload["table_lines"],
            "MinerU did not emit obvious table lines. Check the source PDF if results or baselines matter.",
        ),
        "equations.md": render_section(
            "Extracted Equations",
            relative_path,
            mineru_payload["equation_lines"],
            "MinerU did not emit obvious equation lines. Check the source PDF if formulas drive the method.",
        ),
        "figures.md": render_section(
            "Extracted Figures",
            relative_path,
            mineru_payload["figure_lines"],
            "MinerU did not emit figure caption lines. Check the source PDF if diagrams explain the method.",
        ),
    }
    for name, content in files.items():
        (output_dir / name).write_text(content, encoding="utf-8")

    manifest = {
        "source": relative_path,
        "source_hash": digest,
        "status": "extracted",
        "strategy": strategy_name,
        "files": sorted(files),
        "uncertainty": {
            "tables": "MinerU markdown was normalized back into workflow table notes; verify important numeric cells.",
            "equations": "MinerU markdown may still lose symbols or layout; verify formulas that matter.",
            "figures": "Figure captions are best-effort; image semantics are still not fully interpreted.",
        },
        "mineru_artifacts": mineru_payload["artifact_files"],
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def extract_with_mineru(pdf: Path, runner: MineruRunner | None = None) -> dict:
    with tempfile.TemporaryDirectory(prefix="mineru-extract-") as tmpdir:
        output_dir = Path(tmpdir)
        effective_runner = runner or run_mineru_wrapper
        effective_runner(pdf, output_dir)
        return collect_mineru_output(output_dir)


def run_mineru_wrapper(pdf: Path, output_dir: Path) -> None:
    if not MINERU_WRAPPER.exists():
        raise RuntimeError(f"MinerU wrapper not found: {MINERU_WRAPPER}")

    result = subprocess.run(
        [str(MINERU_WRAPPER), str(pdf), "--output", str(output_dir)],
        check=False,
        capture_output=True,
        text=True,
        timeout=1800,
    )
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "MinerU wrapper failed"
        raise RuntimeError(message)


def collect_mineru_output(output_dir: Path) -> dict:
    artifact_files = sorted(
        path.relative_to(output_dir).as_posix()
        for path in output_dir.rglob("*")
        if path.is_file()
    )
    markdown_files = sorted(output_dir.rglob("*.md"))
    if not markdown_files:
        raise RuntimeError("MinerU completed without Markdown output.")

    chunks = []
    for path in markdown_files:
        text = path.read_text(encoding="utf-8", errors="replace").strip()
        if text:
            chunks.append(text)
    combined_text = "\n\n".join(chunks).strip()
    if not combined_text:
        raise RuntimeError("MinerU Markdown output is empty.")

    return {
        "text": combined_text,
        "table_lines": extract_table_lines(combined_text),
        "equation_lines": extract_equation_lines(combined_text),
        "figure_lines": extract_figure_lines(combined_text),
        "artifact_files": artifact_files,
    }


def write_extracted_documents(
    output_dir: Path,
    relative_path: str,
    digest: str,
    text: str,
    strategy_name: str = "pdftotext-layout-or-pypdf-with-heuristics",
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
        "strategy": strategy_name,
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


def normalize_strategy(strategy: str) -> str:
    value = (strategy or DEFAULT_STRATEGY).strip().lower()
    if value not in {"auto", "lightweight", "mineru"}:
        raise ValueError(f"Unsupported extraction strategy: {strategy}")
    return value


def main(argv: list[str] | None = None, stdout: TextIO | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python extract_pdfs.py")
    parser.add_argument("--root", default=str(ROOT), help="project root")
    parser.add_argument("--force", action="store_true", help="extract even when PDF hash is unchanged")
    parser.add_argument(
        "--strategy",
        default=DEFAULT_STRATEGY,
        choices=["auto", "lightweight", "mineru"],
        help="PDF extraction strategy",
    )
    args = parser.parse_args(argv)

    payload = extract_all(Path(args.root), force=args.force, strategy=args.strategy)
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    if stdout is None:
        print(text)
    else:
        stdout.write(text)
        stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
