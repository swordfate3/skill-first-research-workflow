# Project Status

Last updated: 2026-04-20

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
7 unittest tests passed.
Python files compiled successfully.
workflow.py prepare scans papers, extracts/skips PDFs, keeps uncarded papers in the work queue, and returns next Agent actions.
```

## Next Steps

1. Invoke the skill on the current real PDFs and inspect generated paper cards.
2. Improve table extraction if `tables.md` misses important experimental tables.
3. Add web approval buttons for `pending`, `approved`, and `rejected` output documents.
4. Decide whether to add OCR/MinerU/Marker as an optional advanced extraction path.

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
