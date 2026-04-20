# Skill-First Research Workflow

一个给大模型/Agent 用的论文研究工作流。

你只需要：

```text
放论文 -> 调用 skill -> 看输出文档
```

## 快速开始

### 1. 准备一次环境

```bash
uv sync
```

### 2. 放论文

把 PDF、Markdown 笔记或 TXT 摘要放进：

```text
workspace/papers/
```

### 3. 调用 skill

对 Claude Code、Codex 或其他 Agent 说：

```text
请使用 skills/research-workflow/SKILL.md 处理新论文。
```

Agent 会自动：

```text
扫描新论文
提取 PDF 正文/表格/公式/图表线索
跳过已经处理过的论文
生成 paper card
生成新的创新碰撞
记录已处理状态
```

输出默认是中文研究笔记；关键英文术语会保留原文，并在文档里给出术语对照。

输出在：

```text
workspace/outputs/
```

## 看结果

启动本地页面：

```bash
uv run python server.py
```

打开：

```text
http://127.0.0.1:8765
```

## 它如何避免重复

项目会记录论文 hash 和已碰撞组合。

- 新论文：生成 paper card。
- 论文没变：跳过。
- 论文变了：重新生成 paper card。
- 已经碰撞过的论文组合：跳过。
- 新增论文 D 后：只做 D 和旧论文的新组合。

状态文件在：

```text
workspace/state.json
```

## PDF 会提取什么

PDF 会提取到：

```text
workspace/extracted/<paper-name>/
  text.md
  tables.md
  equations.md
  figures.md
  manifest.json
```

注意：表格、公式、图像是轻量提取，不保证完美。Agent 会在 paper card 里标记不确定的地方。

## 手动调试命令

平时不用手动跑这些。只有排查问题时用：

```bash
uv run python workflow.py prepare
uv run python state.py scan
uv run python extract_pdfs.py
uv run python -m unittest discover -s tests -v
```

## 目录

```text
skills/research-workflow/SKILL.md   # Agent 工作流
workflow.py                         # 自动准备入口
state.py                            # 去重和碰撞状态
extract_pdfs.py                     # PDF 轻量提取
server.py                           # 本地 Web 页面
workspace/papers/                   # 放论文
workspace/extracted/                # PDF 提取结果
workspace/outputs/                  # Agent 输出文档
```
