# 研究面板与方向链路设计

日期：2026-04-21

## 目标

把当前 `skill-first-research-workflow` 从“能生成 paper card 和 collision 的文档流”推进成“能跑顺真实论文链路、并在网页里看清研究状态的研究面板”。

本轮只做一个聚焦子目标：

1. 用当前两篇真实论文跑通 `memory -> paper card -> collision -> direction`
2. 把 Web 从纯文档列表升级成可按类型查看的研究面板

## 当前现状

当前仓库已经具备：

- 可安装 skill 与 bootstrap 模板
- PDF 提取
- paper memory 状态结构
- paper card 输出
- Top-K collision 机制
- pending direction 状态
- Web 基础页面与状态数字

当前真实数据状态：

- `workspace/papers/` 有 2 篇真实论文
- `workspace/outputs/` 有 2 篇 `paper_card` 和 1 篇 `collision`
- 还没有 `direction` 输出
- Web 还不能按研究对象类型浏览，只能看一个混合文档列表

## 不做什么

本轮明确不做：

- 多模型后端调度
- 新的复杂打分算法
- SVG / 图表生成
- prototype / draft 自动生成
- 大规模 UI 重做

目标是把现有链路跑顺，而不是再引入新复杂度。

## 方案选择

已确认采用方案 2：

1. 先跑一遍真实论文的完整链路，补出 `direction`
2. 再把 Web 升级成三块：
   - 左侧状态
   - 中间按类型分组的列表
   - 右侧详情阅读

这是当前最稳的推进方式，因为它先验证真实数据流，再做最小必要的展示升级。

## 设计

### A. 真实链路补齐

当前链路目标：

```text
PDF -> extracted -> paper memory -> paper card -> collision -> direction
```

本轮需要确认：

1. `workflow.py prepare` 能正确返回：
   - `papers_to_memory`
   - `papers_to_card`
   - `pending_collisions`
   - `pending_directions`
2. `state.py` 中的方向待办逻辑在真实数据上成立
3. 至少生成 1 篇真实 `direction` 文档
4. 方向生成后，状态能被正确标记，不会反复重复进入待办

### B. Web 研究面板

当前 Web 只提供：

- 状态数字
- 一列混合文档列表
- 右侧 Markdown 详情

本轮升级后，页面结构如下：

#### 左侧：状态与筛选

显示：

- 论文数
- 已建 memory 数
- 已碰撞数
- 待碰撞数
- 已生成方向数
- 待生成方向数

并增加类型筛选：

- 全部
- paper card
- collision
- direction

#### 中间：按类型查看的文档列表

每条列表项显示：

- 标题
- 类型
- 状态
- 文件名

默认按以下顺序展示：

1. `paper_card`
2. `collision`
3. `direction`

如果启用筛选，只显示对应类型。

#### 右侧：详情阅读

保留现有 Markdown 渲染方式，但增加文档头部摘要：

- 标题
- 类型
- 状态

不新增复杂编辑能力，仍然只做阅读面板。

### C. 后端接口改动范围

为了支撑 Web 面板，需要对 `server.py` 做小范围增强：

1. `list_documents()` 返回更明确的排序键或可供前端分组的 `type`
2. `build_state_summary()` 继续复用现有 `scan_workspace()` 输出
3. 不新增新的写接口
4. 继续只读 `workspace/outputs/` 和 `workspace/state.json`

原则：

- 不把 Web 变成管理后台
- 仍然保持“文件系统是唯一状态源”

### D. 测试与验证

本轮至少覆盖三类验证：

1. 工作流验证
   - 真实论文链路能产出 `direction`
   - `pending_directions` 在生成后会消失

2. 前端 / API 验证
   - 文档列表能按类型过滤
   - 类型统计与状态面板不冲突

3. 回归验证
   - 现有 `paper card`
   - 现有 `collision`
   - 现有 Web 文档打开行为
   都不被破坏

## 实施顺序

### Phase 1

先验证并补齐真实论文链路：

- 检查当前 `workspace/state.json`
- 检查 `pending_directions`
- 生成真实 `direction`
- 标记状态并再次运行 `workflow.py prepare`

完成标准：

- 真实 `direction` 文件落到 `workspace/outputs/`
- `prepare` 不再重复提示同一条方向

### Phase 2

升级 Web 面板：

- 增加类型筛选控件
- 文档按类型分组或排序
- 保持右侧详情阅读体验

完成标准：

- 用户能一眼分出 `paper card / collision / direction`
- 页面仍然保持轻量，不变成复杂工作台

### Phase 3

做回归验证并记录结果。

## 风险

### 风险 1：真实方向链路提示词质量不稳定

处理方式：

- 本轮优先确认状态流正确
- 如果方向内容质量一般，先不改大框架，只调整模板和提示词

### 风险 2：Web 过早复杂化

处理方式：

- 只做筛选与阅读
- 不加编辑、拖拽、审批按钮

### 风险 3：状态与输出不同步

处理方式：

- 生成每个阶段输出后立刻调用对应 `mark-*`
- 用 `workflow.py prepare` 复检状态一致性

## 验收标准

本轮完成后，满足以下条件就算达标：

1. 两篇真实论文能跑出至少一个 `direction`
2. `workflow.py prepare` 输出和真实文件状态一致
3. Web 可以按 `paper card / collision / direction` 看结果
4. 页面上能直接看出“当前研究进展到哪一步”

## 之后的下一步

如果本轮顺利，下一轮再进入：

1. collision 打分增强
2. direction 质量增强
3. prototype / draft 从高分 direction 自动生长

也就是说，本轮是“把链路跑顺、把面板看顺”，不是“把所有后续能力一次做完”。
