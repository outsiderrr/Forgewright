// T-3.6a Review UI MVP — vanilla JS, no framework (ADR-025).
// State is one global object; views re-render on demand. Mermaid is
// loaded via the F17 fallback chain: vendor bundle > CDN > plain text.

const state = {
  scenes: [],
  filteredScenes: [],
  selectedSceneId: null,
  currentDetail: null,
  graphFormat: 'mermaid',
  mermaidStatus: 'pending', // 'vendor' | 'cdn' | 'failed' | 'pending'
  filters: {
    unreviewed: true,
    accepted: true,
    rejected: true,
    failed: true,
  },
};

const els = {};

// ---------------------------------------------------------------------------
// Mermaid loader (F17 fallback chain)
// ---------------------------------------------------------------------------

function setGraphSourceBadge(label, kind) {
  const badge = els.graphSourceBadge;
  badge.textContent = `graph: ${label}`;
  badge.className = 'badge ' + ({
    vendor: 'badge-pass',
    cdn: 'badge-info',
    fallback: 'badge-warn',
    failed: 'badge-fail',
    pending: 'badge-muted',
  }[kind] || 'badge-muted');
}

function loadScript(src) {
  return new Promise((resolve, reject) => {
    const s = document.createElement('script');
    s.src = src;
    s.onload = () => resolve(src);
    s.onerror = () => reject(new Error(`failed to load ${src}`));
    document.head.appendChild(s);
  });
}

async function ensureMermaid() {
  if (window.mermaid) return state.mermaidStatus;
  try {
    await loadScript('/static/vendor/mermaid.min.js');
    if (window.mermaid) {
      window.mermaid.initialize({ startOnLoad: false, theme: 'default', securityLevel: 'strict' });
      state.mermaidStatus = 'vendor';
      return 'vendor';
    }
  } catch (e) {
    console.warn('[mermaid] vendor bundle missing; trying CDN', e);
  }
  try {
    await loadScript('https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js');
    if (window.mermaid) {
      window.mermaid.initialize({ startOnLoad: false, theme: 'default', securityLevel: 'strict' });
      state.mermaidStatus = 'cdn';
      return 'cdn';
    }
  } catch (e) {
    console.warn('[mermaid] CDN unavailable; falling back to text views', e);
  }
  state.mermaidStatus = 'failed';
  return 'failed';
}

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------

async function api(path, opts) {
  const res = await fetch(path, opts);
  if (!res.ok) {
    let msg = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (body && body.detail) msg += ` — ${body.detail}`;
    } catch (_) { /* ignore */ }
    throw new Error(msg);
  }
  const ct = res.headers.get('content-type') || '';
  if (ct.includes('application/json')) return res.json();
  return res.text();
}

// ---------------------------------------------------------------------------
// Scene list (view 1)
// ---------------------------------------------------------------------------

function statusLabel(scene) {
  if (scene.success === false) return { text: '失败', cls: 'badge-fail' };
  if (scene.review_status === 'accepted') return { text: '[A]', cls: 'badge-pass' };
  if (scene.review_status === 'rejected') return { text: '[R]', cls: 'badge-fail' };
  if (scene.source === 'content') return { text: 'content', cls: 'badge-info' };
  return { text: '未审', cls: 'badge-muted' };
}

function passSummary(scene) {
  const items = [];
  if (scene.success === false) items.push({ text: 'fail', cls: 'badge-fail' });
  for (const k of ['mechanical_pass', 'topology_pass', 'sampling_pass']) {
    const v = scene[k];
    if (v === true) items.push({ text: k.replace('_pass', '').slice(0, 3), cls: 'badge-pass' });
    else if (v === false) items.push({ text: k.replace('_pass', '').slice(0, 3), cls: 'badge-fail' });
  }
  if (scene.advisory) {
    items.push({ text: `J:${scene.advisory[0].toUpperCase()}`, cls: 'badge-info' });
  }
  return items;
}

