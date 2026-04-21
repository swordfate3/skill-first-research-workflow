# 研究面板与方向链路 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让当前两篇真实论文跑通 `memory -> paper card -> collision -> direction`，并把 Web 升级成可按 `paper card / collision / direction` 浏览的研究面板。

**Architecture:** 保持“文件系统是唯一状态源”的现有架构，不引入新服务端写接口。后端只增强只读聚合能力，前端增加类型筛选和更清晰的文档分组展示，真实方向输出继续落在 `workspace/outputs/` 并通过 `state.py` 标记完成。

**Tech Stack:** Python 3.10 + `uv`, `unittest`, 原生 `http.server`, 原生 HTML/CSS/JavaScript

---

## File Structure

本轮涉及文件和职责如下：

- Modify: `state.py`
  - 若真实方向链路测试暴露状态问题，在这里修正 `pending_directions` 与 `mark-direction` 的一致性。
- Modify: `workflow.py`
  - 若真实链路需要额外动作提示或状态顺序修正，在这里做最小改动。
- Modify: `server.py`
  - 为 Web 提供更明确的文档类型、排序和筛选支持。
- Modify: `web/index.html`
  - 添加类型筛选入口和更清晰的三栏研究面板骨架。
- Modify: `web/app.js`
  - 拉取状态、筛选文档、维持右侧详情阅读。
- Modify: `web/styles.css`
  - 为筛选条、文档列表和阅读区提供稳定布局。
- Create: `tests/test_server.py`
  - 覆盖文档排序、类型筛选、状态接口返回。
- Modify: `tests/test_state.py`
  - 覆盖真实方向待办消失、状态落盘一致性。
- Modify: `tests/test_workflow.py`
  - 覆盖 `prepare` 在方向生成前后返回的动作序列。
- Modify: `tests/test_web_assets.py`
  - 覆盖前端筛选控件与关键 DOM 逻辑。
- Modify: `PROJECT_STATUS.md`
  - 记录本轮“真实方向链路 + 研究面板”完成情况。

---

### Task 1: 为方向链路和研究面板先补失败测试

**Files:**
- Create: `tests/test_server.py`
- Modify: `tests/test_state.py`
- Modify: `tests/test_workflow.py`
- Modify: `tests/test_web_assets.py`

- [ ] **Step 1: 在 `tests/test_state.py` 增加“方向已生成后不再待办”的失败测试**

```python
def test_marked_direction_is_removed_from_pending_queue(self):
    state = load_state_module()

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        papers_dir = root / "workspace" / "papers"
        memory_dir = root / "workspace" / "memory" / "papers"
        papers_dir.mkdir(parents=True)
        memory_dir.mkdir(parents=True)

        for name, topic in [
            ("paper-a.txt", "aes differential neural distinguisher"),
            ("paper-b.txt", "aes ciphertext distinguisher neural"),
        ]:
            (papers_dir / name).write_text(topic, encoding="utf-8")
            state.scan_workspace(root)
            state.mark_paper_memory(root, name, f"workspace/memory/papers/{Path(name).stem}.json")
            (memory_dir / f"{Path(name).stem}.json").write_text(
                json_memory_fixture(name, topic), encoding="utf-8"
            )
            state.mark_paper_card(root, name, f"workspace/outputs/{Path(name).stem}.md")

        collision = state.mark_collision(
            root, "paper-a.txt", "paper-b.txt", "workspace/outputs/collision-a-b.md"
        )
        before = state.scan_workspace(root)
        state.mark_direction(root, collision["key"], "workspace/outputs/004-direction-a-b.md")
        after = state.scan_workspace(root)

    self.assertEqual(len(before["pending_directions"]), 1)
    self.assertEqual(after["pending_directions"], [])
```

- [ ] **Step 2: 在 `tests/test_workflow.py` 增加“方向生成后 next_actions 清空”的失败测试**

