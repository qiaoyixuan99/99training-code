// ── Constants ──
const NODE_W = 220;
const NODE_H = 100;
const GAP_X = 80;
const GAP_Y = 30;

// ── State ──
let threads = [];
let activeThread = null;
let treeRoots = [];
let allNodes = [];
let dateFilter = { from: "", to: "" };
let searchTimeout = null;

// ── DOM refs ──
const els = {
  stats:          document.getElementById("sidebar-stats"),
  threadList:     document.getElementById("thread-list"),
  treeHeader:     document.getElementById("tree-header"),
  treeLines:      document.getElementById("tree-lines"),
  treeNodes:      document.getElementById("tree-nodes"),
  placeholder:    document.getElementById("placeholder"),
  detailOverlay:  document.getElementById("detail-overlay"),
  detailPanel:    document.getElementById("detail-panel"),
  detailSubject:  document.getElementById("detail-subject"),
  detailBody:     document.getElementById("detail-body"),
  btnDetailClose: document.getElementById("btn-detail-close"),
  btnRefresh:     document.getElementById("btn-refresh"),
  btnSample:      document.getElementById("btn-import-sample"),
  btnSettings:    document.getElementById("btn-settings"),
  modalOverlay:   document.getElementById("modal-overlay"),
  btnModalClose:  document.getElementById("btn-modal-close"),
  btnSaveConfig:  document.getElementById("btn-save-config"),
  btnTestFetch:   document.getElementById("btn-test-fetch"),
  btnFetchSave:   document.getElementById("btn-fetch-save"),
  cfgEmail:       document.getElementById("cfg-email"),
  cfgAuthCode:    document.getElementById("cfg-auth-code"),
  cfgServer:      document.getElementById("cfg-server"),
  cfgPort:        document.getElementById("cfg-port"),
  cfgStatus:      document.getElementById("cfg-status"),
  searchInput:    document.getElementById("search-input"),
  searchResults:  document.getElementById("search-results"),
  dateFrom:       document.getElementById("date-from"),
  dateTo:         document.getElementById("date-to"),
  btnApplyFilter: document.getElementById("btn-apply-filter"),
  dlCheckboxes:   document.querySelectorAll(".dl-checkbox"),
};

// ── Toast ──
function toast(msg, type = "info") {
  const c = document.getElementById("toast-container");
  const el = document.createElement("div");
  el.className = "toast " + type;
  el.textContent = msg;
  c.appendChild(el);
  setTimeout(() => el.remove(), 4000);
}

// ── API wrappers ──
async function api(path, opts = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.message || `HTTP ${res.status}`);
  }
  return res.json();
}

// ── Date filter ──
function setDatePreset(preset) {
  const now = new Date();
  const y = now.getFullYear();
  const m = now.getMonth() + 1;

  switch (preset) {
    case "this-month":
      dateFilter.from = `${y}-${String(m).padStart(2, "0")}-01`;
      dateFilter.to = `${y}-${String(m).padStart(2, "0")}-${new Date(y, m, 0).getDate()}`;
      break;
    case "3months": {
      let startM = m - 2;
      let startY = y;
      if (startM <= 0) { startM += 12; startY--; }
      dateFilter.from = `${startY}-${String(startM).padStart(2, "0")}-01`;
      dateFilter.to = `${y}-${String(m).padStart(2, "0")}-${new Date(y, m, 0).getDate()}`;
      break;
    }
    case "this-year":
      dateFilter.from = `${y}-01-01`;
      dateFilter.to = `${y}-12-31`;
      break;
    case "all":
      dateFilter.from = "";
      dateFilter.to = "";
      break;
  }

  els.dateFrom.value = dateFilter.from;
  els.dateTo.value = dateFilter.to;

  document.querySelectorAll(".btn-preset").forEach(b => {
    b.classList.toggle("active", b.dataset.range === preset);
  });

  loadThreads();
}

function applyCustomFilter() {
  dateFilter.from = els.dateFrom.value;
  dateFilter.to = els.dateTo.value;
  document.querySelectorAll(".btn-preset").forEach(b => b.classList.remove("active"));
  loadThreads();
}