function applyFilters() {
  state.filteredScenes = state.scenes.filter((s) => {
    if (s.success === false && !state.filters.failed) return false;
    if (s.review_status === 'accepted' && !state.filters.accepted) return false;
    if (s.review_status === 'rejected' && !state.filters.rejected) return false;
    if (s.review_status === 'unreviewed' && s.success !== false && !state.filters.unreviewed) return false;
    return true;
  });
}

function renderSceneList() {
  applyFilters();
  els.sceneList.innerHTML = '';
  if (state.filteredScenes.length === 0) {
    const li = document.createElement('li');
    li.className = 'placeholder';
    li.textContent = '（无场景；请检查 batch_dir 或 filter）';
    els.sceneList.appendChild(li);
    return;
  }
  for (const scene of state.filteredScenes) {
    const li = document.createElement('li');
    li.className = 'scene-row';
    if (scene.scene_id === state.selectedSceneId) li.classList.add('active');
    if (scene.success === false) li.classList.add('failed');
    if (scene.review_status === 'accepted') li.classList.add('accepted');
    if (scene.review_status === 'rejected') li.classList.add('rejected');
    li.dataset.sceneId = scene.scene_id;

    const id = document.createElement('span');
    id.className = 'row-id';
    id.textContent = scene.scene_id;
    li.appendChild(id);

    const meta = document.createElement('span');
    meta.className = 'row-meta';
    const status = statusLabel(scene);
    const statusBadge = document.createElement('span');
    statusBadge.className = 'badge ' + status.cls;
    statusBadge.textContent = status.text;
    meta.appendChild(statusBadge);
    for (const item of passSummary(scene)) {
      const b = document.createElement('span');
      b.className = 'badge ' + item.cls;
      b.textContent = item.text;
      meta.appendChild(b);
    }
    li.appendChild(meta);

    li.addEventListener('click', () => selectScene(scene.scene_id));
    els.sceneList.appendChild(li);
  }
}

// ---------------------------------------------------------------------------
// Scene detail load
// ---------------------------------------------------------------------------

async function selectScene(sceneId) {
  state.selectedSceneId = sceneId;
  renderSceneList();
  setReviewFlash('', null);
  els.rejectReason.value = '';
  els.sceneTitle.textContent = sceneId;
  try {
    const detail = await api(`/api/scene/${encodeURIComponent(sceneId)}`);
    state.currentDetail = detail;
    renderSceneDetail();
    if (detail.graph_views_available && detail.graph_views_available.length > 0) {
      const preferred = detail.graph_views_available.includes(state.graphFormat)
        ? state.graphFormat
        : detail.graph_views_available[0];
      setGraphFormat(preferred, { fromDetail: true });
    } else {
      renderGraphPlaceholder('（该场景未生成 graph views — content/ 来源场景仅 batch_dir 可渲染）');
    }
  } catch (err) {
    state.currentDetail = null;
    els.sceneMeta.textContent = '';
    els.sceneTitle.textContent = sceneId;
    renderGraphPlaceholder(`加载失败：${err.message}`);
  }
}

