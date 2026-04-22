const listEl = document.querySelector("#documentList");
const viewEl = document.querySelector("#documentView");
const emptyEl = document.querySelector("#emptyState");
const refreshButton = document.querySelector("#refreshButton");
const stateEl = document.querySelector("#stateSummary");
const uploadButton = document.querySelector("#uploadButton");
const uploadInput = document.querySelector("#paperUploadInput");
const uploadHintEl = document.querySelector("#uploadHint");
const uploadStatusListEl = document.querySelector("#uploadStatusList");
const filterButtons = [...document.querySelectorAll("[data-filter]")];
const documentTypeOrder = ["paper_card", "collision", "direction"];

let activeName = "";
let activeFilter = "all";
let uploadPollTimer = 0;
let pendingUploadBatchId = "";

refreshButton.addEventListener("click", refresh);
uploadButton.addEventListener("click", () => uploadInput.click());
uploadInput.addEventListener("change", async () => {
  const files = [...uploadInput.files];
  uploadInput.value = "";
  if (!files.length) {
    return;
  }
  await uploadFiles(files);
});
for (const button of filterButtons) {
  button.addEventListener("click", () => {
    const nextFilter = button.dataset.filter || "all";
    if (nextFilter === activeFilter) {
      return;
    }
    activeFilter = nextFilter;
    activeName = "";
    refresh();
  });
}

refresh();
loadUploadStatus();

async function refresh() {
  await Promise.all([loadState(), loadDocuments(activeFilter)]);
}

async function uploadFiles(files) {
  const payload = new FormData();
  for (const file of files) {
    payload.append("files", file);
  }
  uploadHintEl.textContent = `正在上传 ${files.length} 个 PDF...`;

  const response = await fetch("/api/upload-papers", {
    method: "POST",
    body: payload,
  });
  const result = await response.json();
  if (!response.ok) {
    uploadHintEl.textContent = result.error || "上传失败";
    return;
  }

  pendingUploadBatchId = result.batch_id || "";
  renderUploadStatus({
    files: result.files || [],
    is_processing: true,
    queue_size: 0,
    active_batch_id: pendingUploadBatchId,
    last_error: "",
  });
  uploadHintEl.textContent = `已接收 ${files.length} 个 PDF，开始处理。`;
  pollUploadStatus();
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
  const query = activeFilter ? `?type=${encodeURIComponent(activeFilter)}` : "";
  const response = await fetch(`/api/documents${query}`);
  const documents = await response.json();
  listEl.innerHTML = "";
  updateFilterButtons();

  if (!documents.length) {
    emptyEl.classList.remove("hidden");
    viewEl.classList.add("hidden");
    activeName = "";
    return;
  }

  renderDocumentGroups(documents);

  if (activeName && documents.some((doc) => doc.name === activeName)) {
    await loadDocument(activeName);
    return;
  }

  if (!activeName) {
    await loadDocument(documents[0].name);
    return;
  }

  activeName = documents[0].name;
  await loadDocument(activeName);
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

function updateFilterButtons() {
  for (const button of filterButtons) {
    button.classList.toggle("active", button.dataset.filter === activeFilter);
  }
}

function renderDocumentGroups(documents) {
  const groupedDocuments = groupDocumentsByType(documents);

  for (const [type, entries] of groupedDocuments) {
    const groupEl = globalThis.document.createElement("section");
    groupEl.className = "document-group";

    const titleEl = globalThis.document.createElement("div");
    titleEl.className = "group-title";
    titleEl.textContent = `${type} (${entries.length})`;
    groupEl.appendChild(titleEl);

    for (const doc of entries) {
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
      groupEl.appendChild(button);
    }

    listEl.appendChild(groupEl);
  }
}

function groupDocumentsByType(documents) {
  const groups = [];

  for (const type of documentTypeOrder) {
    const entries = documents.filter((doc) => doc.type === type);
    if (entries.length) {
      groups.push([type, entries]);
    }
  }

  const otherEntries = documents.filter((doc) => !documentTypeOrder.includes(doc.type));
  if (otherEntries.length) {
    groups.push(["other", otherEntries]);
  }

  return groups;
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

async function loadUploadStatus() {
  const response = await fetch("/api/upload-status");
  const status = await response.json();
  renderUploadStatus(status);
  if ((status.is_processing || status.queue_size > 0) && !uploadPollTimer) {
    uploadPollTimer = window.setTimeout(pollUploadStatus, 1200);
  }
  return status;
}

async function pollUploadStatus() {
  clearTimeout(uploadPollTimer);
  uploadPollTimer = 0;
  const status = await loadUploadStatus();
  if (status.is_processing || status.queue_size > 0) {
    uploadPollTimer = window.setTimeout(pollUploadStatus, 1200);
    return;
  }

  if (pendingUploadBatchId && status.active_batch_id === pendingUploadBatchId) {
    pendingUploadBatchId = "";
    uploadHintEl.textContent = status.last_error ? status.last_error : "处理完成，面板已刷新。";
    await refresh();
  }
}

function renderUploadStatus(status) {
  const files = Array.isArray(status.files) ? status.files : [];
  uploadStatusListEl.innerHTML = "";

  if (!files.length) {
    if (!pendingUploadBatchId) {
      uploadHintEl.textContent = "支持多选 PDF，上传后会自动开始处理。";
    }
    return;
  }

  for (const item of files) {
    const row = globalThis.document.createElement("div");
    row.className = "upload-status-item";
    row.innerHTML = `
      <span class="upload-file-name">${escapeHtml(item.name || "")}</span>
      <span class="upload-file-state ${escapeHtml(item.status || "unknown")}">${escapeHtml(
        item.status || "unknown"
      )}</span>
    `;
    if (item.error) {
      const errorEl = globalThis.document.createElement("div");
      errorEl.className = "upload-file-error";
      errorEl.textContent = item.error;
      row.appendChild(errorEl);
    }
    uploadStatusListEl.appendChild(row);
  }

  if (status.last_error) {
    uploadHintEl.textContent = status.last_error;
  } else if (status.is_processing) {
    uploadHintEl.textContent = `正在处理 ${files.length} 个 PDF...`;
  } else {
    uploadHintEl.textContent = "最近一批 PDF 已处理完成。";
  }
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