// ── Load sidebar ──
async function loadStatus() {
  const s = await api("/api/status");
  els.stats.innerHTML =
    `共 <b>${s.total_threads}</b> 个线程 · <b>${s.total_emails}</b> 封邮件` +
    (s.checked_today ? ` · <span style="color:#27ae60">今日已更新</span>` : "");

  // Only set date filter from server if we don't already have one
  if (!dateFilter.from && !dateFilter.to) {
    if (s.default_date_from || s.default_date_to) {
      dateFilter.from = s.default_date_from || "";
      dateFilter.to = s.default_date_to || "";
    }
    // Default to "all" if no server default
    els.dateFrom.value = dateFilter.from;
    els.dateTo.value = dateFilter.to;
  }
}

async function loadThreads() {
  const params = [];
  if (dateFilter.from) params.push(`date_from=${dateFilter.from}`);
  if (dateFilter.to) params.push(`date_to=${dateFilter.to}`);
  const qs = params.length ? "?" + params.join("&") : "";
  threads = await api(`/api/threads${qs}`);
  renderThreadList();
}

function renderThreadList() {
  els.threadList.innerHTML = "";
  if (threads.length === 0) {
    els.threadList.innerHTML =
      '<div style="padding:24px;text-align:center;color:#999;">当前时间范围暂无邮件线程<br>请调整筛选条件或点击"更新数据"获取邮件</div>';
    return;
  }
  threads.forEach(t => {
    const div = document.createElement("div");
    div.className = "thread-item" + (activeThread === t.thread_id ? " active" : "");
    div.innerHTML = `
      <div class="subject">${escHtml(t.subject)}</div>
      <div class="meta">
        <span>${escHtml(t.participants)}</span>
        <span class="count">${t.msg_count}</span>
      </div>
      <div class="meta" style="margin-top:2px">${t.latest_date}</div>
    `;
    div.addEventListener("click", () => openThread(t.thread_id));
    els.threadList.appendChild(div);
  });
}

// ── Search ──
els.searchInput.addEventListener("input", function() {
  clearTimeout(searchTimeout);
  const q = this.value.trim();
  if (!q) {
    els.searchResults.classList.add("hidden");
    els.searchResults.innerHTML = "";
    return;
  }
  searchTimeout = setTimeout(() => doSearch(q), 300);
});

els.searchInput.addEventListener("focus", function() {
  if (this.value.trim() && els.searchResults.children.length > 0) {
    els.searchResults.classList.remove("hidden");
  }
});

document.addEventListener("click", function(e) {
  if (!els.searchInput.contains(e.target) && !els.searchResults.contains(e.target)) {
    els.searchResults.classList.add("hidden");
  }
});

async function doSearch(q) {
  try {
    const results = await api(`/api/search?q=${encodeURIComponent(q)}`);
    renderSearchResults(results);
  } catch (err) {
    els.searchResults.innerHTML = `<div style="padding:12px;color:#e74c3c;font-size:12px">搜索失败: ${escHtml(err.message)}</div>`;
    els.searchResults.classList.remove("hidden");
  }
}

function renderSearchResults(results) {
  els.searchResults.innerHTML = "";
  if (results.length === 0) {
    els.searchResults.innerHTML = '<div style="padding:12px;color:#999;font-size:12px;text-align:center">未找到匹配的邮件</div>';
  } else {
    results.forEach(r => {
      const div = document.createElement("div");
      div.className = "search-result-item";
      div.innerHTML = `
        <div class="sri-subject">${escHtml(r.subject)}</div>
        <div class="sri-meta">
          <span>${escHtml(r.sender_name || r.sender_addr)}</span>
          <span>${(r.date || "").slice(0, 16)}</span>
        </div>
      `;
      div.addEventListener("click", () => {
        els.searchResults.classList.add("hidden");
        els.searchInput.value = "";
        if (r.thread_id) {
          openThread(r.thread_id);
        }
      });
      els.searchResults.appendChild(div);
    });
  }
  els.searchResults.classList.remove("hidden");
}

// ── Tree building ──
function buildTree(msgs) {
  const nodeMap = {};
  msgs.forEach(m => {
    nodeMap[m.message_id] = {
      ...m,
      children: [],
      depth: 0,
      x: 0,
      y: 0,
    };
  });

  const roots = [];
  msgs.forEach(m => {
    const node = nodeMap[m.message_id];
    const parentId = m.in_reply_to || "";
    if (parentId && nodeMap[parentId]) {
      nodeMap[parentId].children.push(node);
    } else {
      roots.push(node);
    }
  });

  return { roots, nodeMap };
}

