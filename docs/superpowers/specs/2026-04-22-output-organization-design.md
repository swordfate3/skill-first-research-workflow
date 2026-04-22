# 输出分类与索引化设计

Last updated: 2026-04-22

## 背景

当前研究工作流已经具备完整主链路：

- `workspace/papers/`
- `workspace/extracted/`
- `workspace/memory/papers/`
- `workspace/outputs/`
- Web 面板展示

但 `workspace/outputs/` 仍然采用**单目录平铺**方式存放所有 Markdown 输出，例如：

- `001-paper-card-*.md`
- `003-collision-*.md`
- `004-direction-*.md`

前端虽然已经能按 `paper_card / collision / direction` 做逻辑分组，但底层存储仍然把所有文件堆在同一个目录。这在论文数量少时还能接受，规模一上来会带来几个问题：

1. 文件系统层面不直观
2. 后端仍需扫描平铺目录并依赖 frontmatter 猜类型
3. 后续如果要加时间、来源、分数、状态，列表构建会越来越脆弱
4. 模板和实际运行目录都缺少清晰的长期演进结构

## 目标

把输出层升级为：

1. **物理分目录**
2. **逻辑索引化**
3. **兼容旧平铺结构**

并保持：

- 现有 Web 能继续读取
- 现有状态文件逻辑尽量少改
- 已生成输出可平滑迁移

## 非目标

本次不做：

- 不重写 state 评分逻辑
- 不新增数据库
- 不新增审批流或复杂标签系统
- 不把 paper memory 挪进 outputs
- 不改输出文档内容模板，只改存储与展示组织方式

## 方案比较

### 方案 A：继续单目录，新增 `index.json`

优点：

- 兼容性最好
- 改动小

缺点：

- 文件系统仍然杂乱
- 肉眼管理输出时体验没有本质改善

### 方案 B：只分目录，不做索引

优点：

- 目录结构直观

缺点：

- 后端仍需扫描文件并解析 frontmatter
- 未来扩展元数据时会很快吃力

### 方案 C：分目录 + 索引（推荐）

结构改成：

```text
workspace/outputs/
  index.json
  paper-cards/
  collisions/
  directions/
```

优点：

- 目录清楚
- 后端和前端都能读稳定元数据
- 未来加排序、搜索、分数、来源映射都更自然

缺点：

- 需要一次性改写读取逻辑和迁移逻辑

**结论：采用方案 C。**

## 目标目录结构

改造后输出目录为：

```text
workspace/outputs/
  index.json
  paper-cards/
    001-paper-card-*.md
  collisions/
    003-collision-*.md
  directions/
    004-direction-*.md
```

## 索引文件设计

新增：

`workspace/outputs/index.json`

记录示例：

```json
{
  "version": 1,
  "documents": [
    {
      "name": "001-paper-card-aes.md",
      "path": "workspace/outputs/paper-cards/001-paper-card-aes.md",
      "type": "paper_card",
      "title": "AES 差分神经密码分析",
      "status": "pending",
      "source_papers": [
        "paper-a.pdf"
      ]
    }
  ]
}
```

### 必要字段

- `name`
- `path`
- `type`
- `title`
- `status`
- `source_papers`

### 预留字段

后续可继续加：

- `score`
- `created_at`
- `updated_at`
- `related_collision`
- `tags`

## 后端设计

### `server.py`

目前 `server.py` 是直接扫描 `workspace/outputs/*.md`。

改造后逻辑：

1. 优先读取 `workspace/outputs/index.json`
2. 如果索引存在且合法，直接从索引生成列表
3. 如果索引缺失，回退到扫描模式：
   - 扫描 `paper-cards/`
   - 扫描 `collisions/`
   - 扫描 `directions/`
   - 再兼容扫描旧平铺目录里的 `.md`
4. 需要时可重建索引

### 文档读取

`load_document(name)` 也不能再假设文件就在 `workspace/outputs/` 根目录。

改造为：

- 先从索引查 `name -> path`
- 再去那个 path 读文档
- 如果索引没有，再回退扫描所有支持目录

## 写入策略

本轮不把“文档生成”完全自动化进代码里，但需要把**路径约定**统一下来。

约定如下：

- `paper_card` -> `workspace/outputs/paper-cards/`
- `collision` -> `workspace/outputs/collisions/`
- `direction` -> `workspace/outputs/directions/`

同时增加一个轻量索引维护模块，负责：

- 从输出文件重建 `index.json`
- 从新生成文件追加/更新索引

## 迁移策略

新增一个迁移脚本，例如：

`migrate_outputs.py`

职责：

1. 扫描旧的 `workspace/outputs/*.md`
2. 读取 frontmatter 判断类型
3. 把文件移动到对应子目录
4. 生成或重建 `index.json`

迁移后仍保留兼容读取，避免未迁移完成前 Web 直接失效。

## Web 展示设计

前端不需要大改视觉结构。

保持：

- 左侧状态面板
- 筛选按钮
- 文档列表
- 右侧阅读区

但数据来源从“扫描结果”切到“索引优先”之后，会带来这些好处：

- 分组更稳定
- 文档名和路径不再强耦合
- 后面容易加来源论文和分数摘要

## 兼容性要求

这轮必须兼容两种状态：

### 新结构

```text
workspace/outputs/paper-cards/*.md
workspace/outputs/collisions/*.md
workspace/outputs/directions/*.md
workspace/outputs/index.json
```

### 旧结构

```text
workspace/outputs/*.md
```

Web 和后端在两种结构下都要能读。

## 受影响文件

### 修改

- `server.py`
- `web/app.js`
- `web/index.html`（若需要少量文案调整）
- `tests/test_server.py`
- `tests/test_runtime_smoke.py`
- `tests/test_skill_packaging.py`
- `README.md`
- `PROJECT_STATUS.md`

### 新增

- `migrate_outputs.py`
- `tests/test_output_migration.py`
- `workspace/outputs/paper-cards/.gitkeep`
- `workspace/outputs/collisions/.gitkeep`
- `workspace/outputs/directions/.gitkeep`

### 模板同步

还要同步到：

- `skills/research-workflow/assets/project-template/...`

## 测试策略

### 1. 后端读取测试

覆盖：

- 新结构从索引读取
- 新结构无索引时扫描子目录
- 旧平铺目录仍可读

### 2. 迁移测试

覆盖：

- 旧平铺 markdown 被正确分流到目标子目录
- `index.json` 被正确生成

### 3. 打包测试

确认模板项目里包含新的输出子目录骨架。

### 4. 真实输出冒烟

更新现有 smoke test，使其适配新路径与索引。

## 风险

### 风险 1：迁移后旧路径失效

缓解：

- 保留兼容回退
- 先做读取兼容，再做迁移脚本

### 风险 2：索引与真实文件不同步

缓解：

- 后端在索引缺失/损坏时可回退扫描
- 提供重建索引能力

### 风险 3：模板和主项目结构分叉

缓解：

- 同步修改主项目与 `project-template`
- 用现有打包测试兜底

## 验收标准

完成后应满足：

1. 输出目录物理上分成 `paper-cards / collisions / directions`
2. 新增 `index.json`
3. Web 继续可用，并优先读取索引
4. 旧平铺目录在迁移前后都能正常显示
5. 有迁移脚本可将旧文件搬迁到新结构
6. 模板项目结构同步更新
7. 全量测试继续通过