```python
def test_prepare_workspace_stops_requesting_direction_after_mark_direction(self):
    workflow = load_workflow_module()

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        papers = root / "workspace" / "papers"
        memory_dir = root / "workspace" / "memory" / "papers"
        papers.mkdir(parents=True)
        memory_dir.mkdir(parents=True)
        (papers / "paper-a.txt").write_text("aes neural differential", encoding="utf-8")
        (papers / "paper-b.txt").write_text("aes ciphertext neural", encoding="utf-8")

        workflow.state.scan_workspace(root)
        for name in ("paper-a.txt", "paper-b.txt"):
            workflow.state.mark_paper_memory(root, name, f"workspace/memory/papers/{Path(name).stem}.json")
            workflow.state.mark_paper_card(root, name, f"workspace/outputs/{Path(name).stem}.md")
            (memory_dir / f"{Path(name).stem}.json").write_text(
                '{"classification":{"primary_tags":["aes"],"keywords":["aes","neural"]},"innovation_seeds":{"transferable_techniques":[{"technique":"neural distinguisher","potential_targets":["aes"],"reasoning":"shared"}],"open_problems":["generalization"],"weakness_opportunities":["better evidence"]}}',
                encoding="utf-8",
            )

        collision = workflow.state.mark_collision(root, "paper-a.txt", "paper-b.txt", "workspace/outputs/003-collision.md")
        before = workflow.prepare_workspace(root)
        workflow.state.mark_direction(root, collision["key"], "workspace/outputs/004-direction.md")
        after = workflow.prepare_workspace(root)

    self.assertIn("Draft 1 high-priority research direction.", before["next_actions"])
    self.assertNotIn("Draft 1 high-priority research direction.", after["next_actions"])
```

- [ ] **Step 3: 新建 `tests/test_server.py`，为筛选与排序写失败测试**

```python
from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


def load_server_module():
    module_path = Path(__file__).resolve().parents[1] / "server.py"
    spec = importlib.util.spec_from_file_location("skill_first_server", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ServerTests(unittest.TestCase):
    def test_list_documents_sorts_by_type_then_name(self):
        server = load_server_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            outputs = root / "workspace" / "outputs"
            outputs.mkdir(parents=True)
            (outputs / "004-direction-test.md").write_text(
                "---\ntitle: Direction\ntype: direction\nstatus: pending\n---\n# Direction\n",
                encoding="utf-8",
            )
            (outputs / "003-collision-test.md").write_text(
                "---\ntitle: Collision\ntype: collision\nstatus: pending\n---\n# Collision\n",
                encoding="utf-8",
            )
            (outputs / "001-paper-card-test.md").write_text(
                "---\ntitle: Card\ntype: paper_card\nstatus: pending\n---\n# Card\n",
                encoding="utf-8",
            )

            server.OUTPUTS_ROOT = outputs
            docs = server.list_documents()

        self.assertEqual([doc["type"] for doc in docs], ["paper_card", "collision", "direction"])

    def test_list_documents_can_filter_by_type(self):
        server = load_server_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            outputs = root / "workspace" / "outputs"
            outputs.mkdir(parents=True)
            (outputs / "001-paper-card-test.md").write_text(
                "---\ntitle: Card\ntype: paper_card\nstatus: pending\n---\n# Card\n",
                encoding="utf-8",
            )
            (outputs / "004-direction-test.md").write_text(
                "---\ntitle: Direction\ntype: direction\nstatus: pending\n---\n# Direction\n",
                encoding="utf-8",
            )

            server.OUTPUTS_ROOT = outputs
            docs = server.list_documents(doc_type="direction")

        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0]["type"], "direction")
```

- [ ] **Step 4: 在 `tests/test_web_assets.py` 为筛选控件与类型常量写失败测试**

```python
def test_app_js_contains_type_filters_and_document_type_order(self):
    app_js = (Path(__file__).resolve().parents[1] / "web" / "app.js").read_text(
        encoding="utf-8"
    )
    index_html = (Path(__file__).resolve().parents[1] / "web" / "index.html").read_text(
        encoding="utf-8"
    )

    self.assertIn("filterButton", app_js)
    self.assertIn("paper_card", app_js)
    self.assertIn("collision", app_js)
    self.assertIn("direction", app_js)
    self.assertIn('data-filter="direction"', index_html)
```

- [ ] **Step 5: 运行测试确认它们先失败**

Run:

```bash
uv run python -m unittest tests/test_state.py tests/test_workflow.py tests/test_server.py tests/test_web_assets.py -v
```

Expected:

- 新增的方向测试至少有一个失败
- `tests/test_server.py` 因 `list_documents(doc_type=...)` 尚未支持而失败
- `tests/test_web_assets.py` 因筛选控件尚未存在而失败

- [ ] **Step 6: Commit**

```bash
git add tests/test_state.py tests/test_workflow.py tests/test_server.py tests/test_web_assets.py
git commit -m "test(panel): 补充方向链路与研究面板回归用例"
```

---

### Task 2: 修正方向状态链路并补齐真实方向输出

**Files:**
- Modify: `state.py`
- Modify: `workflow.py`
- Modify: `workspace/outputs/004-direction-*.md` (runtime output, not committed)

- [ ] **Step 1: 在 `state.py` 明确 `mark_direction()` 落盘字段，并让 `build_pending_directions()` 跳过已标记碰撞**