function layoutTree(roots) {
  let leafCounter = 0;

  function assignY(node, depth) {
    node.depth = depth;
    node.x = depth * (NODE_W + GAP_X);

    if (node.children.length === 0) {
      node.y = leafCounter * (NODE_H + GAP_Y);
      leafCounter++;
    } else {
      for (let child of node.children) {
        assignY(child, depth + 1);
      }
      const first = node.children[0];
      const last = node.children[node.children.length - 1];
      node.y = (first.y + last.y) / 2;
    }
  }

  roots.sort((a, b) => (a.date || "").localeCompare(b.date || ""));
  for (let root of roots) {
    assignY(root, 0);
  }

  const all = [];
  function collect(node) {
    all.push(node);
    for (let child of node.children) {
      collect(child);
    }
  }
  for (let root of roots) {
    collect(root);
  }
  return all;
}

function drawLines(roots) {
  els.treeLines.innerHTML = "";

  function draw(from, to) {
    const x1 = from.x + NODE_W;
    const y1 = from.y + NODE_H / 2;
    const x2 = to.x;
    const y2 = to.y + NODE_H / 2;
    const mx = (x1 + x2) / 2;

    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    const d = `M ${x1} ${y1} C ${mx} ${y1}, ${mx} ${y2}, ${x2} ${y2}`;
    path.setAttribute("d", d);
    path.setAttribute("stroke", "#c4c8d4");
    path.setAttribute("stroke-width", "1.5");
    path.setAttribute("fill", "none");
    path.setAttribute("stroke-dasharray", from.children.length > 1 ? "5,3" : "none");
    els.treeLines.appendChild(path);

    const arrow = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    arrow.setAttribute("cx", x2);
    arrow.setAttribute("cy", y2);
    arrow.setAttribute("r", "3.5");
    arrow.setAttribute("fill", "#c4c8d4");
    els.treeLines.appendChild(arrow);
  }

  function traverse(node) {
    for (let child of node.children) {
      draw(node, child);
      traverse(child);
    }
  }
  for (let root of roots) {
    traverse(root);
  }

  if (allNodes.length > 0) {
    const maxX = Math.max(...allNodes.map(n => n.x)) + NODE_W + 40;
    const maxY = Math.max(...allNodes.map(n => n.y)) + NODE_H + 40;
    els.treeLines.setAttribute("width", maxX);
    els.treeLines.setAttribute("height", maxY);
    els.treeNodes.style.width = maxX + "px";
    els.treeNodes.style.height = maxY + "px";
  }
}

function renderTree(roots) {
  els.treeNodes.innerHTML = "";
  allNodes = layoutTree(roots);

  allNodes.forEach((n) => {
    const div = document.createElement("div");
    div.className = "tree-node-card" + (n.depth === 0 ? " root-node" : "");
    div.style.left = n.x + "px";
    div.style.top = n.y + "px";

    const initial = (n.sender_name || "?")[0];
    const subject = n.subject || "(无主题)";
    const date = (n.date || "").slice(0, 16);

    div.innerHTML = `
      <div class="node-avatar">${escHtml(initial)}</div>
      <div class="node-sender">${escHtml(n.sender_name || n.sender_addr)}</div>
      <div class="node-subject">${escHtml(subject)}</div>
      <div class="node-date">${escHtml(date)}</div>
      ${n.children.length > 0 ? `<div class="node-badge">${n.children.length}</div>` : ""}
    `;

    div.addEventListener("click", (e) => {
      e.stopPropagation();
      openDetail(n);
    });

    els.treeNodes.appendChild(div);
  });

  drawLines(roots);

  const wrap = document.getElementById("tree-canvas-wrap");
  if (wrap && roots.length > 0) {
    wrap.scrollLeft = 0;
    wrap.scrollTop = 0;
  }
}

// ── Open thread ──
async function openThread(threadId) {
  activeThread = threadId;
  renderThreadList();

  const msgs = await api(`/api/thread/${encodeURIComponent(threadId)}`);
  const thread = threads.find(t => t.thread_id === threadId);

  els.treeHeader.innerHTML = `
    <div class="subject">${escHtml(thread ? thread.subject : msgs[0]?.subject || "")}</div>
    <div class="overview">${msgs.length} 封邮件 · ${thread ? escHtml(thread.participants) : ""}</div>
  `;

  els.placeholder.style.display = "none";

  const { roots } = buildTree(msgs);
  treeRoots = roots;
  renderTree(roots);
}

