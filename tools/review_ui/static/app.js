// T-3.6a Review UI MVP + T-3.6b integrations — vanilla JS, no framework (ADR-025).
// State is one global object; views re-render on demand. Mermaid is
// loaded via the F17 fallback chain: vendor bundle > CDN > plain text.
//
// T-3.6b additions are additive: navMode, chapters, staleReport, scene
// visuals + playtest payloads. MVP behaviors (selectScene → graph/setting/
// nodes/deps + validators + advisory + A/R/S) stay byte-equivalent.

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
    skipped: true,
    failed: true,
  },
  // T-3.6b
  navMode: 'list', // 'list' | 'chapter'
  chapters: [],
  // PR #48 review §4.3: placements come from /api/chapters scene_placements,
  // which prefers sidecar chapter_id/act_id over ontology anchor lookup.
  scenePlacements: {}, // scene_id → { chapter_id, act_id, scene_anchor, source }
  placementSummary: null, // { total, placed, from_sidecar, from_ontology_anchor, unplaced }
  staleReport: null, // last /api/stale payload, or null
  staleSceneIds: new Set(), // scene_ids flagged stale by current report
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
    // Pin to the same version as the vendor bundle (review C-5.1) so the
    // CDN fallback can't drift to a different rendering between A and B
    // phase screenshots.  Refresh both sites in lockstep — see vendor/README.
    await loadScript('https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js');
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
  if (scene.review_status === 'skipped') return { text: '[S]', cls: 'badge-warn' };
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
    if (s.review_status === 'skipped' && !state.filters.skipped) return false;
    if (s.review_status === 'unreviewed' && s.success !== false && !state.filters.unreviewed) return false;
    return true;
  });
}

function buildSceneRow(scene) {
  const li = document.createElement('li');
  li.className = 'scene-row';
  if (scene.scene_id === state.selectedSceneId) li.classList.add('active');
  if (scene.success === false) li.classList.add('failed');
  if (scene.review_status === 'accepted') li.classList.add('accepted');
  if (scene.review_status === 'rejected') li.classList.add('rejected');
  if (scene.review_status === 'skipped') li.classList.add('skipped');
  if (state.staleSceneIds.has(scene.scene_id)) li.classList.add('stale');
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
  if (state.staleSceneIds.has(scene.scene_id)) {
    const sb = document.createElement('span');
    sb.className = 'badge badge-warn';
    sb.textContent = 'stale';
    sb.title = 'flagged by /api/stale';
    meta.appendChild(sb);
  }
  li.appendChild(meta);

  li.addEventListener('click', () => selectScene(scene.scene_id));
  return li;
}

function renderSceneList() {
  applyFilters();
  if (state.navMode === 'chapter') {
    els.sceneList.hidden = true;
    els.sceneTree.hidden = false;
    renderChapterTree();
    return;
  }
  els.sceneList.hidden = false;
  els.sceneTree.hidden = true;
  els.sceneList.innerHTML = '';
  if (state.filteredScenes.length === 0) {
    const li = document.createElement('li');
    li.className = 'placeholder';
    li.textContent = '（无场景；请检查 batch_dir 或 filter）';
    els.sceneList.appendChild(li);
    return;
  }
  for (const scene of state.filteredScenes) {
    els.sceneList.appendChild(buildSceneRow(scene));
  }
}

// T-3.6b RUI-INT-4: chapter / act grouping --------------------------------