function renderSceneDetail() {
  const d = state.currentDetail;
  if (!d) return;
  els.sceneTitle.textContent = `${d.scene_id} ${d.iter_id != null ? `· iter ${d.iter_id}` : ''}`;
  const metaParts = [];
  metaParts.push(`<span class="badge badge-info">${d.source}</span>`);
  if (d.fixture_id) metaParts.push(`<span>fixture: <strong>${escapeHtml(d.fixture_id)}</strong></span>`);
  if (typeof d.cost_usd === 'number') metaParts.push(`<span>cost: $${d.cost_usd.toFixed(4)}</span>`);
  if (d.inner_attempt_count != null) metaParts.push(`<span>attempts: ${d.inner_attempt_count}</span>`);
  if (d.failure_reason) metaParts.push(`<span class="badge badge-fail">${escapeHtml(d.failure_reason)}</span>`);
  els.sceneMeta.innerHTML = metaParts.join(' · ');

  // setting
  const setting = (d.fixture && d.fixture.scene_setting) ? d.fixture : null;
  els.sceneSetting.textContent = setting
    ? JSON.stringify(setting, null, 2)
    : (d.source === 'content' ? '（content 来源场景无 fixture）' : '—');

  // nodes
  els.sceneNodes.innerHTML = '';
  const nodes = (d.graph && d.graph.nodes) || {};
  const ids = Object.keys(nodes);
  if (ids.length === 0) {
    els.sceneNodes.textContent = '（无节点）';
  } else {
    for (const nid of ids) {
      const n = nodes[nid];
      const card = document.createElement('div');
      card.className = 'node-item';
      const head = document.createElement('div');
      head.className = 'node-id';
      head.textContent = `${nid} · type=${n.type} · speaker=${n.speaker_ref || '(narrator)'}`;
      card.appendChild(head);
      if (n.narration) {
        const p = document.createElement('div');
        p.className = 'node-narration';
        p.textContent = n.narration;
        card.appendChild(p);
      }
      if (n.options && n.options.length) {
        const ul = document.createElement('div');
        ul.className = 'node-options';
        for (const opt of n.options) {
          const line = document.createElement('div');
          const cond = opt.condition ? '[cond] ' : '';
          line.textContent = `• ${cond}${opt.text || ''} → ${opt.target_node_id}`;
          ul.appendChild(line);
        }
        card.appendChild(ul);
      }
      els.sceneNodes.appendChild(card);
    }
  }

  // deps
  els.sceneDeps.textContent = d.deps
    ? JSON.stringify(d.deps, null, 2)
    : '（无 deps.json sidecar）';

  // validators (view 3)
  renderValidators(d.validator_summaries, d.graph);

  // advisory
  renderAdvisory(d.advisory, d.advisory_rationale);

  // review (view 4)
  renderReviewSection(d);
}

function renderValidators(summaries, graph) {
  const fmt = (obj) => obj == null ? '—' : JSON.stringify(obj, null, 2);
  if (!summaries) {
    els.validatorSchema.textContent = graph ? `schema_pass=true (success row; envelope embedded the graph successfully)` : '—';
    els.validatorTopology.textContent = '—';
    els.validatorSampling.textContent = '—';
    els.validatorMechanical.textContent = '—';
    return;
  }
  els.validatorSchema.textContent = `schema_pass: ${graph ? 'true' : 'unknown'}\n(scene_results envelope shape; sub-schema details are in /schema/dialogue_graph.schema.json)`;
  els.validatorTopology.textContent = fmt(summaries.topology);
  els.validatorSampling.textContent = fmt(summaries.sampling);
  els.validatorMechanical.textContent = fmt(summaries.mechanical);
}

function renderAdvisory(advisory, rationale) {
  if (!advisory) {
    els.advisoryContent.textContent = '（无 AI judge 报告或本场景未评分）';
    return;
  }
  const pillCls = advisory === 'accept' ? 'advisory-accept'
                : advisory === 'reject' ? 'advisory-reject'
                : 'advisory-marginal';
  let html = `<div><span class="advisory-pill ${pillCls}">${escapeHtml(advisory)}</span></div>`;
  if (rationale) {
    if (rationale.lenient) html += `<p style="margin:6px 0 4px"><strong>lenient:</strong> ${escapeHtml(rationale.lenient)}</p>`;
    if (rationale.strict) html += `<p style="margin:4px 0"><strong>strict:</strong> ${escapeHtml(rationale.strict)}</p>`;
  }
  els.advisoryContent.innerHTML = html;
}

function renderReviewSection(detail) {
  const review = detail.review;
  if (review) {
    const verdict = review.accepted ? '[A] accepted' : '[R] rejected';
    const reason = review.reason ? ` · reason: ${review.reason}` : '';
    els.reviewStatus.textContent = `已审：${verdict} @ ${review.reviewed_at}${reason}（提交新决策会追加新行）`;
  } else {
    els.reviewStatus.textContent = '未审。';
  }
  const isContent = detail.source === 'content';
  els.btnAccept.disabled = isContent;
  els.btnReject.disabled = isContent;
  els.btnSkip.disabled = false;
  if (isContent) {
    els.reviewStatus.textContent = 'content 来源场景不可在此 UI 提交审阅（请改 batch_dir 来源场景）。';
  }
}

