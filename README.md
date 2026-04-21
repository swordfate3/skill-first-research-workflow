# Skill-First Research Workflow

一个给大模型 / Agent 用的论文研究工作流 skill。

它的目标很简单：

```text
装 skill -> 建工作目录 -> 放论文 -> 调用 skill -> 看 memory / 碰撞 / 方向输出
```

---

## 先理解两个目录

这个项目有两个容易混淆的目录。

### 1. skill 安装目录

通过下面命令安装：

```bash
npx skills add <owner>/<repo>@research-workflow
```

安装后，skill 会出现在本地类似这样的位置：

```text
~/.agents/skills/research-workflow/
```

这个目录里放的是：

- `SKILL.md`
- `scripts/bootstrap_project.py`
- `assets/project-template/`
- `agents/openai.yaml`

它的作用是：

**提供能力和模板**

它不是你真正处理论文的目录。

### 2. 工作目录

这是你自己创建的目录，比如：

```bash
mkdir ~/my-research
cd ~/my-research
```

这个目录的作用是：

**真正存放论文、提取结果、输出文档、状态文件**

后续所有研究过程都发生在这里。

---

## 整个使用流程

## 第一步：安装 skill

把 `<owner>/<repo>` 换成你的 GitHub 仓库：

```bash
npx skills add <owner>/<repo>@research-workflow
```

安装完成后，相当于你把“研究工作流能力包”装进本地了。

---

## 第二步：创建工作目录

比如：

```bash
mkdir ~/my-research
cd ~/my-research
```

这个目录就是你之后真正工作的地方。

---

## 第三步：把工作流模板释放到当前目录

有两种方式。

### 方式 A：让 Agent 自动做

你直接对 Agent 说：

```text
请使用 research-workflow skill 处理我这里的新论文。
```

如果当前目录还没有这些文件：

- `workflow.py`
- `state.py`
- `workspace/papers/`

skill 会先自动初始化项目骨架。

### 方式 B：你手动先初始化

如果你想先自己准备好目录，可以手动运行：

```bash
python ~/.agents/skills/research-workflow/scripts/bootstrap_project.py --dest .
```

执行完成后，当前目录会出现：

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

这时候，当前目录就已经是一个可运行的研究项目目录了。

---

## 第四步：准备 Python 环境

在工作目录里执行：

```bash
uv sync
```

这一步会为当前工作目录准备依赖和虚拟环境。

---

## 第五步：放论文

把论文放到：

```text
workspace/papers/
```

支持的输入包括：

- PDF
- Markdown
- TXT

例如：

```text
workspace/papers/paper-a.pdf
workspace/papers/paper-b.pdf
workspace/papers/notes.md
```

---

## 第六步：调用 skill 处理论文

对 Agent 说：

```text
请使用 research-workflow skill 处理新论文。
```

skill 会自动做这些事：

1. 扫描 `workspace/papers/`
2. 识别哪些论文是新的、哪些改过、哪些没变
3. 对 PDF 做正文 / 表格 / 公式 / 图表线索提取
4. 为每篇论文生成结构化 paper memory
5. 生成 paper card
6. 只保留 Top-K 高价值创新碰撞
7. 基于高分碰撞继续生成研究方向
8. 更新状态文件，避免重复处理

---

## 第七步：结果会写到哪里

这是最关键的部分。

### 原始论文

放在：

```text
workspace/papers/
```

### PDF 提取结果

写到：

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

### 结构化 paper memory

写到：

```text
workspace/memory/papers/
```

例如：

```text
workspace/memory/papers/paper-a.json
workspace/memory/papers/paper-b.json
```

### 最终输出文档

写到：

```text
workspace/outputs/
```

例如：

```text
workspace/outputs/001-paper-card-xxx.md
workspace/outputs/002-paper-card-yyy.md
workspace/outputs/003-collision-xxx-yyy.md
workspace/outputs/004-direction-xxx.md
```

### 状态文件

写到：

```text
workspace/state.json
```

这个文件用来记录：

- 哪些论文处理过
- 哪些论文内容发生过变化
- 哪些论文已经生成 memory / card
- 哪些组合已经做过碰撞
- 哪些碰撞已经升格成方向

---

## 重点结论

**释放完工作目录之后，skill 后续产生的文件，都会写到这个工作目录。**

不会写到：

```text
~/.agents/skills/research-workflow/
```

而是会写到你自己的项目目录，比如：

```text
~/my-research/
```

所以：

- skill 安装目录 = 模板和能力包
- 工作目录 = 真实研究现场

---

## 第二次怎么继续用

以后你只要重复这两步：

1. 往 `workspace/papers/` 里加新论文
2. 再调用一次 `research-workflow` skill

它会自动判断：

- 哪些是新论文
- 哪些论文还没有 memory
- 哪些论文已经处理过
- 哪些论文变了
- 哪些碰撞组合已经存在
- 哪些高分碰撞还没生成方向

所以你不需要手动管理重复。

---

## Web 怎么用

在工作目录里运行：

```bash
uv run python server.py
```

打开：

```text
http://127.0.0.1:8765
```

网页读取的是当前工作目录里的这些内容：

- `workspace/outputs/`
- `workspace/state.json`

所以网页展示的是这一次工作目录里的研究结果，不是 skill 安装目录里的内容。状态面板也会显示：

- 论文数
- 已建 memory 数
- 已碰撞组合数
- 已生成方向数
- 待生成方向数

---

## 最推荐的完整操作顺序

你可以直接照着下面做：

```bash
npx skills add <owner>/<repo>@research-workflow

mkdir ~/my-research
cd ~/my-research

python ~/.agents/skills/research-workflow/scripts/bootstrap_project.py --dest .
uv sync
```

然后把论文放进：

```text
workspace/papers/
```

再对 Agent 说：

```text
请使用 research-workflow skill 处理新论文。
```

查看结果：

- 结构化 memory：`workspace/memory/papers/`
- Markdown 文档：`workspace/outputs/`
- 本地网页：`uv run python server.py`

---

## 常见问题

### 可以直接进入 `~/.agents/skills/research-workflow/` 运行吗？

不推荐。

这个目录是 skill 安装目录，不是正式工作目录。  
虽然模板文件在里面，但你的论文、输出、状态都不应该直接堆在 skill 安装目录里。

正确做法是：

1. 安装 skill
2. 在你自己的目录里 bootstrap
3. 在你自己的目录里运行 workflow 和 web

### 第一次没有 `workspace/papers/` 怎么办？

没关系。  
第一次 bootstrap 后会自动创建。

### 输出是什么语言？

默认是中文。  
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

其中：

```text
SKILL.md
scripts/bootstrap_project.py
assets/project-template/
agents/openai.yaml
```

也就是说，安装的是 `research-workflow` 这个 skill，而不是仓库根目录本身。
