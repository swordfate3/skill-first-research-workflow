# Skill-First Research Workflow

一个可以通过 `npx skills add` 安装的论文研究 workflow skill。

现在这个仓库同时承担两件事：

1. 作为本地开发中的示例项目
2. 作为可安装的 `research-workflow` skill 源仓库

最推荐的分发方式是：

```bash
npx skills add <owner>/<repo>@research-workflow
```

装完以后，Agent 就能在任意工作目录里调用这个 skill。skill 会先把完整项目骨架释放到当前目录，再自动处理论文。

## 使用体验

你只需要：

```text
放论文 -> 调用 skill -> 看输出文档
```

## 安装后怎么用

### 1. 安装 skill

```bash
npx skills add <owner>/<repo>@research-workflow
```

### 2. 进入一个空目录或你的研究目录

```bash
mkdir my-research-workflow
cd my-research-workflow
```

### 3. 调用 skill

对 Agent 说：

```text
请使用 research-workflow skill 处理我这里的新论文。
```

skill 会自动：

```text
把项目模板初始化到当前目录
安装 Python 依赖
扫描新论文
提取 PDF 正文/表格/公式/图表线索
跳过已经处理过的论文
生成中文 paper card
生成新的创新碰撞
记录已处理状态
```

输出默认是中文研究笔记；关键英文术语会保留原文，并在文档里给出术语对照。

## 当前目录会生成什么

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

论文放这里：

```text
workspace/papers/
```

输出在这里：

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

## Skill 仓库结构

```text
skills/research-workflow/
  SKILL.md
  agents/openai.yaml
  scripts/bootstrap_project.py
  assets/project-template/
```

`bootstrap_project.py` 会把 `assets/project-template/` 复制到当前目录，所以这个 skill 被单独安装后也能工作，不再依赖仓库根目录。

## 本地开发调试

如果你是在这个仓库里直接开发，而不是通过 `skills add` 安装，那么继续用仓库根目录下现有文件即可：

```bash
uv sync
uv run python workflow.py prepare
uv run python server.py
uv run python -m unittest discover -s tests -v
```
