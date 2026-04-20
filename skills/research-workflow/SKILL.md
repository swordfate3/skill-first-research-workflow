---
name: research-workflow
description: Use when the user wants an Agent to process newly added research papers, create paper cards, find innovation collisions, or draft research outputs from workspace files.
---

# Research Workflow

Run the workflow automatically. The user should only need to add papers to `workspace/papers/` and invoke this skill.

Do not ask the user to run setup commands unless a command fails or a PDF needs OCR/manual text.

## Start Here

Immediately run:

```bash
uv run python workflow.py prepare
```

Use the JSON result:

- `papers_to_card`: create or recreate paper cards for these papers only.
- `pending_collisions`: create collision documents for these pairs only.
- `pdf_extraction.failed`: tell the user these PDFs need OCR or manual text.
- If `next_actions` says no work is needed, stop and report that nothing new was found.

## Inputs

Read from:

```text
workspace/papers/
workspace/extracted/
```

For PDFs, prefer:

```text
workspace/extracted/<paper-name>/text.md
workspace/extracted/<paper-name>/tables.md
workspace/extracted/<paper-name>/equations.md
workspace/extracted/<paper-name>/figures.md
workspace/extracted/<paper-name>/manifest.json
```

`tables.md`, `equations.md`, and `figures.md` are best-effort extraction notes. Mention uncertainty when using them.

## Outputs

Write Markdown files to:

```text
workspace/outputs/
```

Every output starts with:

```markdown
---
title: Short title
type: paper_card | collision | prototype | draft | note
status: pending
source_papers:
  - paper file or paper title
---
```

## Paper Cards

For each `papers_to_card` item, write:

```text
001-paper-card-<short-name>.md
```

Include only useful, concrete information:

- one-sentence summary
- core problem
- method
- evidence, especially tables
- key formulas
- limitations
- useful concepts
- follow-up experiments
- extraction uncertainty for PDFs

After each paper card, immediately run:

```bash
uv run python state.py mark-card <paper_path> <output_file>
```

## Innovation Collisions

For each `pending_collisions` pair, write:

```text
002-collision-<paper-a>-<paper-b>.md
```

Look for:

- problem from A + method from B
- limitation from A + tool/formula/table evidence from B
- shared gap
- conflicting assumptions
- cheap first experiment

Each idea needs:

- title
- source papers
- why it might be novel
- why it might fail
- first experiment
- score from 0.0 to 1.0

After each collision document, immediately run:

```bash
uv run python state.py mark-collision <paper_a> <paper_b> <output_file>
```

## Optional Drafting

Only write prototype or draft documents when a collision idea is clearly strong or the user asks for it.

## Finish

Report briefly:

- files created
- papers skipped because unchanged
- collisions generated
- PDFs needing OCR/manual text
