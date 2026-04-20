---
name: research-workflow
description: Use when the user wants an Agent to process newly added research papers, create paper cards, find innovation collisions, or draft research outputs from workspace files.
---

# Research Workflow

Run the workflow automatically. The user should only need to add papers to `workspace/papers/` and invoke this skill.

Do not ask the user to run setup commands unless a command fails or a PDF needs OCR/manual text.

## Language

默认使用中文写所有输出文档和最终回复。

关键英文术语保留原文，第一次出现时写成：

```text
中文术语（English term）
```

Do not translate paper titles, method names, metric names, dataset names, model names, or cipher names when translation would make them harder to recognize.

Every paper card and collision document should include a short `## 术语对照` section when the source paper is mainly English.

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

- 一句话总结
- 核心问题
- 方法
- 证据，尤其是表格证据
- 关键公式
- 局限性
- 有用概念
- 后续实验
- PDF 提取不确定性
- 术语对照

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

- A 的问题 + B 的方法
- A 的局限 + B 的工具/公式/表格证据
- 共同未解决缺口
- 冲突假设
- 便宜的第一个实验

Each idea needs:

- 标题
- 来源论文
- 可能新在哪里
- 为什么可能失败
- 第一个实验
- 0.0 到 1.0 分数

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