// ── Detail panel ──
async function openDetail(node) {
  els.detailOverlay.classList.remove("hidden");
  els.detailPanel.classList.remove("hidden");
  els.detailSubject.textContent = node.subject || "(无主题)";

  const date = node.date || "";
  els.detailBody.innerHTML = `
    <div class="detail-field">
      <div class="detail-label">发件人</div>
      <div class="detail-value">${escHtml(node.sender_name || node.sender_addr)} &lt;${escHtml(node.sender_addr)}&gt;</div>
    </div>
    <div class="detail-field">
      <div class="detail-label">收件人</div>
      <div class="detail-value">${escHtml(node.recipients || "")}</div>
    </div>
    <div class="detail-field">
      <div class="detail-label">时间</div>
      <div class="detail-value">${escHtml(date)}</div>
    </div>
    <div class="detail-field">
      <div class="detail-label">邮件内容</div>
      <div class="detail-body-text" style="color:#999;font-style:italic">加载中…</div>
    </div>
  `;

  try {
    const full = await api(`/api/email/${node.id}`);
    const body = full.body_clean || full.body_plain || "(无内容)";
    const bodyEl = els.detailBody.querySelector(".detail-body-text");
    if (bodyEl) {
      bodyEl.style.cssText = "";
      bodyEl.textContent = body;
    }
  } catch (err) {
    const bodyEl = els.detailBody.querySelector(".detail-body-text");
    if (bodyEl) {
      bodyEl.style.cssText = "";
      bodyEl.textContent = "加载失败: " + err.message;
    }
  }
}

function closeDetail() {
  els.detailOverlay.classList.add("hidden");
  els.detailPanel.classList.add("hidden");
}

// ── Refresh (incremental: only fetch new emails since last check) ──
async function handleRefresh() {
  els.btnRefresh.disabled = true;
  els.btnRefresh.innerHTML = '<span class="spinner"></span>更新中…';
  try {
    const cfg = await api("/api/imap-config");
    let r;
    if (cfg.email && cfg.has_auth) {
      // Incremental fetch: only get new emails since last fetch
      r = await api("/api/imap-fetch", {
        method: "POST",
        body: JSON.stringify({
          incremental: true,
        }),
      });
    } else {
      r = await api("/api/check-new", { method: "POST" });
    }
    if (r.status === "cached") {
      toast(r.message, "warning");
    } else {
      toast(r.message, "success");
      await loadThreads();
      await loadStatus();
    }
  } catch (err) {
    toast("更新失败: " + err.message, "error");
  }
  els.btnRefresh.disabled = false;
  els.btnRefresh.textContent = "更新数据";
}

// ── Import sample ──
async function handleImportSample() {
  els.btnSample.disabled = true;
  els.btnSample.textContent = "导入中…";
  try {
    const r = await api("/api/import-sample", { method: "POST" });
    toast(`已导入 ${r.inserted} 封示例邮件`, "success");
    await loadStatus();
    await loadThreads();
  } catch (err) {
    toast("导入失败: " + err.message, "error");
  }
  els.btnSample.disabled = false;
  els.btnSample.textContent = "导入示例";
}

// ── IMAP Settings ──
async function openSettings() {
  els.modalOverlay.classList.remove("hidden");
  els.cfgStatus.textContent = "";
  try {
    const cfg = await api("/api/imap-config");
    els.cfgEmail.value = cfg.email || "";
    els.cfgServer.value = cfg.server || "";
    els.cfgPort.value = cfg.port || 993;
    els.cfgAuthCode.value = "";
    els.cfgAuthCode.placeholder = cfg.has_auth ? "已保存授权码（留空则沿用）" : "输入邮箱授权码";

    // Load existing email stats
    if (cfg.email && cfg.has_auth) {
      try {
        const info = await api("/api/existing-ids");
        const infoEl = document.getElementById("dl-db-info");
        if (infoEl) {
          infoEl.innerHTML = `数据库中已有 <b>${info.count}</b> 封邮件` +
            (info.earliest_date ? `（${info.earliest_date} ~ ${info.latest_date}）` : "") +
            ` · 数据库: <code>${(await api("/api/status")).db_name}</code>`;
          infoEl.style.display = "";
        }
      } catch (e) {
        // ignore
      }
    }
  } catch (err) {
    els.cfgStatus.textContent = "加载配置失败: " + err.message;
  }
}

