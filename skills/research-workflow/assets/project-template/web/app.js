const listEl = document.querySelector("#documentList");
const viewEl = document.querySelector("#documentView");
const emptyEl = document.querySelector("#emptyState");
const refreshButton = document.querySelector("#refreshButton");
const stateEl = document.querySelector("#stateSummary");

let activeName = "";

refreshButton.addEventListener("click", refresh);

refresh();

async function refresh() {
  await Promise.all([loadState(), loadDocuments()]);
}

async function loadState() {
  const response = await fetch("/api/state");
  const state = await response.json();
  stateEl.innerHTML = `
    <div><span class="state-number">${state.paper_count}</span> 论文</div>
    <div><span class="state-number">${state.memory_count}</span> 已建 memory</div>
    <div><span class="state-number">${state.collision_count}</span> 已碰撞组合</div>
    <div><span class="state-number">${state.pending_collisions.length}</span> 待碰撞组合</div>
    <div><span class="state-number">${state.direction_count}</span> 已生成方向</div>
    <div><span class="state-number">${state.pending_directions.length}</span> 待生成方向</div>
  `;
}

async function loadDocuments() {
  const response = await fetch("/api/documents");
  const documents = await response.json();
  listEl.innerHTML = "";

  if (!documents.length) {
    emptyEl.classList.remove("hidden");
    viewEl.classList.add("hidden");
    return;
  }

  for (const doc of documents) {
    const button = globalThis.document.createElement("button");
    button.className = "document-item";
    if (doc.name === activeName) {
      button.classList.add("active");
    }
    button.type = "button";
    button.dataset.name = doc.name;
    button.innerHTML = `
      <span class="document-title">${escapeHtml(doc.title)}</span>
      <span class="document-meta">${escapeHtml(doc.type)} · ${escapeHtml(doc.status)} · ${escapeHtml(doc.name)}</span>
    `;
    button.addEventListener("click", () => loadDocument(doc.name));
    listEl.appendChild(button);
  }

  if (!activeName) {
    await loadDocument(documents[0].name);
  }
}

async function loadDocument(name) {
  activeName = name;
  const response = await fetch(`/api/document?name=${encodeURIComponent(name)}`);
  const doc = await response.json();
  if (!response.ok) {
    viewEl.innerHTML = `<p>${escapeHtml(doc.error || "加载失败")}</p>`;
    return;
  }

  emptyEl.classList.add("hidden");
  viewEl.classList.remove("hidden");
  viewEl.innerHTML = `
    <span class="status ${escapeHtml(doc.status)}">${escapeHtml(doc.status)}</span>
    ${renderMarkdown(doc.body)}
  `;

  [...listEl.querySelectorAll(".document-item")].forEach((item) => {
    item.classList.toggle("active", item.dataset.name === name);
  });
}

function renderMarkdown(markdown) {
  const lines = markdown.split("\n");
  const html = [];
  let inList = false;

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) {
      if (inList) {
        html.push("</ul>");
        inList = false;
      }
      continue;
    }

    if (trimmed.startsWith("### ")) {
      if (inList) {
        html.push("</ul>");
        inList = false;
      }
      html.push(`<h3>${escapeHtml(trimmed.slice(4))}</h3>`);
    } else if (trimmed.startsWith("## ")) {
      if (inList) {
        html.push("</ul>");
        inList = false;
      }
      html.push(`<h2>${escapeHtml(trimmed.slice(3))}</h2>`);
    } else if (trimmed.startsWith("# ")) {
      if (inList) {
        html.push("</ul>");
        inList = false;
      }
      html.push(`<h1>${escapeHtml(trimmed.slice(2))}</h1>`);
    } else if (trimmed.startsWith("- ")) {
      if (!inList) {
        html.push("<ul>");
        inList = true;
      }
      html.push(`<li>${inlineMarkdown(trimmed.slice(2))}</li>`);
    } else {
      if (inList) {
        html.push("</ul>");
        inList = false;
      }
      html.push(`<p>${inlineMarkdown(trimmed)}</p>`);
    }
  }

  if (inList) {
    html.push("</ul>");
  }

  return html.join("\n");
}

function inlineMarkdown(value) {
  return escapeHtml(value).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