```python
def mark_direction(root: Path, collision_key: str, output_path: str) -> dict:
    state = load_state(root)
    directions = state.setdefault("directions", {})
    directions[collision_key] = {
        "collision_key": collision_key,
        "output": output_path,
        "status": "created",
    }
    save_state(root, state)
    return directions[collision_key]


def build_pending_directions(state: dict) -> list[dict]:
    directions = state.get("directions", {})
    pending = []
    for key, collision in state.get("collisions", {}).items():
        if key in directions:
            continue
        score = collision.get("score", 0)
        if score >= MIN_DIRECTION_SCORE:
            pending.append({
                "collision_key": key,
                "collision": collision,
                "score": score,
            })
    return pending[:MAX_PENDING_DIRECTIONS]
```

- [ ] **Step 2: 若 `workflow.py` 的提示顺序与真实链路不一致，做最小修正**

```python
if pending_directions:
    count = len(pending_directions)
    label = "direction" if count == 1 else "directions"
    actions.append(f"Draft {count} high-priority research {label}.")
```

- [ ] **Step 3: 运行刚才的测试，确认状态逻辑通过**

Run:

```bash
uv run python -m unittest tests/test_state.py tests/test_workflow.py tests/test_server.py tests/test_web_assets.py -v
```

Expected:

- `test_marked_direction_is_removed_from_pending_queue` PASS
- `test_prepare_workspace_stops_requesting_direction_after_mark_direction` PASS
- 服务器和前端相关测试仍然可能失败

- [ ] **Step 4: 用真实论文跑一遍 `prepare`，确认待生成方向存在**

Run:

```bash
uv run python workflow.py prepare
```

Expected:

- JSON 中出现 `pending_directions`
- 或者清楚表明没有待生成方向，需要先检查 collision 分数

- [ ] **Step 5: 在 `workspace/outputs/` 生成真实 `direction` 文档并标记状态**

参考文档内容模板：

```md
---
title: AES 神经区分器与 FESLA 的研究方向
type: direction
status: pending
source_papers:
  - Differential-neural cryptanalysis on AES(1).pdf
  - Distinguishing Full-Round AES-256 in a Ciphertext-Only Setting via Hybrid Statistical Learning.pdf
---

# AES 神经区分器与 FESLA 的研究方向

## 研究问题
- 能否把差分神经区分器与仅密文统计学习框架结合，形成更稳健的 AES 区分流程？

## 为什么值得做
- 两篇论文都围绕 AES 区分，但证据来源不同，存在互补空间。

## 基于哪些碰撞
- `paper-a.txt::paper-b.txt`

## 技术路径
- 统一输入表示
- 对比统计特征与神经特征
- 设计混合评分器

## 第一个实验
- 用两篇论文各自最小设置构造一个混合 distinguisher baseline。

## 风险
- 特征融合后可能没有增益

## 推荐分数
- 0.78

## 术语对照
- 区分器（distinguisher）
- 仅密文（ciphertext-only）
```

标记命令：

```bash
uv run python state.py mark-direction "<collision_key>" "workspace/outputs/004-direction-<slug>.md"
```

- [ ] **Step 6: 再跑 `prepare`，确认该方向不再待办**

Run:

```bash
uv run python workflow.py prepare
```

Expected:

- 刚才那条 `collision_key` 不再出现在 `pending_directions`

- [ ] **Step 7: Commit**

```bash
git add state.py workflow.py tests/test_state.py tests/test_workflow.py tests/test_server.py
git commit -m "feat(direction): 跑通真实方向状态链路"
```

---

### Task 3: 把 Web 升级成研究面板

**Files:**
- Modify: `server.py`
- Modify: `web/index.html`
- Modify: `web/app.js`
- Modify: `web/styles.css`
- Modify: `tests/test_server.py`
- Modify: `tests/test_web_assets.py`

- [ ] **Step 1: 为 `server.py` 增加类型排序和可选过滤参数**

```python
TYPE_ORDER = {
    "paper_card": 0,
    "collision": 1,
    "direction": 2,
    "prototype": 3,
    "draft": 4,
    "note": 9,
}


def list_documents(doc_type: str | None = None) -> list[dict]:
    OUTPUTS_ROOT.mkdir(parents=True, exist_ok=True)
    documents = []
    for path in sorted(OUTPUTS_ROOT.glob("*.md")):
        content = path.read_text(encoding="utf-8", errors="replace")
        metadata, body = split_frontmatter(content)
        item_type = metadata.get("type") or "note"
        if doc_type and item_type != doc_type:
            continue
        documents.append(
            {
                "name": path.name,
                "title": metadata.get("title") or infer_title(body) or path.stem,
                "type": item_type,
                "status": metadata.get("status") or "unknown",
            }
        )
    return sorted(documents, key=lambda doc: (TYPE_ORDER.get(doc["type"], 99), doc["name"]))
```

