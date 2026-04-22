# Web 论文上传与自动处理设计

Last updated: 2026-04-22

## 背景

当前项目主流程已经打通：

- 论文放入 `workspace/papers/`
- `extract_pdfs.py` 提取 PDF
- `workflow.py prepare` 生成待办
- 研究输出写入 `workspace/memory/` 与 `workspace/outputs/`
- Web 面板展示状态与文档

但“新增论文”这一步仍然依赖用户手动把 PDF 拷进 `workspace/papers/`。这会带来两个问题：

1. Web 面板还不是完整工作台，新增输入仍要跳出页面操作
2. “放论文 -> 自动处理 -> 看结果”这条链没有在前端闭环

本次要把这一步接到 Web 里，让用户能直接从前端上传 PDF，并自动触发后续处理。

## 目标

新增一条前端闭环流程：

1. 在 Web 页面选择多个 PDF
2. 后端保存到 `workspace/papers/`
3. 同名文件直接覆盖
4. 上传完成后自动触发研究工作流
5. 前端看到每个文件的上传/处理状态
6. 处理完成后自动刷新研究面板

## 非目标

本次不做：

- 不支持非 PDF 文件
- 不做拖拽上传
- 不做上传百分比进度条
- 不做数据库或外部消息队列
- 不做独立 worker 进程
- 不把上传会话状态持久化到磁盘

## 方案比较

### 方案 A：只上传不处理

前端只负责上传，处理仍然手动触发。

优点：

- 改动最小

缺点：

- 没有形成真正闭环
- 仍然要用户理解内部工作流

### 方案 B：上传后由当前 Web 服务串行处理（推荐）

前端上传多个 PDF，后端保存后加入一个内存中的批处理队列，按顺序自动触发提取与工作流刷新。

优点：

- 体验完整
- 不需要额外进程
- 能直接复用现有 `extract_pdfs.py` 与 `workflow.py`
- 适合当前单机轻量架构

缺点：

- 上传状态只在当前服务进程生命周期内保留

### 方案 C：上传后交给独立后台 worker

优点：

- 架构更清晰

缺点：

- 对当前项目过重
- 部署与调试复杂度明显上升

**结论：采用方案 B。**

## 用户体验

在现有研究面板左侧新增一个轻量上传区：

- 按钮：`上传 PDF`
- 输入：支持多文件选择，限制 `.pdf`
- 状态区：展示最近一批上传任务的文件状态

状态枚举：

- `queued`
- `processing`
- `completed`
- `failed`

典型交互为：

1. 用户选择多个 PDF
2. 页面提交到 `POST /api/upload-papers`
3. 文件保存成功后自动进入处理队列
4. 页面轮询任务状态
5. 任务全部完成后自动刷新：
   - `/api/state`
   - `/api/documents`
   - 当前文档阅读区

## 接口设计

### `POST /api/upload-papers`

用途：

- 接收多 PDF 上传
- 保存到 `workspace/papers/`
- 同名覆盖
- 创建一个上传批次并排队处理

请求：

- `multipart/form-data`
- 字段名统一为 `files`

行为：

1. 若没有文件，返回 `400`
2. 若任一文件不是 `.pdf`，返回 `400`
3. 所有合法文件写入 `workspace/papers/`
4. 覆盖同名旧文件
5. 创建 `batch_id`
6. 返回当前批次基础状态

返回示例：

```json
{
  "batch_id": "20260422-153000-01",
  "files": [
    {"name": "paper-a.pdf", "status": "queued"},
    {"name": "paper-b.pdf", "status": "queued"}
  ]
}
```

### `GET /api/upload-status`

用途：

- 返回当前上传/处理批次状态

返回字段：

- `active_batch_id`
- `is_processing`
- `queue_size`
- `files`
- `last_error`

返回示例：

```json
{
  "active_batch_id": "20260422-153000-01",
  "is_processing": true,
  "queue_size": 1,
  "files": [
    {"name": "paper-a.pdf", "status": "completed"},
    {"name": "paper-b.pdf", "status": "processing"}
  ],
  "last_error": ""
}
```

### 内部处理入口

本次不额外暴露用户可见按钮，但在服务端保留一个内部可复用的“开始处理当前批次”入口，供：

