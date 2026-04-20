---
name: research-workflow
description: Use when analyzing research papers, extracting paper cards, generating innovation collisions across papers, drafting prototype ideas, or writing research outputs into a workspace for review.
---

# Research Workflow

You are helping the user turn research papers into useful research documents.

Your job is to read materials from `workspace/papers/`, reason with the model, and write Markdown outputs to `workspace/outputs/`.

Do not build a complex runtime. Do not invent hidden state. Use plain files.

For PDF papers, do not rely on one opaque PDF read. First create lightweight extracted materials under `workspace/extracted/`, then analyze those files.

## Output Directory

Write all results to:

```text
workspace/outputs/
```

PDF extraction writes to:

```text
workspace/extracted/<paper-name>/
```

Each extracted PDF folder may contain:

```text
text.md
tables.md
equations.md
figures.md
manifest.json
```

Create the directory if it does not exist.

Use numbered filenames:

```text
001-paper-card-<short-name>.md
002-collision-ideas.md
003-prototype-<short-name>.md
004-draft-<short-name>.md
```

## Required Markdown Header

Every output file must start with:

```markdown
---
title: Short title
type: paper_card | collision | prototype | draft | note
status: pending
source_papers:
  - paper file or paper title
---
```

Use `status: pending` for outputs that need human review.

## Workflow

### 1. Scan State

Before reading papers, run:

```bash
uv run python state.py scan
```

This updates `workspace/state.json`.

Use the scan result:

- `new_papers`: create paper cards for these.
- `changed_papers`: recreate paper cards for these.
- `unchanged_papers`: do not repeat paper cards unless the user asks.
- `pending_collisions`: generate collision documents for these pairs.

Do not repeat collisions already recorded in `workspace/state.json`.

### 2. Extract PDFs

Before analyzing PDF files, run:

```bash
uv run python extract_pdfs.py
```

This creates or refreshes `workspace/extracted/<paper-name>/` only when the PDF hash changed.

Use the extraction result:

- `extracted`: read the new extracted files.
- `changed`: reread the extracted files and regenerate the paper card.
- `skipped`: reuse existing extracted files.
- `failed`: tell the user which PDFs need manual extraction or OCR.

Important limits:

- `text.md` is the main reading source.
- `tables.md` is best-effort; verify important numeric claims against the PDF when possible.
- `equations.md` is best-effort; symbols, subscripts, matrices, and layout may be wrong.
- `figures.md` captures captions only; image content is not interpreted.
- Always inspect `manifest.json` for uncertainty notes.

### 3. Read Inputs

Inspect `workspace/papers/`.

Accept:

- PDF files
- Markdown notes
- TXT files
- user-provided summaries

For PDFs, prefer the matching files in `workspace/extracted/`:

```text
workspace/extracted/<paper-name>/text.md
workspace/extracted/<paper-name>/tables.md
workspace/extracted/<paper-name>/equations.md
workspace/extracted/<paper-name>/figures.md
workspace/extracted/<paper-name>/manifest.json
```

If extraction failed, ask the user for OCR, paper text, or a clearer source file.

### 4. Create Paper Cards

For each paper, write one paper card.

A paper card must include:

- Title
- One-sentence summary
- Core problem
- Method
- Evidence
- Evidence from tables
- Key formulas or method equations
- Figure or diagram notes
- Limitations
- Useful concepts
- Open questions
- Possible follow-up experiments
- Extraction uncertainty and pages/sections needing human review

After writing a paper card, mark it:

```bash
uv run python state.py mark-card <paper_path> <output_file>
```

Example:

```bash
uv run python state.py mark-card paper-a.pdf 001-paper-card-paper-a.md
```

### 5. Generate Innovation Collisions

After at least two paper cards exist, compare them.

Look for:

- Problem from paper A + method from paper B
- Limitation from paper A + tool from paper B
- Shared unsolved gap across papers
- Conflicting assumptions
- A method that may transfer across domain, cipher, dataset, metric, or experimental setting
- A table result from one paper that could evaluate a method from another
- A formula or constraint from one paper that could repair a limitation in another

Write collision ideas as ranked candidates.

Each candidate should include:

- Idea title
- Source papers
- Collision type
- Why it might be novel
- Why it might fail
- First experiment to try
- Score from 0.0 to 1.0

After writing a collision document, mark the pair:

```bash
uv run python state.py mark-collision <paper_a> <paper_b> <output_file>
```

Example:

```bash
uv run python state.py mark-collision paper-a.pdf paper-b.pdf 002-collision-paper-a-paper-b.md
```

### 6. Recommend Top Ideas

Pick the top 1 to 3 ideas.

Prefer ideas that are:

- testable
- specific
- grounded in the papers
- cheap to validate first
- clear about risk

### 7. Write Prototype

For an approved or promising idea, write a prototype document.

Include:

- Research question
- Hypothesis
- Minimal experiment
- Required data or code
- Evaluation metric
- Expected result
- Failure modes

### 8. Write Draft

For a mature prototype, write a draft document.

Include:

- Abstract
- Motivation
- Related observations from source papers
- Proposed method
- Experiment plan
- Risks and limitations
- Next actions

## Tone

Be concrete. Avoid vague claims like "this is innovative" unless you explain why.

Prefer:

```text
This may be novel because paper A assumes X, while paper B provides Y, and neither tests Z.
```

Avoid:

```text
This is a groundbreaking new direction.
```

## Completion Checklist

Before finishing, ensure:

- Outputs are written to `workspace/outputs/`.
- Each output has the required Markdown header.
- Every idea names its source papers.
- Paper cards mention table evidence when tables exist.
- Paper cards mention key formulas when formulas exist.
- Paper cards include extraction uncertainty for PDFs.
- Every proposed innovation has a first experiment.
- Risks are explicitly written down.