在 handler 中读取 query：

```python
if parsed.path == "/api/documents":
    query = parse_qs(parsed.query)
    doc_type = query.get("type", [""])[0] or None
    self._send_json(list_documents(doc_type=doc_type))
    return
```

- [ ] **Step 2: 在 `web/index.html` 增加筛选条**

```html
<section class="filter-panel">
  <div class="sidebar-title">类型</div>
  <div id="filterBar" class="filter-bar">
    <button class="filter-chip active" data-filter="all" type="button">全部</button>
    <button class="filter-chip" data-filter="paper_card" type="button">Paper Card</button>
    <button class="filter-chip" data-filter="collision" type="button">Collision</button>
    <button class="filter-chip" data-filter="direction" type="button">Direction</button>
  </div>
</section>
```

- [ ] **Step 3: 在 `web/app.js` 中接入筛选状态**

```javascript
const filterBar = document.querySelector("#filterBar");
let activeFilter = "all";

filterBar?.addEventListener("click", async (event) => {
  const button = event.target.closest(".filter-chip");
  if (!button) return;
  activeFilter = button.dataset.filter || "all";
  [...filterBar.querySelectorAll(".filter-chip")].forEach((chip) => {
    chip.classList.toggle("active", chip.dataset.filter === activeFilter);
  });
  activeName = "";
  await loadDocuments();
});

async function loadDocuments() {
  const suffix = activeFilter === "all" ? "" : `?type=${encodeURIComponent(activeFilter)}`;
  const response = await fetch(`/api/documents${suffix}`);
  const documents = await response.json();
  // 其余列表渲染逻辑保持不变
}
```

- [ ] **Step 4: 在 `web/styles.css` 中给筛选条和三栏阅读做稳定样式**

```css
.filter-panel {
  margin-bottom: 20px;
}

.filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.filter-chip {
  border-color: var(--line);
  background: var(--panel);
  color: var(--ink);
  padding: 8px 10px;
}

.filter-chip.active {
  border-color: var(--accent);
  background: var(--accent);
  color: #fff;
}

.document-list {
  display: grid;
  gap: 8px;
  max-height: calc(100vh - 240px);
  overflow: auto;
}
```

- [ ] **Step 5: 跑 Web 相关测试**

Run:

```bash
uv run python -m unittest tests/test_server.py tests/test_web_assets.py -v
```

Expected:

- 所有新加的 server / web 相关测试 PASS

- [ ] **Step 6: 本地启动服务做一次人工检查**

Run:

```bash
uv run python server.py
```

Expected:

- 页面能显示筛选条
- 点击 `Paper Card / Collision / Direction` 时列表切换
- 右侧详情仍正常展示

- [ ] **Step 7: Commit**

```bash
git add server.py web/index.html web/app.js web/styles.css tests/test_server.py tests/test_web_assets.py
git commit -m "feat(panel): 升级研究面板类型筛选与阅读体验"
```

---

### Task 4: 回归验证并更新项目状态

**Files:**
- Modify: `PROJECT_STATUS.md`

- [ ] **Step 1: 跑完整回归**

Run:

```bash
uv run python -m unittest discover -s tests -v
```

Expected:

- 全部测试 PASS

- [ ] **Step 2: 记录本轮完成情况到 `PROJECT_STATUS.md`**

```md
- Validated the real-paper flow through direction output and state transitions.
- Upgraded the local web page into a research panel with type filters for paper cards, collisions, and directions.
```

- [ ] **Step 3: 再次检查真实工作区输出**

Run:

```bash
uv run python workflow.py prepare
```

Expected:

- 真实输出状态与 `workspace/outputs/` 一致
- 不会重复提示已标记的方向

- [ ] **Step 4: Commit**

```bash
git add PROJECT_STATUS.md
git commit -m "docs(status): 更新研究面板推进结果"
```

---

## Self-Review

### Spec coverage

- 真实方向链路：Task 1 + Task 2 覆盖
- Web 三块面板与类型筛选：Task 3 覆盖
- 回归验证：Task 4 覆盖

没有发现 spec 中无人负责的要求。

### Placeholder scan

已检查本计划，没有 `TBD`、`TODO`、`implement later`、`write tests for the above` 这类占位描述。

### Type consistency

- 文档类型统一使用 `paper_card`、`collision`、`direction`
- 状态链路统一使用 `mark_direction()` 与 `pending_directions`
- API 过滤参数统一命名为 `type`

未发现前后命名冲突。
