# Project Status

Last updated: 2026-04-20

## Current Direction

This is now a standalone skill-first research workflow project.

Core idea:

```text
LLM/Agent does the research thinking
Skill defines the workflow
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

## Verified

Run from the project root:

```bash
python -m unittest discover -s tests -v
python -m py_compile extract_pdfs.py state.py server.py
python extract_pdfs.py
```

Current verification result before migration:

```text
5 unittest tests passed.
Python files compiled successfully.
PDF extractor CLI returned an empty summary when no PDFs were present.
```

## Next Steps

1. Try the full flow with 2 real PDF papers in `workspace/papers/`.
2. Improve table extraction if `tables.md` misses important experimental tables.
3. Add web approval buttons for `pending`, `approved`, and `rejected` output documents.
4. Add a simple document status editor for Markdown frontmatter.
5. Decide whether to add OCR/MinerU/Marker as an optional advanced extraction path.

## Useful Commands

```bash
python state.py scan
python extract_pdfs.py
python server.py
python -m unittest discover -s tests -v
```

Open the web viewer at:

```text
http://127.0.0.1:8765
```
