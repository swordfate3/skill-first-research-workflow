# Web 论文上传与自动处理 Implementation Plan

> **Execution note:** `writing-plans` skill is unavailable in this session, so this plan is written manually in the same format and will be executed directly.

**Goal:** 让用户可以在 Web 面板直接批量上传 PDF，文件保存到 `workspace/papers/`，同名覆盖，并在上传后自动串行触发提取与 workflow 处理，最后自动刷新研究面板。

**Architecture:** 保持现有单机、文件系统驱动架构。在 `server.py` 内新增轻量上传接口与内存队列，不引入数据库或独立 worker。前端在现有左侧栏增加 PDF 上传与批次状态展示，完成后继续复用现有 `/api/state` 与 `/api/documents` 刷新逻辑。

**Tech Stack:** Python 3.10 + `uv`, `unittest`, 原生 `http.server`, 原生 HTML/CSS/JavaScript

---

## File Structure

本轮涉及文件和职责如下：

- Modify: `server.py`
  - 增加上传接口、上传状态接口、内存批处理队列与后台串行处理逻辑。
- Modify: `web/index.html`
  - 增加上传区域、隐藏文件输入、上传状态列表容器。
- Modify: `web/app.js`
  - 新增上传、轮询状态、完成后刷新面板逻辑。
- Modify: `web/styles.css`
  - 为上传区、状态列表、状态徽标提供稳定布局。
- Modify: `tests/test_server.py`
  - 覆盖上传接口、文件保存、状态接口和失败场景。
- Modify: `tests/test_web_assets.py`
  - 覆盖前端上传入口和状态区 DOM 约束。
- Modify: `README.md`
  - 补充从 Web 上传 PDF 的使用说明。
- Modify: `skills/research-workflow/assets/project-template/server.py`
  - 同步服务端上传能力到 skill 模板。
- Modify: `skills/research-workflow/assets/project-template/web/index.html`
  - 同步模板前端上传入口。
- Modify: `skills/research-workflow/assets/project-template/web/app.js`
  - 同步模板前端上传与轮询逻辑。
- Modify: `skills/research-workflow/assets/project-template/web/styles.css`
  - 同步模板上传区样式。
- Modify: `skills/research-workflow/SKILL.md`
  - 补充 Web 上传能力说明。

---

## Task 1: 先补失败测试，锁定上传接口与前端入口

**Files:**
- Modify: `tests/test_server.py`
- Modify: `tests/test_web_assets.py`

- [ ] **Step 1: 在 `tests/test_server.py` 增加上传接口成功用例**
  - 构造 multipart 请求
  - 上传两个 PDF
  - 断言文件实际写入 `workspace/papers/`
  - 断言返回 `batch_id` 与 `queued` 状态

- [ ] **Step 2: 增加非 PDF 与空上传失败用例**
  - 非 PDF 返回 `400`
  - 空上传返回 `400`

- [ ] **Step 3: 增加同名覆盖用例**
  - 先写入旧文件
  - 再上传同名新文件
  - 断言最终文件内容为新内容

- [ ] **Step 4: 在 `tests/test_web_assets.py` 增加上传区和状态列表断言**
  - `index.html` 包含上传按钮、文件输入、状态列表容器
  - `app.js` 包含 `upload`、`pollUploadStatus`、`/api/upload-papers`、`/api/upload-status`

- [ ] **Step 5: 运行测试并确认新增用例先失败**

Run:

```bash
uv run python -m unittest tests/test_server.py tests/test_web_assets.py -v
```

---

## Task 2: 在 `server.py` 实现上传接口与串行处理队列

**Files:**
- Modify: `server.py`

- [ ] **Step 1: 增加上传状态数据结构**
  - 定义批次对象、文件状态对象、全局队列/锁
  - 状态至少支持 `queued / processing / completed / failed`

- [ ] **Step 2: 增加 `POST /api/upload-papers`**
  - 解析 `multipart/form-data`
  - 仅接受 `.pdf`
  - 保存到 `workspace/papers/`
  - 同名覆盖
  - 创建批次并入队

- [ ] **Step 3: 增加 `GET /api/upload-status`**
  - 返回当前活动批次、队列长度、文件状态与错误信息

- [ ] **Step 4: 增加后台串行处理逻辑**
  - 当队列非空且无任务运行时，启动后台线程
  - 每批次仅统一跑一次：
    - `extract_pdfs.extract_all(ROOT)`
    - `workflow.prepare_workspace(ROOT)`
  - 成功与失败都写回批次状态

- [ ] **Step 5: 保证异常不会卡死队列**
  - 单批失败后继续处理后续批次

---

## Task 3: 升级 Web 上传体验并在完成后自动刷新

**Files:**
- Modify: `web/index.html`
- Modify: `web/app.js`
- Modify: `web/styles.css`

- [ ] **Step 1: 在左侧栏添加上传区**
  - 上传按钮
  - 隐藏文件输入
  - 最近批次状态列表

- [ ] **Step 2: 在 `web/app.js` 增加上传逻辑**
  - 选择文件后提交到 `/api/upload-papers`
  - 启动轮询 `/api/upload-status`
  - 完成后自动调用现有 `refresh()`

- [ ] **Step 3: 增加状态展示**
  - 显示每个文件的处理状态
  - 显示失败原因
  - 任务完成后不影响现有文档浏览

- [ ] **Step 4: 调整样式**
  - 上传区和过滤区并存时仍稳定
  - 手机和窄屏下不挤压文档阅读区

---

## Task 4: 同步 skill 模板与文档说明

**Files:**
- Modify: `skills/research-workflow/assets/project-template/server.py`
- Modify: `skills/research-workflow/assets/project-template/web/index.html`
- Modify: `skills/research-workflow/assets/project-template/web/app.js`
- Modify: `skills/research-workflow/assets/project-template/web/styles.css`
- Modify: `skills/research-workflow/SKILL.md`
- Modify: `README.md`

- [ ] **Step 1: 把主项目的服务端和前端上传能力同步到 skill 模板**

- [ ] **Step 2: 更新 `README.md`**
  - 说明可从 Web 上传 PDF
  - 说明上传后会自动处理

- [ ] **Step 3: 更新 `SKILL.md`**
  - 说明 Web 面板支持上传新论文

---

## Task 5: 回归验证与提交

**Files:**
- Modify: `tests/test_server.py`
- Modify: `tests/test_web_assets.py`
- Modify: `README.md`
- Modify: `skills/research-workflow/...`

- [ ] **Step 1: 跑定向测试**

```bash
uv run python -m unittest tests/test_server.py tests/test_web_assets.py tests/test_skill_packaging.py -v
```

- [ ] **Step 2: 跑全量测试**

```bash
uv run python -m unittest discover -s tests -v
```

- [ ] **Step 3: 本地启动服务做一次人工检查**
  - 上传两个测试 PDF
  - 确认写入 `workspace/papers/`
  - 确认 `/api/upload-status` 状态变化正确
  - 确认前端在处理完成后自动刷新

- [ ] **Step 4: 提交实现**

建议提交信息：

```bash
git commit -m "feat(web): 支持上传论文并自动处理"
```