- 上传成功后自动调用
- 后续增加“重试/重新处理”按钮复用

## 后端设计

### 服务内批处理队列

在 `server.py` 内新增一个轻量队列管理器，负责：

- 接收新上传批次
- 维护批次顺序
- 确保同一时刻只跑一个处理任务
- 保存短期内存状态供 `/api/upload-status` 返回

建议结构：

- `UploadBatch`
- `UploadStatusStore`
- `ProcessingWorker`

可以是简单的模块级对象，不需要引入复杂抽象。

### 处理时序

每个上传批次执行时：

1. 将所有文件状态设为 `queued`
2. 后台线程取出批次
3. 批次状态切为 `processing`
4. 调用现有处理链：
   - `extract_pdfs.extract_all(root)`
   - `workflow.prepare_workspace(root)`
5. 如果处理成功，所有文件标为 `completed`
6. 如果处理失败，整批标为 `failed`
7. 继续处理队列中的下一批

### 为什么按批次触发一次 workflow

因为同一次多文件上传本质上是一组新增输入。若每个文件单独跑一次：

- 会重复扫描工作区
- 会增加状态竞争风险
- 会让 `state.json` 更频繁被重写

所以推荐：

- 文件逐个保存
- workflow 按批次统一跑一次

## 文件系统行为

上传保存目标固定为：

`workspace/papers/`

规则：

- 文件名原样保留
- 同名直接覆盖
- 不做自动重命名

覆盖后，后续 `scan_workspace()` 会把该文件识别为 changed/new，并进入后续流程。

## 错误处理

### 上传阶段

- 空请求：`400`
- 非 PDF：`400`
- 文件保存失败：该请求返回 `500`

### 处理阶段

- PDF 提取异常：批次 `failed`
- workflow 异常：批次 `failed`
- 失败不阻塞后续新批次

前端只展示简短错误文本，例如：

- `仅支持 PDF`
- `保存失败`
- `提取失败`
- `workflow 执行失败`

## 前端设计

### 新增区域

在现有左侧栏中加入：

1. 上传按钮
2. 隐藏的 `<input type="file" multiple accept=".pdf,application/pdf">`
3. 最近批次状态列表

### 前端状态流

1. 选择文件
2. 调用 `POST /api/upload-papers`
3. 开始轮询 `GET /api/upload-status`
4. 有任务时持续刷新状态区
5. 当任务全部完成或失败：
   - 停止当前轮询周期
   - 调用现有 `refresh()`

### 文案原则

保持轻量，不写解释型长文案，只展示：

- 上传中
- 排队中
- 处理中
- 已完成
- 失败

## 并发与一致性

本次只保证单服务进程内的一致性。

约束为：

- 一个 HTTP 服务实例只跑一个处理任务
- 同一实例内新批次进入等待队列
- 不处理多实例同时写同一工作目录的场景

这和当前项目的单机使用方式一致。

## 测试范围

### 后端接口测试

- 多 PDF 上传成功
- 非 PDF 被拒绝
- 空上传被拒绝
- 同名覆盖成功

### 队列测试

- 上传后状态为 `queued`
- 处理时状态切到 `processing`
- 成功后为 `completed`
- 异常时为 `failed`

### 集成测试

- 上传文件后实际写入 `workspace/papers/`
- 自动触发提取与 `prepare_workspace`
- `/api/state` 与 `/api/documents` 可看到新结果

### 模板同步测试

需同步更新：

- `skills/research-workflow/assets/project-template/server.py`
- `skills/research-workflow/assets/project-template/web/*`

并补测试保证模板项目具备上传入口与状态区。

## 实施边界

本次只做“Web 上传 -> 自动处理 -> 面板刷新”闭环。

后续可增量扩展：

- 拖拽上传
- 批次历史
- 单文件重试
- 处理日志面板
- 处理百分比进度

## 验收标准

满足以下条件即视为完成：

1. 用户可在 Web 页面一次选择多个 PDF
2. 文件会保存到 `workspace/papers/`
3. 同名文件会被覆盖
4. 上传后无需手动命令即可自动开始处理
5. 页面可看到每个文件的状态变化
6. 完成后研究面板自动刷新，能看到新增状态与输出文档
