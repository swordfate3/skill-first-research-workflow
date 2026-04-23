# Skill 首次使用自举与引导设计

Last updated: 2026-04-22

## 背景

当前 `research-workflow` skill 已经具备完整能力：

- 可通过 `npx skills add swordfate3/skill-first-research-workflow --skill research-workflow` 安装
- 可释放项目模板
- 可运行 `workflow.py prepare`
- 可启动本地 Web 面板
- 可从 Web 上传 PDF 并自动进入处理链路

但第一次使用时，仍有几类容易卡住的点：

1. 用户不知道项目应该释放到哪里
2. skill 目前默认围绕“当前目录”判断，容易和用户的真实目标目录错位
3. `uv` 是否已安装、是否需要手动执行 `uv sync` 仍然不够收口
4. Web 面板虽然能运行，但首次使用后不会自然落到“可访问地址已准备好”的状态

项目已经从“内部开发可用”走到“可分发的 skill”，下一步最值得做的是把首次使用引导收成一条统一、明确、可恢复的自举链路。

## 目标

为已安装的 skill 增加一个统一 setup 入口，让首次使用流程变成：

1. 用户调用 skill
2. skill 判断当前目录是否已是工作目录
3. 如果不是工作目录，且用户没有明确目标路径，则先询问释放到哪里
4. 用户给出目标路径后，自动 bootstrap 项目模板
5. 自动检查 `uv`
6. `uv` 可用时自动执行 `uv sync`
7. 自动复用已有 Web 服务，或启动新的本地 Web
8. 返回明确的 Web 地址与后续步骤

## 非目标

本次不做：

- 不自动安装 `uv`
- 不默认把模板偷偷释放到当前目录
- 不引入 Docker-first 启动链路
- 不引入数据库或更复杂的 setup 状态存储
- 不改写研究 workflow 本身的 memory/card/collision/direction 逻辑

## 关键原则

### 1. 释放目录必须由用户明确指定

如果当前目录还不是工作目录，且用户没有给出目标路径，setup 必须停止并返回：

- `needs_destination`

然后由 skill 明确询问用户：

> 你要把项目释放到哪个目录？

即使当前目录看起来是空目录，也不能默认释放到当前目录。

### 2. `uv` 只检测，不自动安装

本次只做：

- 检测是否存在 `uv`
- 存在则自动继续
- 不存在则返回明确提示

原因：

- 不同系统下安装方式差异大
- 自动安装可能碰到权限、包管理器、PATH 等问题
- 先把“清晰失败”做好，收益已经很高

### 3. Web 服务优先复用

若已有 research workflow 的 Web 服务在运行：

- 直接复用
- 不重复启动
- 不强制重启

如果没有服务，再自动启动新的本地 Web。

## 方案比较

### 方案 A：只改 README 和 `SKILL.md`

优点：

- 改动小
- 风险低

缺点：

- 仍然主要依赖 Agent 自己理解说明并手动拼接流程
- 首次体验改善有限

### 方案 B：统一 setup 脚本（推荐）

新增统一入口脚本，收口：

- 工作目录检查
- 明确目标路径
- bootstrap
- `uv` 检测
- `uv sync`
- Web 复用/启动

优点：

- 第一次使用体验显著提升
- 技术复杂度可控
- 与现有 skill-template 架构兼容

缺点：

- 需要重写部分 `SKILL.md` 启动逻辑
- 需要新增若干状态码和测试

### 方案 C：直接上 Docker-first 引导

优点：

- 环境问题最少
- 更接近“调用 skill 就能用”

缺点：

- 超出当前项目这轮目标
- 会把“首次使用优化”扩张成新的运行时路线

**结论：采用方案 B。**

## 新增脚本

建议新增：

```text
skills/research-workflow/scripts/setup_project.py
```

该脚本作为统一 setup 入口，供：

- `SKILL.md` 首次调用
- 用户手动运行
- 后续 README 快速入口

## setup 脚本职责

### 1. 判断当前目录是否已是工作目录

判断标准至少包括：

- 存在 `workflow.py`
- 存在 `state.py`
- 存在 `workspace/papers/`

若满足，直接进入后续环境与 Web 检查。

### 2. 处理项目释放

若当前目录不是工作目录：

- 如果传入 `--dest <path>`，则释放到该路径
- 如果没传入 `--dest`，返回 `needs_destination`

这一步不允许静默默认当前目录。

### 3. 检查 `uv`

建议通过：

- `shutil.which("uv")`

或等效方式检测。

结果：

- 找到：继续
- 找不到：返回 `needs_uv`

### 4. 自动同步依赖

当项目目录已存在且 `uv` 可用时：

- 自动执行 `uv sync`

同步成功后进入 Web 检查。

若失败：

- 返回 `failed`
- 附带 `uv sync` 错误信息

### 5. 复用或启动 Web

