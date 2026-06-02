// ── State ──
let threads      = [];
let activeThread = null;

// ── DOM refs ──
const els = {
  stats:        document.getElementById("sidebar-stats"),
  threadList:   document.getElementById("thread-list"),
  threadDetail: document.getElementById("thread-detail"),
  btnRefresh:   document.getElementById("btn-refresh"),
  btnSample:    document.getElementById("btn-import-sample"),
  btnSettings:  document.getElementById("btn-settings"),
  modalOverlay: document.getElementById("modal-overlay"),
  btnModalClose:document.getElementById("btn-modal-close"),
  btnSaveConfig:document.getElementById("btn-save-config"),
  btnTestFetch: document.getElementById("btn-test-fetch"),
  btnFetchSave: document.getElementById("btn-fetch-save"),
  cfgEmail:     document.getElementById("cfg-email"),
  cfgAuthCode:  document.getElementById("cfg-auth-code"),
  cfgServer:    document.getElementById("cfg-server"),
  cfgPort:      document.getElementById("cfg-port"),
  cfgStatus:    document.getElementById("cfg-status"),
};

// ── Toast ──
function toast(msg, type = "info") {
  const c = document.getElementById("toast-container");
  const el = document.createElement("div");
  el.className = "toast " + type;
  el.textContent = msg;
  c.appendChild(el);
  setTimeout(() => { el.remove(); }, 3500);
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

// ── Load sidebar ──
async function loadStatus() {
  const s = await api("/api/status");
  els.stats.innerHTML =
    `共 <b>${s.total_threads}</b> 个线程 · <b>${s.total_emails}</b> 封邮件` +
    (s.checked_today ? ` · <span style="color:#27ae60">今日已更新</span>` : "");
}

async function loadThreads() {
  threads = await api("/api/threads");
  renderThreadList();
}

function renderThreadList() {
  els.threadList.innerHTML = "";
  if (threads.length === 0) {
    els.threadList.innerHTML =
      '<div style="padding:24px;text-align:center;color:#999;">暂无邮件线程<br>点击"导入示例"开始体验，或配置IMAP获取真实邮件</div>';
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

// ── Open thread detail ──
async function openThread(threadId) {
  activeThread = threadId;
  renderThreadList();

  const msgs = await api(`/api/thread/${encodeURIComponent(threadId)}`);
  const thread = threads.find(t => t.thread_id === threadId);

  els.threadDetail.innerHTML = `
    <div class="thread-header">
      <div class="subject">${escHtml(thread ? thread.subject : msgs[0]?.subject || "")}</div>
      <div class="overview">${msgs.length} 封邮件 · ${thread ? escHtml(thread.participants) : ""}</div>
    </div>
    <div class="conversation">
      ${renderConversation(msgs)}
    </div>
  `;
}

function renderConversation(msgs) {
  let lastDate = "";
  return msgs.map((m, i) => {
    const d = (m.date || "").slice(0, 10);
    let sep = "";
    if (d && d !== lastDate) {
      sep = `<div class="msg-date-separator">── ${d} ──</div>`;
      lastDate = d;
    }
    // Alternate left/right for visual variety
    const cls = i % 2 === 0 ? "" : "self";
    const initial = (m.sender_name || m.sender_addr || "?")[0];
    return sep + `
      <div class="msg-card ${cls}">
        <div class="msg-avatar">${escHtml(initial)}</div>
        <div class="msg-body-wrap">
          <div class="msg-sender">${escHtml(m.sender_name || m.sender_addr)}</div>
          <div class="msg-text">${escHtml(m.body_clean || m.body_plain || "(无内容)")}</div>
          <div class="msg-time">${m.date || ""}</div>
        </div>
      </div>
    `;
  }).join("");
}

// ── Refresh / Check new ──
async function handleRefresh() {
  els.btnRefresh.disabled = true;
  els.btnRefresh.innerHTML = '<span class="spinner"></span>检查中…';
  try {
    // Try IMAP fetch first if configured
    const cfg = await api("/api/imap-config");
    let r;
    if (cfg.email && cfg.has_auth) {
      r = await api("/api/imap-fetch", { method: "POST" });
    } else {
      // Fallback: scan local maildir
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
    toast("检查失败: " + err.message, "error");
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

// ── IMAP Settings Modal ──
async function openSettings() {
  els.modalOverlay.classList.remove("hidden");
  els.cfgStatus.textContent = "";
  try {
    const cfg = await api("/api/imap-config");
    els.cfgEmail.value = cfg.email || "";
    els.cfgServer.value = cfg.server || "";
    els.cfgPort.value = cfg.port || 993;
    els.cfgAuthCode.value = "";
    if (cfg.has_auth) {
      els.cfgAuthCode.placeholder = "已保存授权码（留空则沿用）";
    } else {
      els.cfgAuthCode.placeholder = "输入邮箱授权码";
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
        email:     els.cfgEmail.value.trim(),
        auth_code: els.cfgAuthCode.value.trim(),
        server:    els.cfgServer.value.trim(),
        port:      parseInt(els.cfgPort.value) || 993,
      }),
    });
    els.cfgStatus.textContent = r.message;
    els.cfgStatus.style.color = "#27ae60";
    els.cfgAuthCode.value = "";
    els.cfgAuthCode.placeholder = "已保存授权码（留空则沿用）";
    toast(r.message, "success");
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
        email:     els.cfgEmail.value.trim(),
        auth_code: els.cfgAuthCode.value.trim(),
        server:    els.cfgServer.value.trim(),
        port:      parseInt(els.cfgPort.value) || 993,
      }),
    });
    els.cfgAuthCode.value = "";
    els.cfgAuthCode.placeholder = "已保存授权码（留空则沿用）";

    // Test connection (does NOT save emails, just checks)
    const r = await api("/api/imap-test", { method: "POST" });
    if (r.status === "ok") {
      let msg = r.message;
      if (r.preview && r.preview.length > 0) {
        msg += "\n邮件预览:\n" + r.preview.map(p =>
          `  [${p.date}] ${p.subject} — ${p.from}`
        ).join("\n");
      }
      els.cfgStatus.textContent = msg.replace(/\n/g, "<br>");
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

async function handleFetchSave() {
  els.btnFetchSave.disabled = true;
  els.btnFetchSave.innerHTML = '<span class="spinner"></span>获取并保存中…';
  els.cfgStatus.textContent = "";

  try {
    // Save config first
    await api("/api/imap-config", {
      method: "POST",
      body: JSON.stringify({
        email:     els.cfgEmail.value.trim(),
        auth_code: els.cfgAuthCode.value.trim(),
        server:    els.cfgServer.value.trim(),
        port:      parseInt(els.cfgPort.value) || 993,
      }),
    });
    els.cfgAuthCode.value = "";
    els.cfgAuthCode.placeholder = "已保存授权码（留空则沿用）";

    // Fetch and save with force=true to bypass daily limit
    const r = await api("/api/imap-fetch", {
      method: "POST",
      body: JSON.stringify({ force: true }),
    });
    if (r.status === "cached") {
      els.cfgStatus.textContent = r.message;
      els.cfgStatus.style.color = "#f39c12";
      toast(r.message, "warning");
    } else {
      els.cfgStatus.textContent = r.message;
      els.cfgStatus.style.color = "#27ae60";
      toast(r.message, "success");
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

loadStatus();
loadThreads();
