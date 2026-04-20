# Skill-First Research Workflow

一个更轻的研究工作流版本。

核心思路：

```text
大模型负责分析和写文档
Skill 负责规定流程
Web 负责展示输出
```

它不自己调用模型，也不内置复杂状态机。你让 Claude Code、Codex 或其他 Agent 读取这里的 skill，然后它按流程把结果写成 Markdown。网页只负责把这些 Markdown 展示出来。

## 目录结构

```text
skill-first-research-workflow/
  skills/research-workflow/SKILL.md   # 给大模型/Agent 用的工作流说明
  workspace/
    papers/                           # 放论文、摘要、笔记
    extracted/                        # PDF 提取出的正文、表格、公式、图表线索
    outputs/                          # Agent 生成的文档
    approvals/                        # 可选审批记录
  templates/                          # 输出文档模板
  web/                                # 本地文档展示页面
  extract_pdfs.py                     # 轻量 PDF 结构提取
  state.py                            # 扫描新论文、记录已碰撞组合
  server.py                           # 本地 Web 服务
```

## 最快使用

### 1. 放论文

把 PDF、摘要、Markdown 笔记放进：

```text
workspace/papers/
```

### 2. 扫描新论文

```bash
python state.py scan
```

它会更新：

```text
workspace/state.json
```

规则很简单：

- 新文件 hash 没见过：需要生成 paper card。
- 文件 hash 没变：跳过，不重复分析。
- 文件 hash 变了：重新生成 paper card。
- 已经记录过的论文组合：不重复做 collision。

### 3. 提取 PDF 内容

如果有 PDF，先运行：

```bash
python extract_pdfs.py
```

它会生成：

```text
workspace/extracted/论文名/
  text.md          # 正文
  tables.md        # 表格和数字结果线索
  equations.md     # 公式线索
  figures.md       # 图表 caption 线索
  manifest.json    # 提取状态和不确定性说明
```

它也会看 PDF hash：

- PDF 没变：跳过，不重复提取。
- PDF 变了：重新提取。
- 提取失败：在结果里标记 failed，需要 OCR 或手动提供文本。

注意：这是轻量提取，不是假装完美理解 PDF。表格、公式、图像内容都可能需要人工复核。

### 4. 让大模型执行 skill

给 Claude Code 或 Codex 说：

```text
请使用 skill-first-research-workflow/skills/research-workflow/SKILL.md，
先运行 python state.py scan 和 python extract_pdfs.py，
阅读 workspace/papers 与 workspace/extracted 下的材料，
生成 paper card、创新碰撞和 draft，
把结果写到 workspace/outputs。
```

Agent 会生成类似这些文件：

```text
workspace/outputs/001-paper-card.md
workspace/outputs/002-collision-ideas.md
workspace/outputs/003-prototype.md
workspace/outputs/004-draft.md
```

Agent 写完 paper card 后，记录一下：

```bash
python state.py mark-card paper-a.pdf 001-paper-card-paper-a.md
```

Agent 写完两篇论文的碰撞后，记录一下：

```bash
python state.py mark-collision paper-a.pdf paper-b.pdf 002-collision-paper-a-paper-b.md
```

### 5. 打开网页看结果

在这个目录下启动：

```bash
python server.py
```

然后打开：

```text
http://127.0.0.1:8765
```

## 输出文档格式

每个输出 Markdown 建议带一个简单头部：

```markdown
---
title: Example Idea
type: collision
status: pending
---

# Example Idea

正文内容...
```

`status` 可以是：

```text
pending
approved
rejected
done
```

## PDF 分析规则

PDF 论文不能只看正文。生成 paper card 时，Agent 应该检查：

```text
text.md        背景、方法、结论
tables.md      实验结果、baseline、指标、消融
equations.md   方法公式、损失函数、约束、复杂度
figures.md     模型结构图、流程图、caption
manifest.json  哪些内容可能提取不准
```

paper card 里建议写清楚：

```text
表格证据是什么
关键公式表达了什么假设
图表说明了什么结构
哪些地方需要人工复核
```

## 去重和碰撞规则

轻量版用 `workspace/state.json` 记住已经处理过什么。

它记录：

```json
{
  "papers": {
    "paper-a.pdf": {
      "hash": "...",
      "status": "card_created",
      "paper_card": "001-paper-card-paper-a.md"
    }
  },
  "collisions": {
    "paper-a.pdf::paper-b.pdf": {
      "papers": ["paper-a.pdf", "paper-b.pdf"],
      "output": "002-collision-paper-a-paper-b.md",
      "status": "created"
    }
  }
}
```

如果已经有 A、B、C 三篇文章，并且 A+B、A+C、B+C 都碰撞过，后来新增 D，那么下一次只需要做：

```text
D+A
D+B
D+C
```

旧组合不会重复生成。

## 什么时候用这个轻量版

适合：

- 你想让大模型真正负责研究分析。
- 你想把结果沉淀成 Markdown 文档。
- 你只需要一个网页查看输出，不想维护复杂 workflow runtime。

不适合：

- 需要后台 daemon。
- 需要数据库。
- 需要自动调用模型 API。
- 需要多人权限和生产级部署。