// ---------------------------------------------------------------------------
// Graph view (view 2) — mermaid + fallback
// ---------------------------------------------------------------------------

function setGraphFormat(fmt, opts) {
  state.graphFormat = fmt;
  for (const btn of els.formatButtons) {
    btn.classList.toggle('active', btn.dataset.format === fmt);
  }
  loadAndRenderGraph();
}

function renderGraphPlaceholder(text) {
  els.graphContainer.innerHTML = `<p class="placeholder">${escapeHtml(text)}</p>`;
}

async function loadAndRenderGraph() {
  if (!state.selectedSceneId) {
    renderGraphPlaceholder('未加载场景。');
    return;
  }
  const fmt = state.graphFormat;
  let text;
  try {
    text = await api(`/api/graph/${encodeURIComponent(state.selectedSceneId)}?format=${fmt}`);
  } catch (err) {
    renderGraphPlaceholder(`graph (${fmt}) 不可用：${err.message}`);
    setGraphSourceBadge(`${fmt} unavailable`, 'failed');
    return;
  }
  if (fmt === 'mermaid') {
    const status = await ensureMermaid();
    if (status === 'failed') {
      const fallback = (state.currentDetail.graph_views_available || []).includes('dot') ? 'dot' : 'ascii';
      renderGraphPlaceholder(`mermaid 渲染不可用，自动切换到 ${fallback}`);
      setGraphSourceBadge(`${fallback} fallback`, 'fallback');
      setTimeout(() => setGraphFormat(fallback), 0);
      return;
    }
    try {
      const id = `mermaid-svg-${Date.now()}`;
      const result = await window.mermaid.render(id, text);
      els.graphContainer.innerHTML = result.svg;
      setGraphSourceBadge(`mermaid (${status})`, status);
    } catch (err) {
      console.error('[mermaid] render failed', err);
      const fallback = (state.currentDetail.graph_views_available || []).includes('dot') ? 'dot' : 'ascii';
      renderGraphPlaceholder(`mermaid render 报错；切换到 ${fallback}`);
      setGraphSourceBadge(`${fallback} fallback`, 'fallback');
      setTimeout(() => setGraphFormat(fallback), 0);
    }
  } else {
    const pre = document.createElement('pre');
    pre.textContent = text;
    els.graphContainer.innerHTML = '';
    els.graphContainer.appendChild(pre);
    setGraphSourceBadge(`${fmt} (text)`, 'fallback');
  }
}

// ---------------------------------------------------------------------------
// Review actions (view 4)
// ---------------------------------------------------------------------------

