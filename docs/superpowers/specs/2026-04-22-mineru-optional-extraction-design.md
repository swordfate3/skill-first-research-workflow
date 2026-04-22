# MinerU 可选高级提取设计

Last updated: 2026-04-22

## 背景

当前 `skill-first-research-workflow` 已经打通了从 `workspace/papers/` 到：

- `workspace/extracted/`
- `workspace/memory/papers/`
- `workspace/outputs/`
- 本地 Web 面板

的主流程。

现有 PDF 提取由 `extract_pdfs.py` 负责，默认路径是：

1. `pdftotext -layout`
2. 失败时回退到 `pypdf`

这条路径对普通文本型 PDF 足够轻便，但对以下场景不够稳：

- 扫描 PDF
- 表格密集论文
- 公式密集论文
- 图文混排严重依赖版面的论文

用户本机已经启用了 MinerU Docker，并且环境中已有可复用的封装脚本：

`/home/fate/.agents/skills/mineru-doc-to-md/scripts/mineru_to_md.sh`

因此本次目标不是替换现有轻量提取，而是增加一个 **可选高级提取后端**。

## 目标

在不破坏现有默认行为的前提下，为研究工作流增加 MinerU 提取能力：

- 默认继续使用轻量提取
- 在普通提取失败或用户明确要求时可切到 MinerU
- 提取结果仍然统一落到当前项目约定的 `workspace/extracted/<paper>/`
- skill 文档明确何时使用 MinerU
- 打包模板与主项目保持一致

## 非目标

本次不做这些事：

- 不把所有 PDF 默认改成 MinerU
- 不新增 Web 配置页面
- 不引入数据库或后台任务系统
- 不把 MinerU 的原始目录结构直接暴露给后续工作流
- 不在这轮实现复杂的“自动判断论文是否表格/公式密集”的高风险启发式

## 用户体验

### 默认路径

用户继续像现在一样使用：

1. 把论文放进 `workspace/papers/`
2. 调用 `research-workflow` skill

如果 PDF 是普通文本型文档，工作流继续走轻量提取，不需要额外动作。

### MinerU 路径

以下情况进入 MinerU 路径：

1. 轻量提取失败
2. 用户明确要求使用 MinerU
3. 未来可扩展的自动判定先不在本轮实现

进入 MinerU 路径后，工作流仍然只认统一产物：

- `text.md`
- `tables.md`
- `equations.md`
- `figures.md`
- `manifest.json`

后续 `paper memory / card / collision / direction` 完全不需要知道底层是轻量提取还是 MinerU。

## 方案比较

### 方案 A：默认轻量，按需切 MinerU（推荐）

做法：

- 保留现有提取路径为默认
- 新增 MinerU 提取器
- 加入显式开关和失败回退

优点：

- 与当前项目最兼容
- 小论文不被重处理拖慢
- 用户已有 Docker 资源可以直接发挥作用

缺点：

- 提取逻辑会多一层策略分支

### 方案 B：所有 PDF 默认走 MinerU

优点：

- 路径统一

缺点：

- 成本更高
- 启动更慢
- 对普通论文收益不成比例
- Docker/MinerU 故障会直接影响所有提取

### 方案 C：不改代码，只在 skill 文本里手动要求 MinerU

优点：

- 改动最小

缺点：

- 自动化不足
- 容易因为提示词漂移而失效
- 运行结果不稳定

**结论：选择方案 A。**

## 架构设计

### 1. 提取策略层

在 `extract_pdfs.py` 中显式引入提取策略：

- `lightweight`
- `mineru`
- `auto`

其中：

- `lightweight`：只走 `pdftotext / pypdf`
- `mineru`：只走 MinerU wrapper
- `auto`：先轻量，失败后回退 MinerU

默认策略为 `auto`。

### 2. MinerU 适配层

新增内部函数，职责是把 MinerU 的输出适配到当前工作流格式：

- 调用 wrapper script
- 读取输出目录中的 markdown / json
- 整理成统一的 `text/tables/equations/figures/manifest`

