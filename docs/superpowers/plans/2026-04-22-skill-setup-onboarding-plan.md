# Skill 首次使用自举链路 Implementation Plan

> **Execution note:** `writing-plans` skill is unavailable in this session, so this plan is written manually in the same format and will be executed directly.

**Goal:** 为已安装的 `research-workflow` skill 增加统一 setup 入口，要求首次使用时必须由用户明确提供释放目录；setup 自动完成项目模板释放、`uv` 检测、`uv sync`、Web 服务复用或启动，并把状态以 JSON 返回给 `SKILL.md` 消费。

**Architecture:** 保持现有 skill-template 架构。新增 `skills/research-workflow/scripts/setup_project.py` 作为高层入口，继续复用 `bootstrap_project.py` 负责模板复制；增强 `server.py` 以支持 `--host/--port` 与 `project_root` 暴露，便于 setup 脚本判断是否可复用已有 Web 服务。

**Tech Stack:** Python 3.10 + `uv`, `unittest`, 原生 `http.server`, `subprocess`, `urllib`, `socket`

---

## File Structure

- Create: `skills/research-workflow/scripts/setup_project.py`
  - 统一 setup 入口，负责目录检查、bootstrap、`uv` 检测、依赖同步、Web 复用/启动。
- Modify: `skills/research-workflow/SKILL.md`
  - 改成先运行 setup，再根据状态继续 workflow 或向用户要目标目录。
- Modify: `server.py`
  - 支持 `--host/--port`，在 `/api/state` 暴露 `project_root` 便于 setup 复用正确实例。
- Modify: `skills/research-workflow/assets/project-template/server.py`
  - 同步服务器增强能力到模板。
- Modify: `README.md`
  - 更新首次使用说明与目标目录要求。
- Modify: `tests/test_server.py`
  - 覆盖 `project_root` 字段与 `--port` 相关行为。
- Modify: `tests/test_skill_packaging.py`
  - 覆盖 `setup_project.py` 文件存在、基础返回值和 bootstrap + uv 检测分支。
- Create: `tests/test_setup_project.py`
  - 覆盖 `needs_destination`、`needs_uv`、bootstrap、Web 复用/启动路径。

---

## Task 1: 先补失败测试，钉住 setup 状态机

**Files:**
- Modify: `tests/test_skill_packaging.py`
- Create: `tests/test_setup_project.py`
- Modify: `tests/test_server.py`

- [ ] **Step 1: 在 `tests/test_skill_packaging.py` 断言 skill bundle 包含 `scripts/setup_project.py`**

- [ ] **Step 2: 新建 `tests/test_setup_project.py`，覆盖这些失败前用例**
  - 当前目录不是工作目录且未传 `--dest` 时返回 `needs_destination`
  - 传入 `--dest` 时会调用 bootstrap 并返回 bootstrapped 状态
  - `uv` 不存在时返回 `needs_uv`
  - 已有同项目 Web 服务时返回 `web.status = reused`

- [ ] **Step 3: 在 `tests/test_server.py` 增加 `/api/state` 包含 `project_root` 的断言**

- [ ] **Step 4: 运行定向测试，确认新增用例先失败**

```bash
uv run python -m unittest tests/test_skill_packaging.py tests/test_setup_project.py tests/test_server.py -v
```

---

## Task 2: 增强 `server.py` 以支持 setup 复用与启动

**Files:**
- Modify: `server.py`

- [ ] **Step 1: `/api/state` 增加 `project_root` 字段**

- [ ] **Step 2: 给 `server.py` 增加 `--host` 与 `--port` 参数**
  - 默认仍是 `127.0.0.1:8765`
  - 便于 setup 在冲突端口上启动新实例

- [ ] **Step 3: 保持现有 Web、上传和文档接口不回归**

---

## Task 3: 实现 `setup_project.py`

**Files:**
- Create: `skills/research-workflow/scripts/setup_project.py`

- [ ] **Step 1: 实现工作目录检测**
  - 判断 `workflow.py`、`state.py`、`workspace/papers/`

- [ ] **Step 2: 实现目标目录逻辑**
  - 当前目录非工作目录且未给 `--dest` -> `needs_destination`
  - 给了 `--dest` -> 调用 `bootstrap_project.bootstrap_project()`
  - 冲突 -> `bootstrap_conflict`

- [ ] **Step 3: 实现 `uv` 检测与 `uv sync`**
  - `shutil.which("uv")`
  - `subprocess.run(["uv", "sync"], cwd=project_root, ...)`
  - 缺失 -> `needs_uv`

- [ ] **Step 4: 实现 Web 复用/启动**
  - 先探测 `8765`
  - 若是同项目 research workflow 服务则复用
  - 否则找下一个可用端口
  - 使用 `subprocess.Popen(..., start_new_session=True)` 启动

- [ ] **Step 5: 统一 JSON 返回**
  - `ready`
  - `needs_destination`
  - `needs_uv`
  - `bootstrap_conflict`
  - `web_failed`
  - `failed`

---

## Task 4: 更新 `SKILL.md`、README 和模板同步

**Files:**
- Modify: `skills/research-workflow/SKILL.md`
- Modify: `README.md`
- Modify: `skills/research-workflow/assets/project-template/server.py`

- [ ] **Step 1: `SKILL.md` 改成 setup-first**
  - 未给目标目录时先向用户询问
  - `ready` 后再继续 `workflow.py prepare`

- [ ] **Step 2: README 更新首次使用说明**
  - 说明首次调用时需要明确目标目录
  - 说明 setup 会自动检查 `uv`、自动复用/启动 Web

- [ ] **Step 3: 同步模板 `server.py`**

---

## Task 5: 回归、验证、提交

**Files:**
- Modify: `tests/test_setup_project.py`
- Modify: `tests/test_server.py`
- Modify: `README.md`
- Modify: `skills/research-workflow/SKILL.md`

- [ ] **Step 1: 跑定向测试**

```bash
uv run python -m unittest tests/test_skill_packaging.py tests/test_setup_project.py tests/test_server.py -v
```

- [ ] **Step 2: 跑全量测试**

```bash
uv run python -m unittest discover -s tests -v
```

- [ ] **Step 3: 做一次本地手动验证**
  - 在空目录运行 `setup_project.py` 不带 `--dest`，确认返回 `needs_destination`
  - 传 `--dest` 到新目录，确认能 bootstrap
  - 复用或启动 Web 后返回实际 URL

- [ ] **Step 4: 提交并推远程**

建议提交信息：

```bash
git commit -m "feat(skill): 优化首次使用自举引导"
```