async function submitReview(decision) {
  const detail = state.currentDetail;
  if (!detail) return;
  if (decision === 'skip') {
    nextScene();
    return;
  }
  const reason = els.rejectReason.value.trim();
  if (decision === 'reject' && !reason) {
    setReviewFlash('Reject 必须填 reason。', 'error');
    els.rejectReason.focus();
    return;
  }
  try {
    const body = {
      scene_id: detail.scene_id,
      iter_id: detail.iter_id,
      decision,
      reason: decision === 'reject' ? reason : null,
    };
    const res = await api('/api/review', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    setReviewFlash(`已写入 scene_review_log.jsonl（${res.record.reviewed_at}）`, 'success');
    // Refresh the left nav so the row's status reflects the new decision.
    // The flash is short-lived: keep it visible for ~700ms so the author
    // sees the confirmation before we auto-jump to the next unreviewed scene.
    await refreshScenes();
    setTimeout(nextScene, 700);
  } catch (err) {
    setReviewFlash(`提交失败：${err.message}`, 'error');
  }
}

function nextScene() {
  const i = state.filteredScenes.findIndex((s) => s.scene_id === state.selectedSceneId);
  if (i < 0) return;
  for (let j = i + 1; j < state.filteredScenes.length; j++) {
    if (state.filteredScenes[j].review_status === 'unreviewed' && state.filteredScenes[j].success !== false) {
      selectScene(state.filteredScenes[j].scene_id);
      return;
    }
  }
  setReviewFlash('已到列表末尾，没有更多未审场景。', null);
}

function setReviewFlash(text, kind) {
  els.reviewFlash.textContent = text;
  els.reviewFlash.className = 'flash' + (kind ? ' ' + kind : '');
}

// ---------------------------------------------------------------------------
// Tab switching
// ---------------------------------------------------------------------------

function bindTabBar(navEl) {
  const panels = navEl.parentElement.querySelectorAll('.tab-panel');
  navEl.addEventListener('click', (e) => {
    const btn = e.target.closest('.tab');
    if (!btn) return;
    const target = btn.dataset.tab;
    for (const t of navEl.querySelectorAll('.tab')) t.classList.toggle('active', t === btn);
    for (const p of panels) p.classList.toggle('active', p.dataset.panel === target);
  });
}

// ---------------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------------

async function refreshScenes() {
  const data = await api('/api/scenes');
  state.scenes = data.scenes || [];
  els.batchDir.textContent = `batch: ${data.batch_dir || '—'}`;
  els.scenesDir.textContent = `scenes: ${data.scenes_dir || '—'}`;
  renderSceneList();
}

function escapeHtml(s) {
  return String(s == null ? '' : s)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function bindFilters() {
  const map = {
    'filter-unreviewed': 'unreviewed',
    'filter-accepted': 'accepted',
    'filter-rejected': 'rejected',
    'filter-failed': 'failed',
  };
  for (const [id, key] of Object.entries(map)) {
    const el = document.getElementById(id);
    el.addEventListener('change', () => {
      state.filters[key] = el.checked;
      renderSceneList();
    });
  }
}

function bindFormatButtons() {
  for (const btn of els.formatButtons) {
    btn.addEventListener('click', () => setGraphFormat(btn.dataset.format));
  }
}

function bindReviewButtons() {
  els.btnAccept.addEventListener('click', () => submitReview('accept'));
  els.btnReject.addEventListener('click', () => submitReview('reject'));
  els.btnSkip.addEventListener('click', () => submitReview('skip'));
}

function cacheElements() {
  els.batchDir = document.getElementById('batch-dir');
  els.scenesDir = document.getElementById('scenes-dir');
  els.graphSourceBadge = document.getElementById('graph-source-badge');
  els.sceneList = document.getElementById('scene-list');
  els.sceneTitle = document.getElementById('scene-title');
  els.sceneMeta = document.getElementById('scene-meta');
  els.sceneSetting = document.getElementById('scene-setting');
  els.sceneNodes = document.getElementById('scene-nodes');
  els.sceneDeps = document.getElementById('scene-deps');
  els.graphContainer = document.getElementById('graph-container');
  els.formatButtons = document.querySelectorAll('.format-btn');
  els.validatorSchema = document.getElementById('validator-schema');
  els.validatorTopology = document.getElementById('validator-topology');
  els.validatorSampling = document.getElementById('validator-sampling');
  els.validatorMechanical = document.getElementById('validator-mechanical');
  els.advisoryContent = document.getElementById('advisory-content');
  els.reviewStatus = document.getElementById('review-status');
  els.btnAccept = document.getElementById('btn-accept');
  els.btnReject = document.getElementById('btn-reject');
  els.btnSkip = document.getElementById('btn-skip');
  els.rejectReason = document.getElementById('reject-reason');
  els.reviewFlash = document.getElementById('review-flash');
}

async function boot() {
  cacheElements();
  bindTabBar(document.getElementById('main-tabs'));
  bindTabBar(document.getElementById('validator-tabs'));
  bindFilters();
  bindFormatButtons();
  bindReviewButtons();
  setGraphSourceBadge('—', 'pending');
  try {
    await refreshScenes();
  } catch (err) {
    els.sceneList.innerHTML = `<li class="placeholder">scene 列表加载失败：${escapeHtml(err.message)}</li>`;
  }
}

document.addEventListener('DOMContentLoaded', boot);