function renderChapterTree() {
  els.sceneTree.innerHTML = '';
  if (!state.chapters || state.chapters.length === 0) {
    const p = document.createElement('p');
    p.className = 'placeholder';
    p.textContent = '（ontology 未声明 chapters[]；切回 列表 视图）';
    els.sceneTree.appendChild(p);
    return;
  }
  // PR #48 review §4.3: only render chapter tree if at least one scene
  // has a placed chapter_id+act_id (from sidecar or ontology lookup).
  // Otherwise the tree would be a sea of "未归入" pseudo-state, which
  // the reviewer flagged as misleading.  Fall back to the flat list
  // with an explanatory notice instead.
  const summary = state.placementSummary || { placed: 0 };
  if (summary.placed === 0) {
    const p = document.createElement('p');
    p.className = 'placeholder';
    p.textContent =
      '（场景的 dep_index sidecar 缺 chapter_id / act_id，且 scene_anchor 未在 ontology 的 included_scenes 中；' +
      '已退回 列表 视图。请等 T-3.5 batch_scheduler 写入 sidecar 后再切到本视图。）';
    els.sceneTree.appendChild(p);
    return;
  }
  // Bucket each visible scene by chapter_id/act_id from scene_placements.
  const buckets = new Map(); // chapter_id → Map(act_id → [scene])
  const placedSceneIds = new Set();
  for (const scene of state.filteredScenes) {
    const placement = state.scenePlacements[scene.scene_id];
    if (!placement || !placement.chapter_id || !placement.act_id) continue;
    if (!buckets.has(placement.chapter_id)) buckets.set(placement.chapter_id, new Map());
    const acts = buckets.get(placement.chapter_id);
    if (!acts.has(placement.act_id)) acts.set(placement.act_id, []);
    acts.get(placement.act_id).push(scene);
    placedSceneIds.add(scene.scene_id);
  }
  for (const chap of state.chapters) {
    const det = document.createElement('details');
    det.className = 'chapter-group';
    det.open = true;
    const sumEl = document.createElement('summary');
    sumEl.textContent = `${chap.chapter_id || '(no id)'} · ${chap.display_name || ''}`;
    det.appendChild(sumEl);
    const acts = buckets.get(chap.chapter_id) || new Map();
    for (const act of chap.acts || []) {
      const actDet = document.createElement('details');
      actDet.className = 'act-group';
      actDet.open = true;
      const actSum = document.createElement('summary');
      actSum.textContent = `${act.act_id || '(no id)'} · ${act.display_name || ''}`;
      actDet.appendChild(actSum);
      const ul = document.createElement('ul');
      ul.className = 'act-scene-list';
      const scenes = acts.get(act.act_id) || [];
      if (scenes.length === 0) {
        const empty = document.createElement('li');
        empty.className = 'placeholder';
        empty.textContent = '（本 act 暂无可见场景）';
        ul.appendChild(empty);
      } else {
        for (const scene of scenes) ul.appendChild(buildSceneRow(scene));
      }
      actDet.appendChild(ul);
      det.appendChild(actDet);
    }
    els.sceneTree.appendChild(det);
  }
  // Unplaced scenes — sidecar lacks chapter_id/act_id AND ontology
  // anchor lookup didn't resolve.  Surface them in a separate group so
  // the operator can see what's missing rather than silently hiding.
  const unplaced = state.filteredScenes.filter((s) => !placedSceneIds.has(s.scene_id));
  if (unplaced.length > 0) {
    const det = document.createElement('details');
    det.className = 'chapter-group chapter-orphan';
    det.open = true;
    const sumEl = document.createElement('summary');
    sumEl.textContent = `（未归属 — sidecar 缺 chapter_id/act_id · ${unplaced.length}）`;
    det.appendChild(sumEl);
    const ul = document.createElement('ul');
    ul.className = 'act-scene-list';
    for (const scene of unplaced) ul.appendChild(buildSceneRow(scene));
    det.appendChild(ul);
    els.sceneTree.appendChild(det);
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
  // Reset T-3.6b panels eagerly so a slow request doesn't show stale data.
  renderVisuals(null);
  renderPlaytest(null);
  applyStaleBannerForScene(sceneId);
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
  // T-3.6b: fire integration fetches in parallel (best-effort; UI degrades).
  fetchAndRenderVisuals(sceneId);
  fetchAndRenderPlaytest(sceneId);
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

  // T-3.6b: chapter / act header link (RUI-INT-4 §10)
  renderChapterLinkForScene(d);
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
    let verdict;
    if (review.accepted === true) verdict = '[A] accepted';
    else if (review.accepted === false) verdict = '[R] rejected';
    else verdict = '[S] skipped';
    const reason = review.reason ? ` · reason: ${review.reason}` : '';
    els.reviewStatus.textContent = `已审：${verdict} @ ${review.reviewed_at}${reason}（提交新决策会追加新行）`;
  } else {
    els.reviewStatus.textContent = '未审。';
  }
  // Acceptance-truth-source guard (review C-3.1): only batch envelopes that
  // succeeded + passed mechanical pre-check carry an A/R/S decision.  The
  // server is authoritative; the UI mirrors `detail.reviewable` so the
  // button is disabled for failed/content rows even before the POST round-trips.
  const reviewable = detail.reviewable === true;
  els.btnAccept.disabled = !reviewable;
  els.btnReject.disabled = !reviewable;
  els.btnSkip.disabled = !reviewable;
  if (!reviewable && detail.not_reviewable_reason) {
    els.notReviewableNote.style.display = '';
    els.notReviewableNote.textContent = `不可审：${detail.not_reviewable_reason}`;
  } else {
    els.notReviewableNote.style.display = 'none';
    els.notReviewableNote.textContent = '';
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
  if (detail.reviewable !== true) {
    setReviewFlash(`不可审：${detail.not_reviewable_reason || '场景不在 batch_dir 或未通过 mechanical 预检'}`, 'error');
    return;
  }
  const reason = els.rejectReason.value.trim();
  if ((decision === 'reject' || decision === 'skip') && !reason) {
    setReviewFlash(`${decision === 'reject' ? 'Reject' : 'Skip'} 必须填 reason。`, 'error');
    els.rejectReason.focus();
    return;
  }
  try {
    const body = {
      scene_id: detail.scene_id,
      iter_id: detail.iter_id,
      decision,
      reason: decision === 'accept' ? null : reason,
    };
    const res = await api('/api/review', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const verdict = decision === 'accept' ? '[A]' : decision === 'reject' ? '[R]' : '[S]';
    setReviewFlash(`已写入 ${verdict} → scene_review_log.jsonl（${res.record.reviewed_at}）`, 'success');
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
// T-3.6b RUI-INT-1: visual asset thumbnails
// ---------------------------------------------------------------------------

async function fetchAndRenderVisuals(sceneId) {
  try {
    const payload = await api(`/api/scene/${encodeURIComponent(sceneId)}/visuals`);
    if (state.selectedSceneId !== sceneId) return; // user moved on
    renderVisuals(payload);
  } catch (err) {
    if (state.selectedSceneId !== sceneId) return;
    renderVisuals({ error: err.message });
  }
}

function renderVisuals(payload) {
  const root = els.visualsContent;
  root.innerHTML = '';
  if (payload === null) {
    root.textContent = '加载中…';
    return;
  }
  if (payload && payload.error) {
    root.textContent = `加载失败：${payload.error}`;
    return;
  }
  if (!payload.manifest_loaded) {
    const p = document.createElement('p');
    p.className = 'placeholder';
    p.textContent = `（manifest.json 未找到 · ${payload.manifest_path || 'unknown'}）`;
    root.appendChild(p);
    return;
  }
  if ((payload.characters || []).length === 0 && (payload.locations || []).length === 0) {
    const p = document.createElement('p');
    p.className = 'placeholder';
    p.textContent = '（本场景无对应视觉资产；character_refs / scene_anchor 在 manifest.json 中无匹配）';
    root.appendChild(p);
    return;
  }
  if ((payload.characters || []).length > 0) {
    const h = document.createElement('div');
    h.className = 'visuals-group-header';
    h.textContent = `出场角色 (${payload.characters.length})`;
    root.appendChild(h);
    const grid = document.createElement('div');
    grid.className = 'visuals-grid';
    for (const a of payload.characters) grid.appendChild(buildVisualCard(a));
    root.appendChild(grid);
  }
  if ((payload.locations || []).length > 0) {
    const h = document.createElement('div');
    h.className = 'visuals-group-header';
    h.textContent = `场景背景 (${payload.locations.length})`;
    root.appendChild(h);
    const grid = document.createElement('div');
    grid.className = 'visuals-grid';
    for (const a of payload.locations) grid.appendChild(buildVisualCard(a));
    root.appendChild(grid);
  }
}

function buildVisualCard(asset) {
  const card = document.createElement('div');
  card.className = 'visual-card';
  card.title = `${asset.asset_id} · ${asset.asset_role || asset.asset_kind || ''}`;
  const img = document.createElement('img');
  img.alt = asset.asset_id || 'visual asset';
  img.loading = 'lazy';
  img.src = asset.file_url;
  img.addEventListener('error', () => {
    card.classList.add('visual-card-broken');
    img.replaceWith(document.createTextNode('×'));
  });
  card.appendChild(img);
  const cap = document.createElement('div');
  cap.className = 'visual-card-caption';
  const ref = asset.character_ref || asset.location_ref || asset.target_ref || '';
  cap.textContent = `${ref}\n${asset.asset_role || asset.asset_kind || ''}`;
  card.appendChild(cap);
  card.addEventListener('click', () => openVisualModal(asset));
  return card;
}

function openVisualModal(asset) {
  els.visualModalImg.src = asset.file_url;
  els.visualModalImg.alt = asset.asset_id || '';
  const ref = asset.character_ref || asset.location_ref || asset.target_ref || '';
  els.visualModalCaption.textContent = `${asset.asset_id}  ·  ${ref}  ·  ${asset.asset_role || asset.asset_kind || ''}  ·  ${asset.format || ''} ${asset.width || ''}×${asset.height || ''}`;
  els.visualModal.hidden = false;
}

function closeVisualModal() {
  els.visualModal.hidden = true;
  els.visualModalImg.src = '';
}

// ---------------------------------------------------------------------------
// T-3.6b RUI-INT-2: playtest panel (F13 degrade — never hides the panel)
// ---------------------------------------------------------------------------

async function fetchAndRenderPlaytest(sceneId) {
  try {
    const payload = await api(`/api/playtest/${encodeURIComponent(sceneId)}`);
    if (state.selectedSceneId !== sceneId) return;
    renderPlaytest(payload);
  } catch (err) {
    if (state.selectedSceneId !== sceneId) return;
    renderPlaytest({ error: err.message });
  }
}

function renderPlaytest(payload) {
  const root = els.playtestPanel;
  root.innerHTML = '';
  if (payload === null) {
    root.textContent = '加载中…';
    return;
  }
  if (payload && payload.error) {
    root.textContent = `加载失败：${payload.error}`;
    return;
  }
  if (!payload.playtest_run) {
    // F13 degrade: keep the panel rendered with a hint, do NOT hide it.
    const card = document.createElement('div');
    card.className = 'playtest-empty';
    const hint = document.createElement('p');
    hint.className = 'playtest-hint';
    hint.innerHTML =
      '该场景未跑 playtest——可运行：<br>' +
      '<code>python -m generator.playtest &lt;scene_path&gt;</code><br>' +
      '产物（worst_paths.jsonl + worst_scenes.json + run_manifest.json）入 batch_dir 的 playtest_NNN/ 子目录后刷新本页。';
    card.appendChild(hint);
    const detail = document.createElement('p');
    detail.className = 'advisory-note';
    detail.textContent = `degrade reason: ${payload.reason || 'unknown'}`;
    card.appendChild(detail);
    if (payload.all_runs_scanned != null) {
      const meta = document.createElement('p');
      meta.className = 'advisory-note';
      meta.textContent = `已扫描 ${payload.all_runs_scanned} 个 playtest_*/ 目录`;
      card.appendChild(meta);
    }
    root.appendChild(card);
    return;
  }

  // Header
  const header = document.createElement('div');
  header.className = 'playtest-header';
  header.innerHTML =
    `<strong>${escapeHtml(payload.playtest_run)}</strong> · ` +
    `playtest_id=<code>${escapeHtml(payload.playtest_id || '?')}</code> · ` +
    `model=<code>${escapeHtml(payload.model_id || '?')}</code> · ` +
    `rubric=<code>${escapeHtml(payload.rubric_version || '?')}</code>`;
  root.appendChild(header);

  // Scene-level summary
  const summary = payload.scene_summary;
  if (summary) {
    const sect = document.createElement('div');
    sect.className = 'playtest-summary';
    const h = document.createElement('div');
    h.className = 'playtest-section-h';
    h.textContent = `Scene aggregate (${summary.scene_id})`;
    sect.appendChild(h);
    const score = (summary.scene_quality_score == null) ? '—' : summary.scene_quality_score.toFixed(2);
    const stats = document.createElement('div');
    stats.className = 'playtest-stats';
    stats.innerHTML =
      `<span>quality=<code>${escapeHtml(String(score))}</code></span>` +
      `<span>n_paths=<code>${summary.n_paths || 0}</code></span>` +
      `<span>mean=<code>${summary.mean_path_score != null ? summary.mean_path_score.toFixed(2) : '—'}</code></span>` +
      `<span>min=<code>${summary.min_path_score != null ? summary.min_path_score.toFixed(2) : '—'}</code></span>` +
      `<span class="badge badge-fail">crit ${summary.critical_count || 0}</span>` +
      `<span class="badge badge-warn">major ${summary.major_count || 0}</span>` +
      `<span class="badge badge-muted">minor ${summary.minor_count || 0}</span>`;
    sect.appendChild(stats);
    if (summary.critical_findings && summary.critical_findings.length > 0) {
      const cf = document.createElement('details');
      cf.className = 'playtest-criticals';
      cf.open = true;
      const cfSum = document.createElement('summary');
      cfSum.textContent = `Critical findings (${summary.critical_findings.length})`;
      cf.appendChild(cfSum);
      const ul = document.createElement('ul');
      for (const f of summary.critical_findings) {
        const li = document.createElement('li');
        const dim = f.dimension ? `[${f.dimension}] ` : '';
        const txt = f.text || f.note || JSON.stringify(f);
        li.textContent = `${dim}${txt}`;
        ul.appendChild(li);
      }
      cf.appendChild(ul);
      sect.appendChild(cf);
    }
    root.appendChild(sect);
  }

  // Worst paths
  const paths = payload.worst_paths || [];
  const sect2 = document.createElement('div');
  sect2.className = 'playtest-paths';
  const h2 = document.createElement('div');
  h2.className = 'playtest-section-h';
  h2.textContent = `Worst paths for this scene (${paths.length})`;
  sect2.appendChild(h2);
  if (paths.length === 0) {
    const empty = document.createElement('p');
    empty.className = 'placeholder';
    empty.textContent = '（worst_paths.jsonl 中无本场景的路径）';
    sect2.appendChild(empty);
  } else {
    for (const p of paths) sect2.appendChild(buildPlaytestPathRow(p));
  }
  root.appendChild(sect2);
}

function buildPlaytestPathRow(p) {
  const wrap = document.createElement('details');
  wrap.className = 'playtest-path-row';
  const sum = document.createElement('summary');
  const score = p.judge_score == null ? '—' : p.judge_score.toFixed(2);
  sum.innerHTML =
    `<span class="path-id">${escapeHtml(p.path_id || '')}</span> ` +
    `<code>${escapeHtml(p.persona_id || '')}</code> ` +
    `<span class="badge badge-info">score ${escapeHtml(String(score))}</span> ` +
    `<span class="badge badge-fail">crit ${p.critical_count || 0}</span> ` +
    `<span class="badge badge-warn">major ${p.major_count || 0}</span>` +
    (p.failure_reason ? ` <span class="badge badge-fail">${escapeHtml(p.failure_reason)}</span>` : '') +
    (p.reached_end ? ` <span class="badge badge-pass">end</span>` : '');
  wrap.appendChild(sum);
  if (p.judge_rationale) {
    const r = document.createElement('p');
    r.className = 'path-rationale';
    r.textContent = `rationale: ${p.judge_rationale}`;
    wrap.appendChild(r);
  }
  if (p.severity_findings && p.severity_findings.length > 0) {
    const ul = document.createElement('ul');
    ul.className = 'path-findings';
    for (const f of p.severity_findings) {
      const li = document.createElement('li');
      const sev = f.severity || '?';
      const dim = f.dimension ? `[${f.dimension}] ` : '';
      const txt = f.text || f.note || JSON.stringify(f);
      li.innerHTML = `<span class="badge badge-${sev === 'critical' ? 'fail' : (sev === 'major' ? 'warn' : 'muted')}">${escapeHtml(sev)}</span> ${escapeHtml(dim + txt)}`;
      ul.appendChild(li);
    }
    wrap.appendChild(ul);
  }
  const meta = document.createElement('p');
  meta.className = 'advisory-note';
  meta.textContent =
    `step_count=${p.step_count || 0}` +
    (p.end_node_id ? ` · end_node=${p.end_node_id}` : '');
  wrap.appendChild(meta);
  return wrap;
}

// ---------------------------------------------------------------------------
// T-3.6b RUI-INT-3: stale list (lazy fetch + nav badge + scene banner)
// ---------------------------------------------------------------------------

function buildStaleParams() {
  const params = new URLSearchParams();
  const since = els.staleSince.value.trim();
  if (since) params.set('since', since);
  const ids = els.staleOntology.value.trim();
  if (ids) params.set('changed_ontology_ids', ids);
  const paths = els.staleStatePaths.value.trim();
  if (paths) params.set('changed_state_paths', paths);
  const visuals = els.staleVisuals.value.trim();
  if (visuals) params.set('changed_visual_assets', visuals);
  const clocks = els.staleClocks.value.trim();
  if (clocks) params.set('changed_clocks', clocks);
  return params.toString();
}

async function refreshStale() {
  const qs = buildStaleParams();
  els.staleError.hidden = true;
  els.staleError.textContent = '';
  els.staleList.textContent = '加载中…';
  try {
    const payload = await api(`/api/stale${qs ? `?${qs}` : ''}`);
    state.staleReport = payload;
    state.staleSceneIds = new Set((payload.stale_scenes || []).map((s) => s.scene_id));
    if (payload.diff_error) {
      els.staleError.hidden = false;
      els.staleError.textContent = `--since 解析失败：${payload.diff_error}`;
    }
    renderStaleList(payload);
    renderSceneList();
    applyStaleBannerForScene(state.selectedSceneId);
    updateStaleToggleBadge();
  } catch (err) {
    els.staleError.hidden = false;
    els.staleError.textContent = `请求失败：${err.message}`;
    els.staleList.textContent = '—';
  }
}

function renderStaleList(payload) {
  els.staleList.innerHTML = '';
  const scenes = (payload && payload.stale_scenes) || [];
  if (scenes.length === 0) {
    els.staleList.textContent = '（无 stale 场景 — 输入参数皆为空时也是空集合）';
    return;
  }
  const inputsLine = document.createElement('p');
  inputsLine.className = 'advisory-note';
  const inputs = (payload && payload.inputs) || {};
  inputsLine.textContent =
    `inputs: since=${inputs.since_commit || '—'} · ` +
    `ontology=${(inputs.changed_ontology_ids || []).length} · ` +
    `state=${(inputs.changed_state_paths || []).length} · ` +
    `visual=${(inputs.changed_visual_assets || []).length} · ` +
    `clock=${(inputs.changed_clocks || []).length}`;
  els.staleList.appendChild(inputsLine);
  for (const s of scenes) {
    const item = document.createElement('div');
    item.className = `stale-item priority-${s.priority || 'context_only'}`;
    const head = document.createElement('div');
    head.className = 'stale-item-head';
    head.innerHTML =
      `<span class="badge badge-${s.priority === 'core' ? 'fail' : (s.priority === 'minor' ? 'warn' : 'muted')}">${escapeHtml(s.priority || '')}</span> ` +
      `<a href="#" class="stale-item-link">${escapeHtml(s.scene_id)}</a>`;
    head.querySelector('a').addEventListener('click', (e) => {
      e.preventDefault();
      selectScene(s.scene_id);
    });
    item.appendChild(head);
    const reasonsUl = document.createElement('ul');
    reasonsUl.className = 'stale-reasons';
    for (const r of s.reasons || []) {
      const li = document.createElement('li');
      li.textContent = `${r.kind} → ${r.value}`;
      reasonsUl.appendChild(li);
    }
    item.appendChild(reasonsUl);
    els.staleList.appendChild(item);
  }
}

function updateStaleToggleBadge() {
  const n = state.staleSceneIds.size;
  els.staleToggle.textContent = `⚠ Stale (${n})`;
  els.staleToggle.classList.toggle('has-stale', n > 0);
}

function applyStaleBannerForScene(sceneId) {
  if (!sceneId || !state.staleReport) {
    els.staleBanner.hidden = true;
    return;
  }
  const match = (state.staleReport.stale_scenes || []).find((s) => s.scene_id === sceneId);
  if (!match) {
    els.staleBanner.hidden = true;
    return;
  }
  const reasons = (match.reasons || []).map((r) => `${r.kind}=${r.value}`).join(' · ');
  els.staleBanner.hidden = false;
  els.staleBanner.innerHTML =
    `<strong>⚠ 该场景被 /api/stale 标记 stale</strong> ` +
    `<span class="badge badge-${match.priority === 'core' ? 'fail' : (match.priority === 'minor' ? 'warn' : 'muted')}">${escapeHtml(match.priority || '')}</span> ` +
    `<span class="banner-reasons">${escapeHtml(reasons)}</span>`;
}

// ---------------------------------------------------------------------------
// T-3.6b RUI-INT-4: chapter / act link in scene header
// ---------------------------------------------------------------------------

async function loadChapters() {
  try {
    const payload = await api('/api/chapters');
    state.chapters = payload.chapters || [];
    state.scenePlacements = payload.scene_placements || {};
    state.placementSummary = payload.placement_summary || null;
  } catch (err) {
    state.chapters = [];
    state.scenePlacements = {};
    state.placementSummary = null;
    console.warn('[chapters] load failed', err);
  }
}

function chapterDisplayName(chapter_id) {
  const chap = (state.chapters || []).find((c) => c.chapter_id === chapter_id);
  return chap ? chap.display_name : '';
}

function actDisplayName(chapter_id, act_id) {
  const chap = (state.chapters || []).find((c) => c.chapter_id === chapter_id);
  if (!chap) return '';
  const act = (chap.acts || []).find((a) => a.act_id === act_id);
  return act ? act.display_name : '';
}

function renderChapterLinkForScene(detail) {
  const link = els.sceneChapterLink;
  const placement = state.scenePlacements[detail.scene_id];
  if (!placement) {
    link.hidden = true;
    return;
  }
  if (!placement.chapter_id || !placement.act_id) {
    // Reviewer §4.3: when sidecar lacks chapter_id/act_id we no longer
    // synthesize a "未归入" pseudo-placement.  Show a small advisory
    // instead so the operator knows the data is missing — but never
    // claim a chapter/act the data doesn't support.
    link.hidden = false;
    const anchor = placement.scene_anchor || '';
    link.innerHTML =
      `<span class="badge badge-muted">sidecar 缺 chapter_id / act_id</span> ` +
      `<span class="advisory-note">scene_anchor=<code>${escapeHtml(anchor)}</code></span>`;
    return;
  }
  const chapName = chapterDisplayName(placement.chapter_id);
  const actName = actDisplayName(placement.chapter_id, placement.act_id);
  const sourceBadge = placement.source === 'sidecar'
    ? '<span class="badge badge-pass" title="from dep_index sidecar">sidecar</span>'
    : '<span class="badge badge-info" title="ontology included_scenes lookup via scene_anchor">ontology</span>';
  link.hidden = false;
  link.innerHTML =
    `属 chapter <a href="#" data-chapter="${escapeHtml(placement.chapter_id)}">${escapeHtml(placement.chapter_id)}</a> ` +
    `／ act <code>${escapeHtml(placement.act_id)}</code> ` +
    `${sourceBadge} ` +
    `<span class="advisory-note">${escapeHtml(chapName)} · ${escapeHtml(actName)}</span>`;
  const a = link.querySelector('a[data-chapter]');
  if (a) a.addEventListener('click', (e) => {
    e.preventDefault();
    setNavMode('chapter');
  });
}

function setNavMode(mode) {
  state.navMode = mode === 'chapter' ? 'chapter' : 'list';
  for (const btn of els.navButtons) {
    btn.classList.toggle('active', btn.dataset.nav === state.navMode);
  }
  renderSceneList();
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
    'filter-skipped': 'skipped',
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
  els.notReviewableNote = document.getElementById('not-reviewable-note');
  // T-3.6b
  els.navButtons = document.querySelectorAll('#nav-mode .nav-btn');
  els.sceneTree = document.getElementById('scene-tree');
  els.sceneChapterLink = document.getElementById('scene-chapter-link');
  els.staleToggle = document.getElementById('stale-toggle');
  els.stalePanel = document.getElementById('stale-panel');
  els.staleSince = document.getElementById('stale-since');
  els.staleOntology = document.getElementById('stale-ontology');
  els.staleStatePaths = document.getElementById('stale-state-paths');
  els.staleVisuals = document.getElementById('stale-visuals');
  els.staleClocks = document.getElementById('stale-clocks');
  els.staleRefresh = document.getElementById('stale-refresh');
  els.staleList = document.getElementById('stale-list');
  els.staleError = document.getElementById('stale-error');
  els.staleBanner = document.getElementById('stale-banner');
  els.visualsContent = document.getElementById('visuals-content');
  els.playtestPanel = document.getElementById('playtest-panel');
  els.visualModal = document.getElementById('visual-modal');
  els.visualModalImg = document.getElementById('visual-modal-img');
  els.visualModalCaption = document.getElementById('visual-modal-caption');
  els.visualModalClose = document.getElementById('visual-modal-close');
}

function bindIntegrationsControls() {
  for (const btn of els.navButtons) {
    btn.addEventListener('click', () => setNavMode(btn.dataset.nav));
  }
  els.staleToggle.addEventListener('click', () => {
    els.stalePanel.open = !els.stalePanel.open;
  });
  els.staleRefresh.addEventListener('click', refreshStale);
  els.staleSince.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') refreshStale();
  });
  els.visualModalClose.addEventListener('click', closeVisualModal);
  els.visualModal.addEventListener('click', (e) => {
    if (e.target === els.visualModal || e.target.classList.contains('visual-modal-backdrop')) {
      closeVisualModal();
    }
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !els.visualModal.hidden) closeVisualModal();
  });
}

async function boot() {
  cacheElements();
  bindTabBar(document.getElementById('main-tabs'));
  bindTabBar(document.getElementById('validator-tabs'));
  bindFilters();
  bindFormatButtons();
  bindReviewButtons();
  bindIntegrationsControls();
  setGraphSourceBadge('—', 'pending');
  updateStaleToggleBadge();
  try {
    await Promise.all([refreshScenes(), loadChapters()]);
  } catch (err) {
    els.sceneList.innerHTML = `<li class="placeholder">scene 列表加载失败：${escapeHtml(err.message)}</li>`;
  }
}

document.addEventListener('DOMContentLoaded', boot);
