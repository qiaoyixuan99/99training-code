// ── State ────────────────────────────────────────────────────────────
const state = {
  conversations: [],
  currentBaseSubject: null,
  currentConvData: null,
  selectedEmailId: null,
  dateFrom: '2026-05-01',
  dateTo: '2026-05-31',
};

// ── DOM refs ──────────────────────────────────────────────────────────
const $ = (s) => document.querySelector(s);
const $$ = (s) => document.querySelectorAll(s);

const dom = {
  sidebarStats: $('#sidebar-stats'),
  convList: $('#conv-list'),
  convHeader: $('#conv-header'),
  convBody: $('#conv-body'),
  placeholder: $('#placeholder'),
  mainLineLines: $('#main-line-lines'),
  mainLineNodes: $('#main-line-nodes'),
  sideBranchesList: $('#side-branches-list'),
  searchInput: $('#search-input'),
  searchResults: $('#search-results'),
  detailOverlay: $('#detail-overlay'),
  detailPanel: $('#detail-panel'),
  detailSubject: $('#detail-subject'),
  detailBody: $('#detail-body'),
  dateFrom: $('#date-from'),
  dateTo: $('#date-to'),
  modalOverlay: $('#modal-overlay'),
  toastContainer: $('#toast-container'),
};

// ── Toast ─────────────────────────────────────────────────────────────
function toast(msg, type) {
  type = type || '';
  const el = document.createElement('div');
  el.className = 'toast ' + type;
  el.textContent = msg;
  dom.toastContainer.appendChild(el);
  requestAnimationFrame(() => el.classList.add('show'));
  setTimeout(() => {
    el.classList.remove('show');
    setTimeout(() => el.remove(), 300);
  }, 3000);
}