function closeSettings() {
  els.modalOverlay.classList.add("hidden");
}

async function handleSaveConfig() {
  els.btnSaveConfig.disabled = true;
  els.btnSaveConfig.textContent = "保存中…";
  els.cfgStatus.textContent = "";
  try {
    const r = await api("/api/imap-config", {
      method: "POST",
      body: JSON.stringify({
        email: els.cfgEmail.value.trim(),
        auth_code: els.cfgAuthCode.value.trim(),
        server: els.cfgServer.value.trim(),
        port: parseInt(els.cfgPort.value) || 993,
      }),
    });
    els.cfgStatus.textContent = r.message;
    els.cfgStatus.style.color = "#27ae60";
    els.cfgAuthCode.value = "";
    els.cfgAuthCode.placeholder = "已保存授权码（留空则沿用）";
    toast(r.message, "success");

    // Refresh DB info after config change
    try {
      const info = await api("/api/existing-ids");
      const infoEl = document.getElementById("dl-db-info");
      if (infoEl) {
        infoEl.innerHTML = `数据库中已有 <b>${info.count}</b> 封邮件` +
          (info.earliest_date ? `（${info.earliest_date} ~ ${info.latest_date}）` : "");
        infoEl.style.display = "";
      }
    } catch (e) { /* ignore */ }
  } catch (err) {
    els.cfgStatus.textContent = "保存失败: " + err.message;
    els.cfgStatus.style.color = "#e74c3c";
  }
  els.btnSaveConfig.disabled = false;
  els.btnSaveConfig.textContent = "保存配置";
}

async function handleTestFetch() {
  els.btnTestFetch.disabled = true;
  els.btnTestFetch.innerHTML = '<span class="spinner"></span>测试连接中…';
  els.cfgStatus.textContent = "";
  try {
    // Save config first
    await api("/api/imap-config", {
      method: "POST",
      body: JSON.stringify({
        email: els.cfgEmail.value.trim(),
        auth_code: els.cfgAuthCode.value.trim(),
        server: els.cfgServer.value.trim(),
        port: parseInt(els.cfgPort.value) || 993,
      }),
    });
    els.cfgAuthCode.value = "";
    els.cfgAuthCode.placeholder = "已保存授权码（留空则沿用）";
    const r = await api("/api/imap-test", { method: "POST" });
    if (r.status === "ok") {
      let msg = r.message;
      if (r.preview && r.preview.length > 0) {
        msg += "\n邮件预览:\n" + r.preview.map(p =>
          `  [${p.date}] ${p.subject} — ${p.from}`
        ).join("\n");
      }
      els.cfgStatus.innerHTML = msg.replace(/\n/g, "<br>");
      els.cfgStatus.style.color = "#27ae60";
      toast(r.message, "success");
    }
  } catch (err) {
    els.cfgStatus.innerHTML = `<span style="color:#e74c3c">${escHtml(err.message).replace(/\n/g, "<br>")}</span>`;
    toast(err.message, "error");
  }
  els.btnTestFetch.disabled = false;
  els.btnTestFetch.textContent = "测试连接";
}

