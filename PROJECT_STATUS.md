# Project Status

Last updated: 2026-04-22

## Current Direction

This is now a standalone skill-first research workflow project.

Core idea:

```text
LLM/Agent does the research thinking
Skill runs the workflow automatically after invocation
Plain files keep state and outputs
Web page displays generated documents
```

The project should stay decoupled from the old `research-workflow-plugin` runtime.

## Completed

- Created the lightweight `research-workflow` skill.
- Added Markdown output templates for paper cards, collision ideas, prototypes, and drafts.
- Added `state.py` for paper scanning, hash-based duplicate detection, changed-paper detection, and collision-pair tracking.
- Added a simple local web viewer with `server.py` and static files under `web/`.
- Added `extract_pdfs.py` for lightweight PDF extraction into:

```text
workspace/extracted/<paper-name>/
  text.md
  tables.md
  equations.md
  figures.md
  manifest.json
```

- Updated the skill so Agents must analyze PDF table evidence, key formulas, figure notes, and extraction uncertainty.
- Added tests for state tracking and PDF extraction behavior.
- Added `uv` project configuration with `pyproject.toml` and `.python-version`.
- Added `workflow.py prepare` so the skill has one automatic entry point.
- Simplified `SKILL.md`: user adds papers and invokes the skill; the Agent runs the rest.
- Added default Chinese output rules with English technical terms preserved.
- Added a bundled project template and bootstrap script so the skill can be installed with `npx skills add <owner>/<repo>@research-workflow`.
- Added the first scheme-B workflow upgrade: paper memory JSON, Top-K collision selection, and pending direction generation.
- Ran the current two real AES papers through the full `memory -> paper card -> collision -> direction` chain.
- Added runtime paper memory records under `workspace/memory/papers/` and generated the first real direction draft under `workspace/outputs/`.
- Upgraded the local web viewer so documents can be filtered by `paper_card`, `collision`, and `direction`.
- Added an `all` filter and grouped document sections in the local web viewer so mixed output sets stay readable.
- Added regression tests for direction scoring expectations, document filtering, and type-aware panel behavior.

## Verified

Run from the project root:

```bash
uv sync
uv run python -m unittest discover -s tests -v
uv run python -m py_compile extract_pdfs.py state.py server.py workflow.py
uv run python workflow.py prepare
```

Current verification result:

```text
21 unittest tests passed.
workflow.py prepare now returns no pending memory, card, collision, or direction work for the current two-paper workspace.
The local web API sorts documents by paper_card -> collision -> direction, supports type filtering, and the web panel now supports grouped `all` browsing.
```

## Next Steps

1. Tighten the direction template so recommended experiments, risks, and audit steps are more standardized.
2. Add a tiny end-to-end smoke check for the web panel against real runtime outputs.
3. Decide whether to add OCR/MinerU/Marker as an optional advanced extraction path for table-heavy PDFs.

## Useful Commands

```bash
uv run python workflow.py prepare
uv run python server.py
uv run python -m unittest discover -s tests -v
```

Open the web viewer at:

```text
http://127.0.0.1:8765
```
