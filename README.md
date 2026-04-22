# Skill-First Research Workflow

一个给大模型 / Agent 用的论文研究工作流 skill。

它做的事很直接：

```text
装 skill -> 放论文 -> 调用 skill -> 自动生成 memory / card / collision / direction -> Web 查看结果
```

---

## 30 秒上手

先安装：

```bash
npx skills add swordfate3/skill-first-research-workflow@research-workflow
```

再准备一个工作目录：

```bash
mkdir ~/my-research
cd ~/my-research
python ~/.agents/skills/research-workflow/scripts/bootstrap_project.py --dest .
uv sync
```

把论文放进：

```text
workspace/papers/
```

然后对 Agent 说：

```text
请使用 research-workflow skill 处理新论文。
```

看结果：

- 文档：`workspace/outputs/`
- 结构化 memory：`workspace/memory/papers/`
- 网页：`uv run python server.py`

---

## 它怎么工作

调用 skill 后，工作流会自动做这些事：

1. 扫描 `workspace/papers/`
2. 判断哪些论文是新的、哪些改过、哪些已处理
3. 提取 PDF 正文 / 表格 / 公式 / 图表线索
4. 生成结构化 `paper memory`
5. 生成 `paper card`
6. 生成 Top-K 高价值 `collision`
7. 基于高分碰撞生成 `direction`
8. 更新 `workspace/state.json`，避免重复处理

PDF 提取策略：

- 默认先走轻量提取：`pdftotext` / `pypdf`
- 失败时自动回退到 MinerU
- 也支持显式 `mineru` 提取策略

---

## 两个目录

### 1. skill 安装目录

安装后大概会在这里：

```text
~/.agents/skills/research-workflow/
```

这里放的是：

- `SKILL.md`
- `scripts/bootstrap_project.py`
- `assets/project-template/`
- `agents/openai.yaml`

它只是能力包，不是你的研究项目目录。

### 2. 工作目录

比如：

```bash
mkdir ~/my-research
cd ~/my-research
```

这里才是你真正放论文、跑流程、看输出的地方。

---

## 标准使用流程

### 1. 安装 skill

```bash
npx skills add swordfate3/skill-first-research-workflow@research-workflow
```

### 2. 创建工作目录

```bash
mkdir ~/my-research
cd ~/my-research
```

### 3. 初始化项目骨架

```bash
python ~/.agents/skills/research-workflow/scripts/bootstrap_project.py --dest .
```

初始化后，当前目录会有：

```text
pyproject.toml
workflow.py
state.py
extract_pdfs.py
server.py
templates/
web/
workspace/
```

### 4. 安装依赖

```bash
uv sync
```

### 5. 放论文

放到：

```text
workspace/papers/
```

支持：

- PDF
- Markdown
- TXT

例如：

```text
workspace/papers/paper-a.pdf
workspace/papers/paper-b.pdf
workspace/papers/notes.md
```

### 6. 调用 skill

对 Agent 说：

```text
请使用 research-workflow skill 处理新论文。
```

---

## 输出写到哪里

### 原始论文

```text
workspace/papers/
```

### PDF 提取结果

```text
workspace/extracted/
```

例如：

```text
workspace/extracted/paper-a/text.md
workspace/extracted/paper-a/tables.md
workspace/extracted/paper-a/equations.md
workspace/extracted/paper-a/figures.md
workspace/extracted/paper-a/manifest.json
```

`manifest.json` 会记录提取策略，比如：

- `pdftotext-layout-or-pypdf-with-heuristics`
- `auto-fallback-to-mineru`
- `mineru-docker-wrapper`

### paper memory

```text
workspace/memory/papers/
```

### 输出文档

```text
workspace/outputs/
```

例如：

```text
workspace/outputs/001-paper-card-xxx.md
workspace/outputs/003-collision-xxx-yyy.md
workspace/outputs/004-direction-xxx.md
```

### 状态文件

```text
workspace/state.json
```

---

## 第二次怎么继续用

以后只要重复两步：

1. 往 `workspace/papers/` 里加新论文
2. 再调用一次 `research-workflow` skill

工作流会自动判断：

- 哪些论文是新的
- 哪些论文变了
- 哪些还没生成 memory / card
- 哪些 collision 已做过
- 哪些 direction 还没生成

---

## Web 怎么看

在工作目录里运行：

```bash
uv run python server.py
```

打开：

```text
http://127.0.0.1:8765
```

Web 会读取当前工作目录里的：

- `workspace/outputs/`
- `workspace/state.json`

现在已经支持：

- `all` 视图
- 按 `paper_card / collision / direction` 分组浏览
- 查看真实运行产物

---

## 常见问题

### 可以直接在 `~/.agents/skills/research-workflow/` 里运行吗？

不推荐。

这个目录是 skill 安装目录，不是正式工作目录。

### 输出会写回 skill 安装目录吗？

不会。

输出会写到你自己的工作目录，比如：

```text
~/my-research/
```

### 输出是什么语言？

默认中文输出。  
关键英文术语会保留原文，并附术语对照。

---

## 本地开发

如果你是在这个仓库里直接开发，而不是通过 `skills add` 安装，可以在仓库根目录运行：

```bash
uv sync
uv run python workflow.py prepare
uv run python server.py
uv run python -m unittest discover -s tests -v
```

---

## Skill 仓库结构

真正供安装的 skill 在：

```text
skills/research-workflow/
```

也就是说，安装的是 `research-workflow` 这个 skill，不是仓库根目录本身。