// ── API helpers ───────────────────────────────────────────────────────
async function api(url, opts) {
  opts = opts || {};
  const res = await fetch(url, {
    method: opts.method || 'GET',
    headers: { 'Content-Type': 'application/json' },
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  return res.json();
}

// ── Load conversations ────────────────────────────────────────────────
async function loadConversations() {
  let params = [];
  if (state.dateFrom) params.push('date_from=' + encodeURIComponent(state.dateFrom));
  if (state.dateTo) params.push('date_to=' + encodeURIComponent(state.dateTo));
  const qs = params.length ? '?' + params.join('&') : '';
  const data = await api('/api/conversations' + qs);
  state.conversations = data;
  renderConvList();
}

function renderConvList() {
  const list = state.conversations;
  dom.convList.innerHTML = '';

  if (!list || list.length === 0) {
    dom.convList.innerHTML = '<div class="empty-hint">暂无会话数据</div>';
    return;
  }

  list.forEach(function(conv) {
    const div = document.createElement('div');
    div.className = 'conv-item';
    if (conv.base_subject === state.currentBaseSubject) {
      div.classList.add('active');
    }

    const total = conv.total_count;
    const date = conv.latest_date ? conv.latest_date.slice(0, 10) : '';

    div.innerHTML =
      '<div class="conv-subject">' + escHtml(conv.base_subject) + '</div>' +
      '<div class="conv-meta">' +
        '<span class="conv-count">' + total + ' 封</span>' +
        '<span class="conv-date">' + date + '</span>' +
      '</div>' +
      '<div class="conv-participants">' + escHtml(truncate(conv.participants, 40)) + '</div>';

    div.addEventListener('click', function() {
      selectConversation(conv.base_subject);
    });
    dom.convList.appendChild(div);
  });
}

function escHtml(s) {
  if (!s) return '';
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function truncate(s, n) {
  if (!s) return '';
  return s.length > n ? s.slice(0, n) + '…' : s;
}

// ── Select conversation ───────────────────────────────────────────────
async function selectConversation(baseSubject) {
  state.currentBaseSubject = baseSubject;
  state.selectedEmailId = null;

  // Highlight sidebar item
  $$('.conv-item').forEach(function(el) {
    el.classList.toggle('active', el.querySelector('.conv-subject').textContent === baseSubject);
  });

  // Fetch detail
  let url = '/api/conversation/detail?base_subject=' + encodeURIComponent(baseSubject);
  if (state.dateFrom) url += '&date_from=' + encodeURIComponent(state.dateFrom);
  if (state.dateTo) url += '&date_to=' + encodeURIComponent(state.dateTo);

  const data = await api(url);
  if (data.error) {
    toast(data.error, 'error');
    return;
  }

  state.currentConvData = data;
  dom.placeholder.classList.add('hidden');
  dom.convBody.classList.remove('hidden');
  renderConversation(data);
}

// ── Render conversation (main line + side branches) ───────────────────
function renderConversation(data) {
  // Header
  dom.convHeader.innerHTML =
    '<div class="conv-header-top">' +
      '<h2 class="conv-header-title">' + escHtml(data.base_subject) + '</h2>' +
      '<div class="conv-header-stats">' +
        '<span class="stat-item stat-main">主线路 <b>' + data.total_main + '</b> 封</span>' +
        '<span class="stat-item stat-side">分支/散落 <b>' + data.total_side + '</b> 封</span>' +
        '<span class="stat-item stat-total">合计 <b>' + data.total + '</b> 封</span>' +
      '</div>' +
    '</div>';

  // Collect all main line and side branch emails across components
  var allMainEmails = [];
  var allSideEmails = [];

  data.components.forEach(function(comp, ci) {
    // Tag each email with its component index and type
    comp.main_line.forEach(function(e) {
      e._compIndex = ci;
      e._type = 'main';
      allMainEmails.push(e);
    });
    comp.side_branches.forEach(function(e) {
      e._compIndex = ci;
      e._type = 'side';
      allSideEmails.push(e);
    });
  });

  // Render main line tree (all components' main lines)
  renderMainLineTree(allMainEmails, data.components);

  // Render side branches
  renderSideBranches(allSideEmails);
}

// ── Render main line tree ─────────────────────────────────────────────
function renderMainLineTree(emails, components) {
  var nodesWrap = dom.mainLineNodes;
  var linesSvg = dom.mainLineLines;
  nodesWrap.innerHTML = '';
  linesSvg.innerHTML = '';

  if (emails.length === 0) {
    nodesWrap.innerHTML = '<div class="empty-hint">无主线路邮件</div>';
    return;
  }

  // Build layout: separate disconnected components with a divider
  var allNodes = [];

  components.forEach(function(comp, ci) {
    var mainEmails = comp.main_line;
    if (mainEmails.length === 0) return;

    // Calculate positions
    var nodeW = 280;
    var gapX = 80;
    var gapY = 70;
    var startX = 60;
    var startY = 40;

    // Build parent-child relationships within main line
    var idSet = {};
    mainEmails.forEach(function(e) { idSet[e.message_id] = true; });

    // Sort main line by In-Reply-To chain
    var ordered = orderByReplyChain(mainEmails);

    var nodePositions = [];
    var links = [];

    // For each email, determine its depth in the chain
    var depthMap = {};
    var parentMap = {};  // child_id -> parent_id
    var childrenMap = {}; // parent_id -> [child_ids]

    ordered.forEach(function(em) {
      var parentId = em.in_reply_to || '';
      if (parentId && idSet[parentId]) {
        parentMap[em.message_id] = parentId;
        if (!childrenMap[parentId]) childrenMap[parentId] = [];
        childrenMap[parentId].push(em.message_id);
        depthMap[em.message_id] = (depthMap[parentId] || 0) + 1;
      } else {
        depthMap[em.message_id] = 0;
      }
    });

    // Group by depth
    var depthGroups = {};
    ordered.forEach(function(em) {
      var d = depthMap[em.message_id] || 0;
      if (!depthGroups[d]) depthGroups[d] = [];
      depthGroups[d].push(em);
    });

    // Assign x, y positions
    var positions = {};
    var maxDepth = Math.max.apply(null, Object.keys(depthGroups).map(Number).concat([0]));

    Object.keys(depthGroups).forEach(function(dStr) {
      var d = parseInt(dStr);
      var nodes = depthGroups[d];
      var x = startX + d * (nodeW + gapX);
      nodes.forEach(function(em, i) {
        var y = startY + i * gapY;
        positions[em.message_id] = { x: x, y: y, depth: d };
        nodePositions.push({ email: em, x: x, y: y });
      });
    });

    // Build links
    ordered.forEach(function(em) {
      var parentId = parentMap[em.message_id];
      if (parentId && positions[parentId]) {
        links.push({
          from: positions[parentId],
          to: positions[em.message_id],
        });
      }
    });

    // Collect all nodes with positions
    nodePositions.forEach(function(np) {
      np.email._depth = np.depth;
      np.email._x = np.x;
      np.email._y = np.y;
      allNodes.push(np);
    });

    // Render SVG lines for this component
    var svgNs = 'http://www.w3.org/2000/svg';
    var totalHeight = Math.max.apply(null, nodePositions.map(function(n) { return n.y + 60; }).concat([100]));

    links.forEach(function(link) {
      var x1 = link.from.x + nodeW;
      var y1 = link.from.y + 25;
      var x2 = link.to.x;
      var y2 = link.to.y + 25;
      var mx = (x1 + x2) / 2;

      var path = document.createElementNS(svgNs, 'path');
      var d = 'M' + x1 + ',' + y1 + ' C' + mx + ',' + y1 + ' ' + mx + ',' + y2 + ' ' + x2 + ',' + y2;
      path.setAttribute('d', d);
      path.setAttribute('class', 'main-line-path');
      linesSvg.appendChild(path);
    });

    // Update SVG size
    var currentHeight = parseInt(linesSvg.getAttribute('height') || '0');
    var neededHeight = Math.max(currentHeight, totalHeight);
    linesSvg.setAttribute('height', neededHeight);
    linesSvg.setAttribute('width', '100%');
  });

  // Render all nodes
  allNodes.sort(function(a, b) { return a.y - b.y || a.x - b.x; });

  allNodes.forEach(function(np) {
    var em = np.email;
    var node = document.createElement('div');
    node.className = 'tree-node main-line-node';
    node.style.left = np.x + 'px';
    node.style.top = np.y + 'px';
    node.setAttribute('data-email-id', em.id);
    node.setAttribute('data-message-id', em.message_id);

    if (em.id === state.selectedEmailId) {
      node.classList.add('selected');
    }

    var dateShort = em.date ? em.date.slice(0, 16).replace('T', ' ') : '';
    node.innerHTML =
      '<div class="node-badge main-badge">' + (np.depth === 0 ? '起' : '#' + np.depth) + '</div>' +
      '<div class="node-content">' +
        '<div class="node-sender">' + escHtml(em.sender_name || em.sender_addr) + '</div>' +
        '<div class="node-subject">' + escHtml(em.subject) + '</div>' +
        '<div class="node-date">' + dateShort + '</div>' +
      '</div>';

    node.addEventListener('click', function(e) {
      e.stopPropagation();
      state.selectedEmailId = em.id;
      $$('.tree-node').forEach(function(n) { n.classList.remove('selected'); });
      node.classList.add('selected');
      openDetail(em.id);
    });

    nodesWrap.appendChild(node);
  });

  // Adjust wrap height
  var maxY = allNodes.reduce(function(m, n) { return Math.max(m, n.y); }, 0);
  nodesWrap.style.height = (maxY + 100) + 'px';
  linesSvg.style.height = (maxY + 100) + 'px';
}

function orderByReplyChain(emails) {
  // Topological sort based on In-Reply-To
  var idSet = {};
  emails.forEach(function(e) { idSet[e.message_id] = true; });

  var children = {};  // parent -> [children]
  var inDegree = {};
  emails.forEach(function(e) {
    inDegree[e.message_id] = 0;
  });
  emails.forEach(function(e) {
    var parent = e.in_reply_to || '';
    if (parent && idSet[parent]) {
      if (!children[parent]) children[parent] = [];
      children[parent].push(e.message_id);
      inDegree[e.message_id] = (inDegree[e.message_id] || 0) + 1;
    }
  });

  // Find roots
  var roots = emails.filter(function(e) { return (inDegree[e.message_id] || 0) === 0; });
  roots.sort(function(a, b) { return (a.date || '').localeCompare(b.date || ''); });

  var result = [];
  var visited = {};
  function dfs(mid) {
    if (visited[mid]) return;
    visited[mid] = true;
    var em = emails.find(function(e) { return e.message_id === mid; });
    if (em) result.push(em);
    var kids = children[mid] || [];
    kids.sort();
    kids.forEach(dfs);
  }
  roots.forEach(function(r) { dfs(r.message_id); });
  // Catch any remaining
  emails.forEach(function(e) { if (!visited[e.message_id]) result.push(e); });
  return result;
}

// ── Render side branches ──────────────────────────────────────────────
function renderSideBranches(sideEmails) {
  var container = dom.sideBranchesList;
  container.innerHTML = '';

  if (sideEmails.length === 0) {
    container.innerHTML = '<div class="empty-hint side-empty">无散落邮件 — 所有邮件均在主线路中</div>';
    return;
  }

  // Group side emails by their In-Reply-To chains (mini-threads)
  var groups = groupSideEmails(sideEmails);

  groups.forEach(function(group, gi) {
    var card = document.createElement('div');
    card.className = 'side-card';

    var headerHtml = '';
    if (group.length === 1) {
      var em = group[0];
      var dateShort = em.date ? em.date.slice(0, 16).replace('T', ' ') : '';
      headerHtml =
        '<div class="side-card-header">' +
          '<span class="side-card-sender">' + escHtml(em.sender_name || em.sender_addr) + '</span>' +
          '<span class="side-card-date">' + dateShort + '</span>' +
          '<span class="side-card-subject">' + escHtml(em.subject) + '</span>' +
        '</div>';
    } else {
      var firstDate = group[0].date ? group[0].date.slice(0, 10) : '';
      headerHtml =
        '<div class="side-card-header">' +
          '<span class="side-card-label">分支对话 (' + group.length + ' 封)</span>' +
          '<span class="side-card-date">' + firstDate + '</span>' +
        '</div>';
    }

    var bodyHtml = '<div class="side-card-emails">';
    group.forEach(function(em) {
      var dateShort = em.date ? em.date.slice(0, 16).replace('T', ' ') : '';
      bodyHtml +=
        '<div class="side-email-row" data-email-id="' + em.id + '">' +
          '<span class="side-email-sender">' + escHtml(em.sender_name || em.sender_addr) + '</span>' +
          '<span class="side-email-subject">' + escHtml(em.subject) + '</span>' +
          '<span class="side-email-date">' + dateShort + '</span>' +
        '</div>';
    });
    bodyHtml += '</div>';

    card.innerHTML = headerHtml + bodyHtml;
    container.appendChild(card);

    // Click handlers for side emails
    card.querySelectorAll('.side-email-row').forEach(function(row) {
      row.addEventListener('click', function() {
        var emailId = parseInt(row.getAttribute('data-email-id'));
        state.selectedEmailId = emailId;
        $$('.side-email-row').forEach(function(r) { r.classList.remove('selected'); });
        $$('.tree-node').forEach(function(n) { n.classList.remove('selected'); });
        row.classList.add('selected');
        openDetail(emailId);
      });
    });
  });
}

function groupSideEmails(emails) {
  if (emails.length === 0) return [];

  var idSet = {};
  emails.forEach(function(e) { idSet[e.message_id] = true; });

  // Build adjacency
  var neighbors = {};
  emails.forEach(function(e) {
    neighbors[e.message_id] = [];
  });
  emails.forEach(function(e) {
    var parent = e.in_reply_to || '';
    if (parent && idSet[parent]) {
      neighbors[e.message_id].push(parent);
      neighbors[parent].push(e.message_id);
    }
  });

  var visited = {};
  var groups = [];

  emails.forEach(function(e) {
    if (visited[e.message_id]) return;
    var stack = [e.message_id];
    var group = [];
    while (stack.length) {
      var mid = stack.pop();
      if (visited[mid]) continue;
      visited[mid] = true;
      var em = emails.find(function(x) { return x.message_id === mid; });
      if (em) group.push(em);
      (neighbors[mid] || []).forEach(function(nb) {
        if (!visited[nb]) stack.push(nb);
      });
    }
    group.sort(function(a, b) { return (a.date || '').localeCompare(b.date || ''); });
    groups.push(group);
  });

  // Sort groups by earliest date
  groups.sort(function(a, b) {
    return (a[0].date || '').localeCompare(b[0].date || '');
  });

  return groups;
}

// ── Detail panel ──────────────────────────────────────────────────────
async function openDetail(emailId) {
  const data = await api('/api/email/' + emailId);
  if (data.error) {
    toast(data.error, 'error');
    return;
  }

  dom.detailSubject.textContent = data.subject || '(no subject)';
  dom.detailBody.innerHTML =
    '<div class="detail-field">' +
      '<label>发件人</label><span>' + escHtml(data.sender_name) + ' &lt;' + escHtml(data.sender_addr) + '&gt;</span>' +
    '</div>' +
    '<div class="detail-field">' +
      '<label>收件人</label><span>' + escHtml(data.recipients) + '</span>' +
    '</div>' +
    '<div class="detail-field">' +
      '<label>时间</label><span>' + escHtml(data.date) + '</span>' +
    '</div>' +
    '<div class="detail-field">' +
      '<label>真实标题</label><span class="base-subject-tag">' + escHtml(data.base_subject) + '</span>' +
    '</div>' +
    '<div class="detail-field">' +
      '<label>原始标题</label><span class="raw-subject-text">' + escHtml(data.subject) + '</span>' +
    '</div>' +
    '<div class="detail-body-text">' +
      '<label>邮件正文</label>' +
      '<pre>' + escHtml(data.body_clean || data.body_plain || '(无内容)') + '</pre>' +
    '</div>';

  dom.detailOverlay.classList.remove('hidden');
  dom.detailPanel.classList.remove('hidden');
}

function closeDetail() {
  dom.detailOverlay.classList.add('hidden');
  dom.detailPanel.classList.add('hidden');
}

dom.detailOverlay.addEventListener('click', closeDetail);
$('#btn-detail-close').addEventListener('click', closeDetail);

// ── Search ────────────────────────────────────────────────────────────
let searchTimer = null;
dom.searchInput.addEventListener('input', function() {
  clearTimeout(searchTimer);
  var q = dom.searchInput.value.trim();
  if (!q) {
    dom.searchResults.classList.add('hidden');
    return;
  }
  searchTimer = setTimeout(async function() {
    const results = await api('/api/search?q=' + encodeURIComponent(q));
    renderSearchResults(results);
  }, 300);
});

function renderSearchResults(results) {
  var el = dom.searchResults;
  el.innerHTML = '';
  if (!results || results.length === 0) {
    el.innerHTML = '<div class="search-empty">无匹配结果</div>';
    el.classList.remove('hidden');
    return;
  }
  results.forEach(function(r) {
    var div = document.createElement('div');
    div.className = 'search-item';
    div.innerHTML =
      '<div class="search-subject">' + escHtml(r.subject) + '</div>' +
      '<div class="search-meta">' + escHtml(r.sender_name) + ' · ' + (r.date ? r.date.slice(0, 10) : '') + '</div>';
    div.addEventListener('click', function() {
      dom.searchResults.classList.add('hidden');
      dom.searchInput.value = '';
      // If the result has a base_subject, navigate to that conversation
      if (r.base_subject) {
        selectConversation(r.base_subject).then(function() {
          state.selectedEmailId = r.id;
          $$('.tree-node').forEach(function(n) { n.classList.remove('selected'); });
          var node = document.querySelector('.tree-node[data-email-id="' + r.id + '"]');
          if (node) node.classList.add('selected');
          setTimeout(function() { openDetail(r.id); }, 100);
        });
      } else {
        openDetail(r.id);
      }
    });
    el.appendChild(div);
  });
  el.classList.remove('hidden');
}

document.addEventListener('click', function(e) {
  if (!dom.searchResults.contains(e.target) && e.target !== dom.searchInput) {
    dom.searchResults.classList.add('hidden');
  }
});

// ── Date filter ───────────────────────────────────────────────────────
$$('.btn-preset').forEach(function(btn) {
  btn.addEventListener('click', function() {
    $$('.btn-preset').forEach(function(b) { b.classList.remove('active'); });
    btn.classList.add('active');
    var range = btn.getAttribute('data-range');
    var now = new Date();
    var from = '', to = '';

    switch (range) {
      case 'may2026':
        from = '2026-05-01'; to = '2026-05-31'; break;
      case 'this-month':
        var y = now.getFullYear(), m = String(now.getMonth() + 1).padStart(2, '0');
        from = y + '-' + m + '-01';
        to = y + '-' + m + '-' + String(new Date(y, now.getMonth() + 1, 0).getDate()).padStart(2, '0');
        break;
      case '3months':
        var d = new Date(now.getTime() - 90 * 86400000);
        from = d.toISOString().slice(0, 10);
        to = now.toISOString().slice(0, 10);
        break;
      case 'this-year':
        from = String(now.getFullYear()) + '-01-01';
        to = now.toISOString().slice(0, 10);
        break;
      case 'all':
        from = ''; to = ''; break;
    }
    state.dateFrom = from;
    state.dateTo = to;
    dom.dateFrom.value = from;
    dom.dateTo.value = to;
    refreshAll();
  });
});

$('#btn-apply-filter').addEventListener('click', function() {
  state.dateFrom = dom.dateFrom.value;
  state.dateTo = dom.dateTo.value;
  $$('.btn-preset').forEach(function(b) { b.classList.remove('active'); });
  refreshAll();
});

async function refreshAll() {
  await loadConversations();
  if (state.currentBaseSubject) {
    // Only reload if the current conversation still exists in the new filter range
    var found = state.conversations.some(function(c) { return c.base_subject === state.currentBaseSubject; });
    if (found) {
      await selectConversation(state.currentBaseSubject);
    } else {
      // Clear selection when the conversation is outside the new filter range
      state.currentBaseSubject = null;
      state.currentConvData = null;
      dom.placeholder.classList.remove('hidden');
      dom.convBody.classList.add('hidden');
    }
  }
}

// ── Buttons ───────────────────────────────────────────────────────────
$('#btn-refresh').addEventListener('click', async function() {
  var btn = $('#btn-refresh');
  btn.disabled = true;
  btn.textContent = '检查中…';
  try {
    var res = await api('/api/check-new', { method: 'POST' });
    toast(res.message, res.status === 'updated' ? 'success' : '');
    await refreshAll();
  } catch (err) {
    toast('操作失败: ' + err.message, 'error');
  }
  btn.disabled = false;
  btn.textContent = '更新数据';
});

$('#btn-import-sample').addEventListener('click', async function() {
  var btn = $('#btn-import-sample');
  btn.disabled = true;
  btn.textContent = '导入中…';
  try {
    var res = await api('/api/import-sample', { method: 'POST' });
    toast('已导入 ' + res.inserted + ' 封示例邮件（含前缀变体）', 'success');
    await refreshAll();
  } catch (err) {
    toast('导入失败: ' + err.message, 'error');
  }
  btn.disabled = false;
  btn.textContent = '导入V3示例';
});

// ── IMAP Settings modal ───────────────────────────────────────────────
$('#btn-settings').addEventListener('click', async function() {
  const cfg = await api('/api/imap-config');
  $('#cfg-email').value = cfg.email || '';
  $('#cfg-server').value = cfg.server || '';
  $('#cfg-port').value = cfg.port || 993;
  dom.modalOverlay.classList.remove('hidden');
});

$('#btn-modal-close').addEventListener('click', function() {
  dom.modalOverlay.classList.add('hidden');
});
dom.modalOverlay.addEventListener('click', function(e) {
  if (e.target === dom.modalOverlay) dom.modalOverlay.classList.add('hidden');
});

$('#btn-save-config').addEventListener('click', async function() {
  var body = {
    email: $('#cfg-email').value.trim(),
    auth_code: $('#cfg-auth-code').value.trim(),
    server: $('#cfg-server').value.trim(),
    port: parseInt($('#cfg-port').value) || 993,
  };
  var res = await api('/api/imap-config', { method: 'POST', body: body });
  $('#cfg-status').textContent = res.message || res.status;
  if (res.status === 'ok') toast('配置已保存', 'success');
});

$('#btn-test-fetch').addEventListener('click', async function() {
  // Save config first
  var body = {
    email: $('#cfg-email').value.trim(),
    auth_code: $('#cfg-auth-code').value.trim(),
    server: $('#cfg-server').value.trim(),
    port: parseInt($('#cfg-port').value) || 993,
  };
  await api('/api/imap-config', { method: 'POST', body: body });

  $('#cfg-status').textContent = '正在测试连接…';
  var res = await api('/api/imap-test', { method: 'POST' });
  if (res.status === 'ok') {
    var html = '<div style="color:green">' + res.message + '</div>';
    if (res.preview && res.preview.length) {
      html += '<div style="margin-top:8px">';
      res.preview.forEach(function(p) {
        html += '<div style="font-size:11px;margin:2px 0">' +
          '<b>' + escHtml(p.from) + '</b>: ' + escHtml(p.subject) + ' (' + (p.date || '') + ')</div>';
      });
      html += '</div>';
    }
    $('#cfg-status').innerHTML = html;
  } else {
    $('#cfg-status').innerHTML = '<div style="color:red">' + escHtml(res.message) + '</div>';
  }
});

$('#btn-fetch-save').addEventListener('click', async function() {
  var body = {
    email: $('#cfg-email').value.trim(),
    auth_code: $('#cfg-auth-code').value.trim(),
    server: $('#cfg-server').value.trim(),
    port: parseInt($('#cfg-port').value) || 993,
  };
  await api('/api/imap-config', { method: 'POST', body: body });

  $('#cfg-status').textContent = '正在从服务器获取邮件…';
  var reqBody = { force: true };
  if (state.dateFrom) reqBody.date_from = state.dateFrom;
  if (state.dateTo) reqBody.date_to = state.dateTo;
  var res = await api('/api/imap-fetch', { method: 'POST', body: reqBody });
  if (res.status === 'updated') {
    $('#cfg-status').textContent = res.message;
    toast(res.message, 'success');
    dom.modalOverlay.classList.add('hidden');
    await refreshAll();
  } else if (res.status === 'cached') {
    $('#cfg-status').textContent = res.message;
    toast(res.message);
  } else {
    $('#cfg-status').innerHTML = '<div style="color:red">' + escHtml(res.message || res.status) + '</div>';
  }
});

// ── Init ──────────────────────────────────────────────────────────────
async function init() {
  const status = await api('/api/status');
  dom.sidebarStats.innerHTML =
    '<span>共 <b>' + status.total_emails + '</b> 封邮件</span>' +
    '<span><b>' + status.total_conversations + '</b> 个会话</span>' +
    (status.checked_today ? '<span class="badge-ok">今日已更新</span>' : '');

  if (status.default_date_from) {
    state.dateFrom = status.default_date_from;
    dom.dateFrom.value = status.default_date_from;
  }
  if (status.default_date_to) {
    state.dateTo = status.default_date_to;
    dom.dateTo.value = status.default_date_to;
  }

  await loadConversations();
}

init();