关键原则：

- 对后续阶段暴露统一接口
- 不要求工作流知道 MinerU 的原始目录结构

### 3. 输出标准化

无论轻量还是 MinerU，最终都写入：

`workspace/extracted/<paper-stem>/`

并保证 `manifest.json` 至少包含：

- `source`
- `source_hash`
- `status`
- `strategy`
- `files`
- `uncertainty`

MinerU 路径会把 `strategy` 写成类似：

- `mineru-docker-wrapper`
- 或 `auto-fallback-to-mineru`

### 4. Skill 集成

更新 `skills/research-workflow/SKILL.md`：

- 默认使用轻量提取
- 普通提取失败时自动改用 MinerU
- 用户若明确提到扫描件、表格/公式很重要，优先使用 MinerU
- 使用 MinerU 后，优先依据其结构化结果撰写 paper memory 与 paper card

### 5. 打包模板同步

同步修改：

- `extract_pdfs.py`
- `skills/research-workflow/assets/project-template/extract_pdfs.py`
- `skills/research-workflow/SKILL.md`

保证通过 `skills add` 安装出来的项目与当前主项目行为一致。

## 数据流

### 现有数据流

`paper.pdf -> lightweight extraction -> workspace/extracted/... -> memory/card/collision/direction`

### 改造后数据流

`paper.pdf -> extraction strategy selector -> lightweight or MinerU -> normalized extracted outputs -> memory/card/collision/direction`

也就是说，后续研究链路不需要改数据消费方式。

## CLI 与接口设计

扩展 `extract_pdfs.py` CLI：

- `--strategy auto|lightweight|mineru`
- 可选 `--mineru-output-root` 仅在内部调试时使用，本轮默认不对 README 暴露

扩展 `extract_all()`：

- 接收 `strategy` 参数
- 保留现有 `extractor` 注入点，方便单元测试
- 新增可选的 `mineru_runner` 注入点，避免测试中真的跑 Docker

## 错误处理

### lightweight 失败

- 若策略为 `auto`：回退到 MinerU
- 若策略为 `lightweight`：直接记失败 manifest

### MinerU 失败

- 写 `failed` manifest
- 保留错误信息
- 不生成半成品 extracted 文档

### 输出不完整

如果 MinerU 成功但没有产生足够内容：

- 仍写 manifest
- 在 `uncertainty` 里明确标注内容缺失
- 后续文档生成时保守使用并提示人工复核

## 测试策略

### 单元测试

扩展 `tests/test_extract_pdfs.py` 覆盖：

1. 默认轻量提取成功
2. `auto` 模式下 lightweight 失败后回退 MinerU
3. `mineru` 模式直走 MinerU
4. manifest 正确记录 strategy

### 打包测试

保证模板里仍包含更新后的 `extract_pdfs.py` 和 `SKILL.md`。

### 运行时冒烟

不在单测中真实启动 Docker。
通过依赖注入模拟 MinerU wrapper 返回结果，避免测试变慢和环境耦合。

## 风险

### 风险 1：MinerU 输出结构在不同版本下不稳定

缓解：

- 适配层只依赖最小必要产物
- 读取失败时给出明确错误，而不是写入伪正确数据

### 风险 2：Docker 调用拖慢工作流

缓解：

- 默认只在 `auto` 回退或显式指定时使用 MinerU

### 风险 3：主项目与打包模板分叉

缓解：

- 同一轮同时修改主项目和 `assets/project-template`
- 通过现有打包测试兜底

## 验收标准

本轮完成后应满足：

1. 普通 PDF 仍可按现有方式提取
2. 在 lightweight 失败时，`auto` 策略会改用 MinerU
3. MinerU 结果会被标准化写入 `workspace/extracted/<paper>/`
4. `manifest.json` 能区分轻量与 MinerU 策略
5. `research-workflow` skill 明确说明何时调用 MinerU
6. 模板项目与主项目行为一致
7. 全量测试继续通过