// ── Save & Fetch: check DB first, allow selective download ──
async function handleFetchSave() {
  els.btnFetchSave.disabled = true;
  els.btnFetchSave.innerHTML = '<span class="spinner"></span>处理中…';
  els.cfgStatus.textContent = "";
  els.cfgStatus.style.color = "";

  try {
    // Save config first
    await api("/api/imap-config", {
      method: "POST",
      body: JSON.stringify({
        email: els.cfgEmail.value.trim(),
        auth_code: els.cfgAuthCode.value.trim(),
        server: els.cfgServer.value.trim(),
        port: parseInt(els.cfgPort.value) || 993,
      }),
    });
    els.cfgAuthCode.value = "";
    els.cfgAuthCode.placeholder = "已保存授权码（留空则沿用）";

    // Check which download options are selected
    const selected = [];
    document.querySelectorAll(".dl-checkbox:checked").forEach(cb => {
      selected.push(cb.value);
    });

    if (selected.length === 0) {
      els.cfgStatus.innerHTML = '<span style="color:#e74c3c">请至少选择一个下载范围</span>';
      els.btnFetchSave.disabled = false;
      els.btnFetchSave.textContent = "保存并获取邮件到本地";
      return;
    }

    // Build date ranges from selected options
    const now = new Date();
    const y = now.getFullYear();
    const m = now.getMonth() + 1;

    const rangeMap = {
      "this-month": {
        from: `${y}-${String(m).padStart(2, "0")}-01`,
        to: `${y}-${String(m).padStart(2, "0")}-${new Date(y, m, 0).getDate()}`,
      },
      "3months": {
        from: (() => { let sm = m - 2, sy = y; if (sm <= 0) { sm += 12; sy--; } return `${sy}-${String(sm).padStart(2, "0")}-01`; })(),
        to: `${y}-${String(m).padStart(2, "0")}-${new Date(y, m, 0).getDate()}`,
      },
      "this-year": { from: `${y}-01-01`, to: `${y}-12-31` },
      "all": { from: "2020-01-01", to: "" },
    };

    let totalFetched = 0;
    let totalInserted = 0;
    let totalSkipped = 0;
    const messages = [];

    for (const sel of selected) {
      const range = rangeMap[sel];
      if (!range) continue;

      els.cfgStatus.innerHTML = `<span style="color:#666">正在下载: ${sel}（${range.from} ~ ${range.to || "至今"}）…</span>`;

      const r = await api("/api/imap-fetch", {
        method: "POST",
        body: JSON.stringify({
          date_from: range.from,
          date_to: range.to,
        }),
      });

      totalFetched += r.fetched || 0;
      totalInserted += r.new_count || 0;
      totalSkipped += r.skipped || 0;
      messages.push(`${sel}: 获取${r.fetched}封, 新增${r.new_count}封`);
    }

    const summaryParts = [];
    if (totalFetched > 0) summaryParts.push(`获取 ${totalFetched} 封`);
    if (totalSkipped > 0) summaryParts.push(`跳过 ${totalSkipped} 封已存在`);
    if (totalInserted > 0) summaryParts.push(`新增入库 ${totalInserted} 封`);
    if (summaryParts.length === 0) summaryParts.push("无新邮件");

    const summary = summaryParts.join("，");
    els.cfgStatus.innerHTML = `<span style="color:#27ae60">${escHtml(summary)}</span><br><span style="color:#999;font-size:11px">${messages.join("<br>")}</span>`;
    toast(summary, totalInserted > 0 ? "success" : "warning");

    if (totalInserted > 0) {
      await loadThreads();
      await loadStatus();
    }
  } catch (err) {
    els.cfgStatus.innerHTML = `<span style="color:#e74c3c">${escHtml(err.message).replace(/\n/g, "<br>")}</span>`;
    toast(err.message, "error");
  }
  els.btnFetchSave.disabled = false;
  els.btnFetchSave.textContent = "保存并获取邮件到本地";
}

// ── Utils ──
function escHtml(s) {
  const d = document.createElement("div");
  d.textContent = s || "";
  return d.innerHTML;
}

// ── Init ──
els.btnRefresh.addEventListener("click", handleRefresh);
els.btnSample.addEventListener("click", handleImportSample);
els.btnSettings.addEventListener("click", openSettings);
els.btnModalClose.addEventListener("click", closeSettings);
els.modalOverlay.addEventListener("click", (e) => {
  if (e.target === els.modalOverlay) closeSettings();
});
els.btnSaveConfig.addEventListener("click", handleSaveConfig);
els.btnTestFetch.addEventListener("click", handleTestFetch);
els.btnFetchSave.addEventListener("click", handleFetchSave);
els.btnDetailClose.addEventListener("click", closeDetail);
els.detailOverlay.addEventListener("click", closeDetail);
els.btnApplyFilter.addEventListener("click", applyCustomFilter);

// Date preset buttons
document.querySelectorAll(".btn-preset").forEach(btn => {
  btn.addEventListener("click", () => setDatePreset(btn.dataset.range));
});

// Toggle all download checkboxes
const dlToggleAll = document.getElementById("dl-toggle-all");
if (dlToggleAll) {
  dlToggleAll.addEventListener("change", function() {
    document.querySelectorAll(".dl-checkbox").forEach(cb => {
      cb.checked = this.checked;
    });
  });
}

loadStatus().then(() => loadThreads());