优先尝试默认地址：

```text
http://127.0.0.1:8765
```

处理逻辑：

1. 若该端口已有 research workflow Web 服务，则直接复用
2. 若端口被其他进程占用，则尝试递增端口，如：
   - `8766`
   - `8767`
3. 若没有服务，则启动：

```bash
uv run python server.py
```

并返回实际 URL。

## Web 复用判定

不能只判断“端口有服务”，还要判断是不是本项目服务。

建议通过请求：

```text
GET /api/state
```

或根路径特征来判断是否为 research workflow Web。

若响应结构符合预期，则认为可复用。

## 返回结果设计

setup 脚本统一返回 JSON，便于 `SKILL.md` 和测试消费。

### 成功示例

```json
{
  "status": "ready",
  "project_root": "/home/fate/my-research",
  "project_bootstrapped": true,
  "uv_available": true,
  "dependencies_synced": true,
  "web": {
    "status": "reused",
    "url": "http://127.0.0.1:8765"
  },
  "next_step": "run_workflow"
}
```

### 需要目标目录

```json
{
  "status": "needs_destination",
  "message": "Project directory is not initialized. Please provide a destination path for bootstrap."
}
```

### 缺少 `uv`

```json
{
  "status": "needs_uv",
  "project_root": "/home/fate/my-research",
  "project_bootstrapped": true,
  "uv_available": false,
  "message": "uv is required before this project can run."
}
```

### Bootstrap 冲突

```json
{
  "status": "bootstrap_conflict",
  "project_root": "/home/fate/my-research",
  "message": "Destination already contains conflicting files.",
  "conflicts": ["workflow.py", "server.py"]
}
```

### Web 启动失败

```json
{
  "status": "web_failed",
  "project_root": "/home/fate/my-research",
  "message": "Web server could not be started.",
  "port_attempts": [8765, 8766]
}
```

## 状态枚举

本次至少引入这些 setup 状态：

- `ready`
- `needs_destination`
- `needs_uv`
- `bootstrap_conflict`
- `web_failed`
- `failed`

## `SKILL.md` 改造

当前 `SKILL.md` 中 bootstrap、`uv sync`、Web 启动逻辑较分散。

改造后：

1. 先运行统一 setup 脚本
2. 根据返回状态决定下一步

建议行为：

- `needs_destination`
  - 问用户：项目要释放到哪个目录
- `needs_uv`
  - 明确告诉用户要先安装 `uv`
- `ready`
  - 告知 Web 地址
  - 然后继续：

```bash
uv run python workflow.py prepare
```

这样 skill 首次使用时，不再需要自己在提示词里拼装 bootstrap / `uv sync` / Web 启动细节。

## README 改造

README 调整成双入口：

### 快速入口

面向只想尽快跑起来的人：

1. `npx skills add ...`
2. 进入任意目录
3. 调用 skill
4. 如果还没释放项目，skill 会询问目标目录
5. setup 成功后自动返回 Web 地址

### 手动入口

保留现有方式：

- 手动 bootstrap
- 手动 `uv sync`
- 手动 `uv run python server.py`

## 对现有脚本的关系

### `bootstrap_project.py`

保留为更底层的模板释放脚本。

### `setup_project.py`

作为更高层的统一入口，内部可调用 `bootstrap_project.py` 的逻辑，而不是替代它。

即：

- `bootstrap_project.py` 负责“复制模板”
- `setup_project.py` 负责“准备可运行项目”

## 测试范围

### setup 脚本测试

- 当前目录已是工作目录时直接返回 `ready`
- 当前目录不是工作目录且未传路径时返回 `needs_destination`
- 传入目标路径时能成功 bootstrap
- `uv` 缺失时返回 `needs_uv`
- `uv sync` 成功时进入 Web 复用/启动逻辑

### Web 复用测试

- 已有 research workflow 服务时返回 `reused`
- 端口被其他服务占用时能换端口
- Web 启动失败时返回 `web_failed`

### 模板同步测试

需同步更新：

- `skills/research-workflow/SKILL.md`
- `skills/research-workflow/scripts/setup_project.py`
- `README.md`
- skill 模板项目中的必要说明

## 验收标准

以下场景都应成立：

1. 用户在空目录调用 skill，未给路径时，skill 会先询问释放到哪里
2. 用户给出路径后，项目模板能成功释放
3. 若本机有 `uv`，则自动执行 `uv sync`
4. setup 完成后，能自动复用或启动 Web
5. 用户能得到明确 URL
6. setup 成功后，skill 能继续进入 `workflow.py prepare`
7. 若缺 `uv`，用户能得到明确、可执行的安装提示

## 后续扩展

这轮不做，但后续自然可接：

- Docker-first setup
- 自动安装 `uv`
- Web 日志面板
- 一键重新打开最近工作目录
- setup 历史记录
