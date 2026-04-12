/* YouTube Shorts Music — Frontend */

const API = '/api';
let currentProject = null;

// --- API helpers ---

async function api(method, path, body, isFormData = false) {
  const opts = { method };
  if (body && !isFormData) {
    opts.headers = { 'Content-Type': 'application/json' };
    opts.body = JSON.stringify(body);
  } else if (body && isFormData) {
    opts.body = body;
  }
  const res = await fetch(`${API}${path}`, opts);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Request failed');
  }
  return res.json();
}

// --- Dashboard ---

let dashboardProjects = [];
let dashboardFilters = {
  query: '',
  moods: new Set(),
  substyle: '',
};
let saveTimers = {}; // per-card debounce timers for notes/title_lock
let expandedCards = new Set(); // track which cards are expanded

async function loadDashboard() {
  document.getElementById('view-dashboard').classList.remove('hidden');
  document.getElementById('view-project').classList.add('hidden');
  document.getElementById('view-editor')?.classList.add('hidden');
  // Update nav-right for dashboard
  document.getElementById('nav-right').innerHTML = `
    <label class="lite-toggle"><input type="checkbox" ${isLiteMode() ? 'checked' : ''} onchange="handleLiteToggle(this.checked)"><span>Lite</span></label>
    <button class="btn btn-s" id="sync-yt-btn" onclick="handleYouTubeSync()">YouTube 동기화</button>
    <button class="btn btn-p" onclick="showCreateModal()">+ 새 프로젝트</button>
  `;
  currentProject = null;
  const list = document.getElementById('project-list');
  list.innerHTML = '<div class="loading-overlay"><div class="spinner"></div></div>';
  try {
    dashboardProjects = (await api('GET', '/projects')).reverse();
    renderProjectList();
  } catch (e) {
    list.innerHTML = `<div style="text-align:center;padding:40px;color:var(--error)">${e.message}</div>`;
  }
}

function renderLiteToggle() {
  const on = isLiteMode();
  return `<label class="lite-toggle"><input type="checkbox" ${on ? 'checked' : ''} onchange="handleLiteToggle(this.checked)"><span>Lite</span></label>`;
}

function handleLiteToggle(on) {
  setLiteMode(on);
  if (currentProject) {
    renderProject();
  } else {
    renderProjectList();
  }
}

function filterProjects() {
  const q = dashboardFilters.query.trim().toLowerCase();
  const wantMoods = dashboardFilters.moods;
  const wantSubstyle = dashboardFilters.substyle;

  return dashboardProjects.filter(p => {
    if (q) {
      const hay = [
        p.id, p.genre,
        p.title_lock || '',
        (p.metadata && p.metadata.title) || '',
        (p.suno_prompt && p.suno_prompt.prompt) || '',
        (p.suno_prompt && p.suno_prompt.style) || '',
        (p.suno_prompt && p.suno_prompt.substyle) || '',
        (p.mood_tags || []).join(' '),
        (p.motif_tags || []).join(' '),
        p.notes || '',
      ].join(' ').toLowerCase();
      if (!hay.includes(q)) return false;
    }
    if (wantMoods.size) {
      const pm = new Set(p.mood_tags || []);
      for (const m of wantMoods) if (!pm.has(m)) return false;
    }
    if (wantSubstyle) {
      const ps = (p.suno_prompt && p.suno_prompt.substyle) || '';
      if (ps !== wantSubstyle) return false;
    }
    return true;
  });
}

async function renderProjectList() {
  const list = document.getElementById('project-list');
  if (!moodsCache) {
    try { moodsCache = await api('GET', '/tags/moods'); }
    catch { moodsCache = []; }
  }
  if (!dashboardProjects.length) {
    list.innerHTML = renderStatsBar() + renderFilterBar(0, 0) + `
      <div style="text-align:center;padding:60px 20px;color:var(--t3)">
        <div style="font-size:14px;color:var(--t2);margin-bottom:8px">프로젝트 없음</div>
        <div style="font-size:12px">새 프로젝트를 생성하여 시작하세요</div>
      </div>`;
    return;
  }
  const filtered = filterProjects();
  const cards = filtered.map(p => renderCard(p)).join('') || `
    <div style="padding:40px 20px;text-align:center;color:var(--t3)">필터와 일치하는 프로젝트가 없습니다.</div>
  `;
  list.innerHTML = renderStatsBar() + renderFilterBar(filtered.length, dashboardProjects.length) + `<div class="card-list">${cards}</div>`;
}

function renderFilterBar(matchCount, totalCount) {
  const moodChips = (moodsCache || []).map(m => {
    const on = dashboardFilters.moods.has(m.name);
    return `<button class="mchip ${on ? 'on' : ''}" data-m="${m.name}" onclick="toggleFilterMood('${m.name}')" title="${esc(m.description)}">${esc(m.label)}</button>`;
  }).join('');

  const substyles = collectSubstyles();
  const substyleOptions = ['<option>전체 장르</option>']
    .concat(substyles.map(s =>
      `<option value="${attr(s)}" ${dashboardFilters.substyle === s ? 'selected' : ''}>${esc(s)}</option>`
    )).join('');

  const hasFilter = dashboardFilters.query || dashboardFilters.moods.size || dashboardFilters.substyle;

  return `
    <div class="filter-wrap">
      <div class="filter-row">
        <div class="filter-search-wrap">
          <svg width="12" height="12" viewBox="0 0 16 16" fill="none"><circle cx="6.5" cy="6.5" r="4.5" stroke="currentColor" stroke-width="1.5"/><path d="M10 10L14 14" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
          <input class="filter-search" type="text" placeholder="트랙, 장르, 무드 검색..."
                 value="${attr(dashboardFilters.query)}"
                 oninput="handleDashboardSearch(this.value)">
        </div>
        <button class="filter-expand-btn" onclick="toggleFilterExpand()">
          <svg width="10" height="10" viewBox="0 0 12 12" fill="none"><rect y="1.5" width="12" height="1.5" rx=".75" fill="currentColor"/><rect y="5.5" width="9" height="1.5" rx=".75" fill="currentColor"/><rect y="9.5" width="6" height="1.5" rx=".75" fill="currentColor"/></svg>
          필터
          <svg class="filter-chevron" width="8" height="8" viewBox="0 0 10 10" fill="none" style="transition:transform 140ms ease"><path d="M2 3.5L5 6.5L8 3.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
        </button>
        ${hasFilter ? `<button class="btn btn-s" style="font-size:10px" onclick="clearFilters()">초기화</button>` : ''}
        <span class="filter-count">${matchCount} / ${totalCount}</span>
      </div>
      <div class="filter-expanded" id="filter-expanded">
        <span class="filter-section-lbl">무드</span>
        <div class="mood-chips">${moodChips}</div>
        <div class="nav-divider" style="height:16px;margin:0 8px"></div>
        <span class="filter-section-lbl">서브스타일</span>
        <select class="genre-select" onchange="handleFilterSubstyle(this.value)">${substyleOptions}</select>
      </div>
    </div>
  `;
}

function toggleFilterExpand() {
  const el = document.getElementById('filter-expanded');
  const chevrons = document.querySelectorAll('.filter-chevron');
  el.classList.toggle('open');
  chevrons.forEach(ch => { ch.style.transform = el.classList.contains('open') ? 'rotate(180deg)' : ''; });
}

function collectSubstyles() {
  const set = new Set();
  for (const p of dashboardProjects) {
    const s = p.suno_prompt && p.suno_prompt.substyle;
    if (s) set.add(s);
  }
  return Array.from(set).sort();
}

function handleDashboardSearch(value) {
  dashboardFilters.query = value;
  renderProjectList();
}

function toggleFilterMood(name) {
  if (dashboardFilters.moods.has(name)) dashboardFilters.moods.delete(name);
  else dashboardFilters.moods.add(name);
  renderProjectList();
}

function handleFilterSubstyle(value) {
  dashboardFilters.substyle = value;
  renderProjectList();
}

function clearFilters() {
  dashboardFilters = { query: '', moods: new Set(), substyle: '' };
  renderProjectList();
}

// --- Stats bar ---

function renderStatsBar() {
  const total = dashboardProjects.length;
  if (!total) return '';
  let totalViews = 0;
  let synced = 0;
  const genreCounts = {};
  for (const p of dashboardProjects) {
    totalViews += (p.youtube_stats || {}).views || 0;
    if (p.youtube_video_id) synced++;
    const g = p.genre || 'unknown';
    genreCounts[g] = (genreCounts[g] || 0) + 1;
  }
  const topGenre = Object.entries(genreCounts).sort((a,b) => b[1]-a[1])[0];
  return `
    <div class="stats-strip">
      <div class="stat-item"><span class="stat-val">${total}</span><span class="stat-lbl">프로젝트</span></div>
      ${totalViews ? `<div class="stat-item"><span class="stat-val">${totalViews.toLocaleString()}</span><span class="stat-lbl">총 조회수</span></div>` : ''}
      ${synced ? `<div class="stat-item"><span class="stat-val">${synced}</span><span class="stat-lbl">동기화</span></div>` : ''}
      ${topGenre ? `<div class="stat-item"><span class="stat-lbl">인기 장르</span><span class="stat-badge">${esc(topGenre[0])}</span></div>` : ''}
    </div>
  `;
}

// --- Card render (collapsed / expanded) ---

function toggleCardExpand(pid) {
  if (expandedCards.has(pid)) expandedCards.delete(pid);
  else expandedCards.add(pid);
  refreshCard(pid);
}

function renderCard(p) {
  return expandedCards.has(p.id) ? renderExpandedCard(p) : renderCollapsedCard(p);
}

function renderCollapsedCard(p) {
  const title = p.title_lock || (p.metadata && p.metadata.title) || p.id;
  const sp = p.suno_prompt || {};
  const meta = p.metadata || {};
  const stats = p.youtube_stats || {};
  const isGold = (stats.views || 0) >= 1000;

  const thumbSrc = p.thumbnail_url
    || ((p.visual_refs && p.visual_refs.length)
        ? `/api/projects/${p.id}/refs/${encodeURIComponent(p.visual_refs[0])}`
        : '');
  const thumbHtml = thumbSrc
    ? `<img class="ccard-thumb" src="${thumbSrc}" alt="" loading="lazy" style="width:56px;height:32px;object-fit:cover;border-radius:3px;flex-shrink:0">`
    : `<div class="thumb-ph has-color"><span style="font-size:7px;color:var(--t4)">${esc(p.genre).slice(0,6).toUpperCase()}</span></div>`;

  const preview = (meta.first_comment || sp.style || sp.prompt || '').split('\n')[0];

  const moodDots = (p.mood_tags || []).map(m => {
    const colorMap = {crimson:'var(--crimson)',void:'var(--void)',frost:'var(--frost)',steel:'var(--steel)',ember:'var(--ember)',shadow:'var(--shadow)'};
    return `<span class="mdot" style="background:${colorMap[m] || 'var(--acc)'}" title="${esc(m)}"></span>`;
  }).join('');

  const viewsText = stats.views ? `${Number(stats.views).toLocaleString()}` : '';

  return `
    <div class="ccard ${isGold ? 'gold' : ''}" data-card="${p.id}" onclick="toggleCardExpand('${p.id}')">
      ${thumbHtml}
      <span class="ccard-title">${esc(title)}</span>
      <span class="ccard-preview">${esc(preview)}</span>
      <span class="genre-badge">${esc(p.genre)}</span>
      ${moodDots ? `<div class="mood-dots">${moodDots}</div>` : ''}
      ${viewsText ? `<span class="views ${isGold ? 'hot' : ''}">${viewsText}</span>` : ''}
      <div class="qcopy">
        ${sp.style ? `<button class="cb" onclick="event.stopPropagation();navigator.clipboard.writeText(${JSON.stringify(sp.style)})">Style</button>` : ''}
        ${meta.title ? `<button class="cb" onclick="event.stopPropagation();navigator.clipboard.writeText(${JSON.stringify(meta.title)})">Title</button>` : ''}
        ${meta.first_comment ? `<button class="cb" onclick="event.stopPropagation();navigator.clipboard.writeText(${JSON.stringify(meta.first_comment)})">1st</button>` : ''}
      </div>
      <span class="expand-arrow">&#9662;</span>
    </div>
  `;
}

function renderExpandedCard(p) {
  const title = p.title_lock || (p.metadata && p.metadata.title) || p.id;
  const sp = p.suno_prompt || {};
  const meta = p.metadata || {};
  const stats = p.youtube_stats || {};
  const isGold = (stats.views || 0) >= 1000;
  const lite = isLiteMode();

  const copyIcon = '<svg width="12" height="12" viewBox="0 0 16 16" fill="none"><rect x="5" y="5" width="9" height="9" rx="1.5" stroke="currentColor" stroke-width="1.5"/><path d="M11 5V3.5A1.5 1.5 0 009.5 2h-6A1.5 1.5 0 002 3.5v6A1.5 1.5 0 003.5 11H5" stroke="currentColor" stroke-width="1.5"/></svg>';

  const thumbSrc = p.thumbnail_url
    || ((p.visual_refs && p.visual_refs.length)
        ? `/api/projects/${p.id}/refs/${encodeURIComponent(p.visual_refs[0])}`
        : '');
  const thumbHtml = thumbSrc
    ? `<img class="xthumb-inner" src="${thumbSrc}" alt="" loading="lazy">`
    : `<div class="xthumb-ph">${esc(p.genre)}</div>`;

  const extraRefs = (p.visual_refs || []).filter(f => f !== 'youtube_thumb.jpg').slice(0, 3);
  const refsHtml = extraRefs.map(fname =>
    `<div class="xref-mini"><img src="/api/projects/${p.id}/refs/${encodeURIComponent(fname)}" alt="" style="width:100%;height:100%;object-fit:cover"></div>`
  ).join('') + `<label class="xref-mini" style="border:1px dashed var(--b2);background:transparent;cursor:pointer"><input type="file" accept=".png,.jpg,.jpeg,.webp,.gif" multiple style="display:none" onchange="cardUploadRefs('${p.id}', this.files); this.value='';">+</label>`;

  function copyRow(label, text) {
    if (!text) return '';
    return `
      <div class="copy-row" data-copy="${attr(text)}">
        <span class="cr-label">${label}</span>
        <span class="cr-value">${esc(text)}</span>
        <button class="cr-copy" onclick="copyText(this)">${copyIcon}</button>
      </div>
    `;
  }

  const moodChips = (moodsCache || []).map(m => {
    const on = (p.mood_tags || []).includes(m.name);
    return `<button class="xmchip ${on ? 'on' : ''}" data-m="${m.name}" onclick="cardToggleMood('${p.id}', '${m.name}')">${esc(m.label)}</button>`;
  }).join('');

  const motifChips = (p.motif_tags || []).map(t =>
    `<span class="motif-tag">${esc(t)}<button class="motif-remove" onclick="cardRemoveMotif('${p.id}', '${esc(t)}')" style="background:none;border:none;color:var(--t3);cursor:pointer;font-size:11px;padding:0 2px;margin-left:2px">x</button></span>`
  ).join('');

  const tagsText = (meta.tags || []).map(t => '#' + t).join(' ');
  const pipelineBtn = !lite ? `<button class="btn btn-s" style="font-size:10px;padding:3px 9px" onclick="openProject('${p.id}')">Pipeline</button>` : '';

  return `
    <div class="xcard open ${isGold ? 'gold' : ''}" data-card="${p.id}">
      <div class="xcard-inner">
        <div class="xcard-left">
          <div class="xthumb">${thumbHtml}</div>
          <div class="xrefs">${refsHtml}</div>
          <div class="xstats">
            <div class="xstat"><div class="xstat-n" ${isGold ? 'style="color:var(--gold)"' : ''}>${stats.views ? Number(stats.views).toLocaleString() : '—'}</div><div class="xstat-l">조회</div></div>
            <div class="xstat"><div class="xstat-n">${stats.likes || '—'}</div><div class="xstat-l">좋아요</div></div>
          </div>
        </div>
        <div class="xcard-right">
          <div class="xcard-head">
            <div class="xcard-ttl">${esc(title)}</div>
            <span class="xcard-date">${p.created_at ? formatDate(p.created_at) : ''}</span>
          </div>
          ${copyRow('Style', sp.style)}
          ${copyRow('Prompt', sp.prompt)}
          ${copyRow('Title', meta.title)}
          ${copyRow('1st', meta.first_comment)}
          ${tagsText ? copyRow('Tags', tagsText) : ''}
          <div class="xcard-chips">
            ${moodChips}
            ${motifChips}
            <input class="hcard-motif-input" placeholder="+ motif"
                   onkeydown="if(event.key==='Enter' && this.value.trim()){cardAddMotif('${p.id}', this.value.trim()); this.value='';event.preventDefault();}">
          </div>
          <div>
            <div class="notes-toggle" onclick="toggleNotes(this)">
              <svg width="9" height="9" viewBox="0 0 10 10" fill="none"><path d="M2 3.5L5 6.5L8 3.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
              메모 / 제목 고정
            </div>
            <div class="notes-body">
              <input class="form-input" placeholder="제목 고정" value="${attr(p.title_lock || '')}"
                     oninput="cardScheduleSave('${p.id}', 'title_lock', this.value)" style="margin-bottom:6px">
              <textarea class="form-input" rows="2" placeholder="작업 메모"
                        oninput="cardScheduleSave('${p.id}', 'notes', this.value)">${esc(p.notes || '')}</textarea>
            </div>
          </div>
          <div class="xcard-actions">
            <button class="btn btn-s" style="font-size:10px;padding:3px 9px" onclick="cardRegenMeta('${p.id}')">재생성</button>
            ${pipelineBtn}
            <button class="btn btn-s" style="font-size:10px;padding:3px 9px;color:var(--error)" onclick="cardDelete('${p.id}')">삭제</button>
            <button class="btn btn-p" style="font-size:10px;padding:3px 9px" onclick="toggleCardExpand('${p.id}')">접기</button>
          </div>
        </div>
      </div>
    </div>
  `;
}

function toggleNotes(el) {
  const body = el.nextElementSibling;
  const svg = el.querySelector('svg');
  body.classList.toggle('open');
  if (svg) svg.style.transform = body.classList.contains('open') ? 'rotate(180deg)' : '';
}

function formatDate(iso) {
  try {
    return new Date(iso).toISOString().slice(0, 10);
  } catch { return ''; }
}

// --- Card action handlers (operate on dashboardProjects[] by pid) ---

function findDashProject(pid) {
  return dashboardProjects.find(p => p.id === pid);
}

function replaceDashProject(pid, updated) {
  const idx = dashboardProjects.findIndex(p => p.id === pid);
  if (idx >= 0) dashboardProjects[idx] = updated;
}

function refreshCard(pid) {
  const el = document.querySelector(`[data-card="${pid}"]`);
  const p = findDashProject(pid);
  if (!el || !p) return renderProjectList();
  el.outerHTML = renderCard(p);
}

async function cardPatch(pid, body) {
  try {
    const updated = await api('PATCH', `/projects/${pid}`, body);
    replaceDashProject(pid, updated);
    refreshCard(pid);
  } catch (e) { alert(e.message); }
}

async function cardToggleMood(pid, name) {
  const p = findDashProject(pid);
  if (!p) return;
  const current = new Set(p.mood_tags || []);
  if (current.has(name)) current.delete(name);
  else current.add(name);
  await cardPatch(pid, { mood_tags: Array.from(current) });
}

async function cardAddMotif(pid, tag) {
  const p = findDashProject(pid);
  if (!p) return;
  const current = [...(p.motif_tags || []), tag];
  await cardPatch(pid, { motif_tags: current });
  motifsCache = null;
}

async function cardRemoveMotif(pid, tag) {
  const p = findDashProject(pid);
  if (!p) return;
  const current = (p.motif_tags || []).filter(t => t !== tag);
  await cardPatch(pid, { motif_tags: current });
}

function cardScheduleSave(pid, field, value) {
  const key = `${pid}:${field}`;
  clearTimeout(saveTimers[key]);
  saveTimers[key] = setTimeout(async () => {
    try {
      const body = {};
      body[field] = value;
      const updated = await api('PATCH', `/projects/${pid}`, body);
      replaceDashProject(pid, updated);
      // Don't refreshCard — would steal focus from the input. Local update is enough.
    } catch (e) { console.error(e); }
  }, 600);
}

async function cardUploadRefs(pid, files) {
  if (!files || !files.length) return;
  const fd = new FormData();
  for (const f of files) fd.append('files', f);
  try {
    const updated = await api('POST', `/projects/${pid}/refs`, fd, true);
    replaceDashProject(pid, updated);
    refreshCard(pid);
  } catch (e) { alert(e.message); }
}

async function cardDeleteRef(pid, fname) {
  if (!confirm(`Delete ref "${fname}"?`)) return;
  try {
    const updated = await api('DELETE', `/projects/${pid}/refs/${encodeURIComponent(fname)}`);
    replaceDashProject(pid, updated);
    refreshCard(pid);
  } catch (e) { alert(e.message); }
}

async function cardRegenMeta(pid) {
  const el = document.querySelector(`[data-card="${pid}"]`);
  if (el) el.style.opacity = '0.6';
  try {
    const updated = await api('POST', `/projects/${pid}/metadata`);
    replaceDashProject(pid, updated);
    refreshCard(pid);
  } catch (e) {
    alert(e.message);
    if (el) el.style.opacity = '';
  }
}

async function handleYouTubeSync() {
  const btn = document.getElementById('sync-yt-btn');
  btn.disabled = true;
  btn.textContent = 'Syncing...';
  try {
    const result = await api('POST', '/sync/youtube');
    btn.textContent = `Done (${result.synced} new, ${result.updated} updated)`;
    setTimeout(() => { btn.textContent = 'Sync YouTube'; btn.disabled = false; }, 3000);
    loadDashboard();
  } catch (e) {
    alert(e.message);
    btn.textContent = 'Sync YouTube';
    btn.disabled = false;
  }
}

async function cardDelete(pid) {
  if (!confirm('Delete this project?')) return;
  try {
    await api('DELETE', `/projects/${pid}`);
    dashboardProjects = dashboardProjects.filter(p => p.id !== pid);
    renderProjectList();
  } catch (e) { alert(e.message); }
}

function statusBadge(status) {
  const map = {
    created: ['Created', 'badge-created'],
    music_registered: ['Music', 'badge-music'],
    prompts_done: ['Prompts', 'badge-prompts'],
    composed: ['Composed', 'badge-composed'],
    uploaded: ['Uploaded', 'badge-composed'],
  };
  const [label, cls] = map[status] || [status, 'badge-created'];
  return `<span class="badge ${cls}">${label}</span>`;
}

// --- Create ---

function showCreateModal() {
  document.getElementById('create-modal').classList.remove('hidden');
  const genreInput = document.querySelector('#create-form [name=genre]');
  genreInput.focus();
  // Populate genre presets
  const presetsEl = document.getElementById('genre-presets');
  if (presetsEl) {
    const genres = {};
    for (const p of dashboardProjects) {
      if (p.genre) genres[p.genre] = (genres[p.genre] || 0) + 1;
    }
    const sorted = Object.entries(genres).sort((a,b) => b[1]-a[1]).slice(0, 8);
    presetsEl.innerHTML = sorted.map(([g]) =>
      `<button type="button" class="gpchip" onclick="this.parentElement.querySelectorAll('.gpchip').forEach(c=>c.classList.remove('on'));this.classList.add('on');document.querySelector('#create-form [name=genre]').value='${esc(g)}'">${esc(g)}</button>`
    ).join('');
  }
  if (!genreInput._substyleWired) {
    genreInput._substyleWired = true;
    genreInput.addEventListener('input', updateSubstyleVisibility);
  }
  updateSubstyleVisibility();
}

function hideCreateModal() {
  document.getElementById('create-modal').classList.add('hidden');
  document.getElementById('create-form').reset();
  document.getElementById('substyle-group').classList.add('hidden');
  document.getElementById('substyle-hint').textContent = '';
}

async function handleCreate(e) {
  e.preventDefault();
  const form = e.target;
  const btn = document.getElementById('create-btn');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Creating...';

  const fd = new FormData(form);
  const style = fd.get('style') || null;
  const substyle = fd.get('substyle') || null;
  const body = {
    genre: fd.get('genre'),
    style,
    substyle,
  };

  try {
    const project = await api('POST', '/projects', body);
    hideCreateModal();
    openProject(project.id);
  } catch (err) {
    alert(err.message);
  } finally {
    btn.disabled = false;
    btn.textContent = 'Create';
  }
}

// --- Project View ---

const STEPS = [
  { key: 'create', label: 'Create' },
  { key: 'metadata', label: 'Metadata' },
  { key: 'library', label: 'Library' },
  { key: 'music', label: 'Music', fullOnly: true },
  { key: 'prompts', label: 'Prompts', fullOnly: true },
  { key: 'assets', label: 'Assets', fullOnly: true },
  { key: 'compose', label: 'Compose', fullOnly: true },
];

let metadataAcknowledged = false;
let libraryAcknowledged = false;

// UI Lite mode — hides video-production steps; persisted in localStorage.
function isLiteMode() {
  return localStorage.getItem('uiLiteMode') !== 'false';
}

function setLiteMode(on) {
  localStorage.setItem('uiLiteMode', on ? 'true' : 'false');
}

function visibleSteps() {
  return isLiteMode() ? STEPS.filter(s => !s.fullOnly) : STEPS;
}

// Tag caches
let moodsCache = null;
let motifsCache = null;

async function openProject(id) {
  document.getElementById('view-dashboard').classList.add('hidden');
  document.getElementById('view-project').classList.remove('hidden');
  document.getElementById('view-editor')?.classList.add('hidden');

  // nav-right gets lite toggle + delete; brand is static
  document.getElementById('nav-right').innerHTML =
    `${renderLiteToggle()}<button class="btn btn-s" style="color:var(--error)" onclick="deleteProject('${id}')">삭제</button>`;

  const content = document.getElementById('step-content');
  content.innerHTML = '<div class="loading-overlay"><div class="spinner"></div></div>';
  metadataAcknowledged = false;
  libraryAcknowledged = false;

  try {
    currentProject = await api('GET', `/projects/${id}`);
    renderProject();
  } catch (err) {
    content.innerHTML = `<div style="text-align:center;padding:40px;color:var(--error)">${err.message}</div>`;
  }
}

function getActiveStep(p) {
  const lite = isLiteMode();
  if (!lite && p.steps_completed.includes('compose')) return 'compose';
  if (!lite && p.steps_completed.includes('prompts')) return 'assets';
  if (!lite && p.steps_completed.includes('music')) return 'prompts';
  if (!lite && libraryAcknowledged && p.steps_completed.includes('create')) return 'music';
  if (metadataAcknowledged && p.steps_completed.includes('create')) return 'library';
  if (p.steps_completed.includes('create')) return 'metadata';
  return 'create';
}

function libraryHasContent(p) {
  return (
    (p.visual_refs && p.visual_refs.length) ||
    (p.mood_tags && p.mood_tags.length) ||
    (p.motif_tags && p.motif_tags.length) ||
    (p.notes && p.notes.trim()) ||
    (p.title_lock && p.title_lock.trim())
  );
}

function renderSteps(activeKey, p) {
  const completed = p.steps_completed;
  const steps = visibleSteps();
  const bar = document.getElementById('steps-bar');
  bar.innerHTML = steps.map((s, i) => {
    let done = completed.includes(s.key);
    if (s.key === 'assets' && completed.includes('compose')) done = true;
    if (s.key === 'metadata' && (p.metadata || completed.includes('music'))) done = true;
    if (s.key === 'library' && (libraryHasContent(p) || completed.includes('music'))) done = true;
    const active = s.key === activeKey;
    const cls = done ? 'completed' : active ? 'active' : '';
    const check = done ? '&#10003;' : (i + 1);
    return `
      <div class="step ${cls}">
        <span class="step-num">${check}</span>
        <span>${s.label}</span>
      </div>
      ${i < steps.length - 1 ? '<div class="step-line"></div>' : ''}
    `;
  }).join('');
}

function renderProject() {
  const p = currentProject;
  const active = getActiveStep(p);
  renderSteps(active, p);

  const el = document.getElementById('step-content');

  if (active === 'create') {
    el.innerHTML = renderStepCreate(p);
    setupDropzone('music-dropzone', (files) => handleMusicUpload(files[0]));
  } else if (active === 'metadata') {
    el.innerHTML = renderStepMetadata(p);
  } else if (active === 'library') {
    renderStepLibrary(p);
  } else if (active === 'music') {
    el.innerHTML = renderStepMusic(p);
    setupDropzone('music-dropzone', (files) => handleMusicUpload(files[0]));
  } else if (active === 'prompts') {
    el.innerHTML = renderStepPrompts(p);
  } else if (active === 'assets') {
    el.innerHTML = renderStepAssets(p);
    setupDropzone('assets-dropzone', handleAssetsUpload);
    loadAssetsStatus();
    // scene item copy buttons need prompt text unescaped for clipboard

  } else if (active === 'compose') {
    el.innerHTML = renderStepCompose(p);
  }
}

// --- Step: Create (Suno prompt) ---

function renderStepCreate(p) {
  if (!p.suno_prompt) {
    return `<div class="card"><div class="text-2 text-sm">Suno prompt not generated. Check API key.</div></div>`;
  }
  return renderSunoPrompt(p) + `<div class="mt-16">${renderMusicUpload()}</div>`;
}

// --- Step: Music ---

function renderMusicUpload() {
  return `
    <div id="music-dropzone" class="dropzone">
      <div class="dropzone-label">Drop MP3 here or click to upload</div>
      <div class="dropzone-hint">.mp3 &middot; Max 58s recommended for Shorts</div>
      <input type="file" accept=".mp3,.wav,.m4a" style="display:none">
    </div>
  `;
}

function renderSunoPrompt(p) {
  if (!p.suno_prompt) return '';
  const sp = p.suno_prompt;
  return `
    <div class="prompt-card mb-12" data-copy="${attr(sp.style)}">
      <div class="flex-between">
        <div class="prompt-card-title">Suno Style Prompt</div>
        <button class="copy-btn" onclick="copyText(this)">Copy</button>
      </div>
      <div class="prompt-card-value">${esc(sp.style)}</div>
    </div>
    <div class="prompt-card mb-12" data-copy="${attr(sp.prompt)}">
      <div class="flex-between">
        <div class="prompt-card-title">Description</div>
        <button class="copy-btn" onclick="copyText(this)">Copy</button>
      </div>
      <div class="prompt-card-value">${esc(sp.prompt)}</div>
    </div>
    <div class="prompt-card mb-12">
      <div class="prompt-card-title">Title</div>
      <div class="prompt-card-value">${esc(sp.title_suggestion || '-')}</div>
    </div>
    ${sp.lyrics ? `
    <div class="prompt-card mb-12" data-copy="${attr(sp.lyrics)}">
      <div class="flex-between">
        <div class="prompt-card-title">Lyrics</div>
        <button class="copy-btn" onclick="copyText(this)">Copy</button>
      </div>
      <div class="prompt-card-value" style="white-space:pre-line">${esc(sp.lyrics)}</div>
    </div>
    ` : ''}
    ${renderSunoOptions(sp)}
    <div class="text-sm text-3 mb-12 mt-16">
      Copy the prompt above to Suno, create your track, then upload the MP3 below.
    </div>
  `;
}

function renderSunoOptions(sp) {
  const items = [];
  if (sp.substyle) items.push(['Substyle', esc(sp.substyle)]);
  if (sp.bpm_suggestion) items.push(['BPM', sp.bpm_suggestion]);
  items.push(['Vocal Gender', sp.vocal_gender ? esc(sp.vocal_gender) : 'Instrumental']);
  if (sp.lyrics_mode) items.push(['Lyrics Mode', esc(sp.lyrics_mode)]);
  if (sp.exclude_styles) items.push(['Exclude', esc(sp.exclude_styles)]);
  if (sp.weirdness != null) items.push(['Weirdness', sp.weirdness + '%']);
  if (sp.style_influence != null) items.push(['Style Influence', sp.style_influence + '%']);
  return `
    <div class="suno-options mb-12">
      <div class="prompt-card-title" style="margin-bottom:10px">Suno Options</div>
      <div class="options-grid">
        ${items.map(([l, v]) => `<div class="opt-item"><span class="opt-label">${l}</span><span class="opt-value">${v}</span></div>`).join('')}
      </div>
    </div>
  `;
}

function renderStepMusic(p) {
  const metaCard = p.metadata ? renderMetadataCard(p.metadata) + '<div class="mt-16"></div>' : '';
  return metaCard + renderSunoPrompt(p) + renderMusicUpload();
}

// --- Step: Metadata ---

function renderMetadataCard(meta) {
  const tags = Array.isArray(meta.tags) ? meta.tags : [];
  const firstComment = meta.first_comment || '';
  return `
    <div class="card" data-copy="${attr(meta.title || '')}">
      <div class="flex-between">
        <div class="text-sm text-3" style="margin-bottom:4px">TITLE</div>
        <button class="copy-btn" onclick="copyText(this)">Copy</button>
      </div>
      <div style="font-size:16px;font-weight:600;margin-bottom:16px">${esc(meta.title || '')}</div>
      ${meta.description ? `
      <div class="text-sm text-3" style="margin-top:12px;margin-bottom:4px">DESCRIPTION</div>
      <div class="text-sm text-2 mb-12" style="white-space:pre-line">${esc(meta.description)}</div>
      ` : ''}
      ${tags.length ? `
      <div class="text-sm text-3" style="margin-top:12px;margin-bottom:4px">TAGS</div>
      <div class="text-sm text-3 mb-12">${tags.map(t => '#' + esc(t)).join(' ')}</div>
      ` : ''}
    </div>
    ${firstComment ? `
    <div class="card mt-12" data-copy="${attr(firstComment)}">
      <div class="flex-between">
        <div class="text-sm text-3" style="margin-bottom:4px">PINNED FIRST COMMENT</div>
        <button class="copy-btn" onclick="copyText(this)">Copy</button>
      </div>
      <div class="text-sm text-2" style="white-space:pre-line">${esc(firstComment)}</div>
    </div>
    ` : ''}
  `;
}

// --- Step: Library ---

async function renderStepLibrary(p) {
  const el = document.getElementById('step-content');
  el.innerHTML = '<div class="loading-overlay"><div class="spinner"></div></div>';

  if (!moodsCache) {
    try { moodsCache = await api('GET', '/tags/moods'); }
    catch { moodsCache = []; }
  }
  if (!motifsCache) {
    try { motifsCache = await api('GET', '/tags/motifs'); }
    catch { motifsCache = []; }
  }

  const moodChips = moodsCache.map(m => {
    const on = (p.mood_tags || []).includes(m.name);
    return `<button class="mood-chip ${on ? 'on' : ''}" data-mood="${m.name}" onclick="toggleMood('${m.name}')" title="${esc(m.description)}">${esc(m.label)}</button>`;
  }).join('');

  const motifChips = (p.motif_tags || []).map(t =>
    `<span class="motif-tag">${esc(t)}<button class="motif-remove" onclick="removeMotif('${esc(t)}')">×</button></span>`
  ).join('');

  const motifSuggestions = (motifsCache || [])
    .filter(m => !(p.motif_tags || []).includes(m.name))
    .slice(0, 12)
    .map(m => `<button class="motif-suggest" onclick="addMotif('${esc(m.name)}')">${esc(m.name)} <span class="text-3">×${m.count}</span></button>`)
    .join('');

  const refs = (p.visual_refs || []).map(fname =>
    `<div class="ref-thumb">
       <img src="/api/projects/${p.id}/refs/${encodeURIComponent(fname)}" alt="${esc(fname)}">
       <button class="ref-remove" onclick="deleteRef('${esc(fname)}')">×</button>
     </div>`
  ).join('');

  const finalTitle = p.title_lock || (p.metadata && p.metadata.title) || '';
  const continueBtn = !isLiteMode() ? `
    <button class="btn btn-primary mt-16" onclick="handleAdvanceToMusic()">
      Continue to Music →
    </button>` : '';

  el.innerHTML = `
    <div class="card">
      <div class="library-section-label">VISUAL REFERENCES</div>
      <div id="refs-dropzone" class="dropzone-compact">
        <span class="dropzone-label">Drop ref images or click</span>
        <input type="file" accept=".png,.jpg,.jpeg,.webp,.gif" multiple style="display:none">
      </div>
      <div class="ref-grid mt-12">${refs || '<div class="text-sm text-3">레퍼런스 이미지 없음</div>'}</div>
    </div>

    <div class="card mt-16">
      <div class="library-section-label">MOOD</div>
      <div class="mood-grid">${moodChips}</div>
    </div>

    <div class="card mt-16">
      <div class="library-section-label">MOTIFS</div>
      <div class="motif-list">${motifChips || '<span class="text-sm text-3">태그 없음</span>'}</div>
      <input id="motif-input" class="form-input mt-12" placeholder="모티프 태그 입력 후 Enter (예: hood, spacesuit, ruins)">
      ${motifSuggestions ? `<div class="motif-suggestions mt-12"><div class="text-sm text-3 mb-12">자주 쓴 태그</div>${motifSuggestions}</div>` : ''}
    </div>

    <div class="card mt-16">
      <div class="library-section-label">FINAL TITLE LOCK</div>
      <div class="text-sm text-3 mb-12">YouTube 업로드 확정 제목 (없으면 메타의 title 사용)</div>
      <input id="title-lock-input" class="form-input" value="${attr(p.title_lock || '')}" placeholder="${attr((p.metadata && p.metadata.title) || '제목 없음')}">
      <div class="text-sm text-3 mt-12">현재 확정: <strong>${esc(finalTitle)}</strong></div>
    </div>

    <div class="card mt-16">
      <div class="library-section-label">NOTES</div>
      <textarea id="notes-input" class="form-input" rows="5" placeholder="작업 메모, 참고 링크, 다음 버전 아이디어 등">${esc(p.notes || '')}</textarea>
    </div>

    <div class="mt-16" style="display:flex;gap:8px">
      <button class="btn btn-primary" onclick="saveLibrary()">Save Library</button>
      ${continueBtn}
    </div>
  `;

  setupDropzone('refs-dropzone', handleRefsUpload);

  const motifInput = document.getElementById('motif-input');
  if (motifInput) {
    motifInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && motifInput.value.trim()) {
        e.preventDefault();
        addMotif(motifInput.value.trim());
        motifInput.value = '';
      }
    });
  }
}

async function toggleMood(name) {
  const current = new Set(currentProject.mood_tags || []);
  if (current.has(name)) current.delete(name);
  else current.add(name);
  try {
    currentProject = await api('PATCH', `/projects/${currentProject.id}`, {
      mood_tags: Array.from(current),
    });
    renderStepLibrary(currentProject);
  } catch (e) { alert(e.message); }
}

async function addMotif(tag) {
  const current = [...(currentProject.motif_tags || []), tag];
  try {
    currentProject = await api('PATCH', `/projects/${currentProject.id}`, {
      motif_tags: current,
    });
    motifsCache = null;
    renderStepLibrary(currentProject);
  } catch (e) { alert(e.message); }
}

async function removeMotif(tag) {
  const current = (currentProject.motif_tags || []).filter(t => t !== tag);
  try {
    currentProject = await api('PATCH', `/projects/${currentProject.id}`, {
      motif_tags: current,
    });
    renderStepLibrary(currentProject);
  } catch (e) { alert(e.message); }
}

async function saveLibrary() {
  const notes = document.getElementById('notes-input').value;
  const titleLock = document.getElementById('title-lock-input').value.trim();
  try {
    currentProject = await api('PATCH', `/projects/${currentProject.id}`, {
      notes,
      title_lock: titleLock,
    });
    const btn = event.target;
    const prev = btn.textContent;
    btn.textContent = 'Saved';
    setTimeout(() => { btn.textContent = prev; }, 1200);
  } catch (e) { alert(e.message); }
}

async function handleRefsUpload(files) {
  if (!files.length) return;
  const fd = new FormData();
  for (const f of files) fd.append('files', f);
  try {
    currentProject = await api('POST', `/projects/${currentProject.id}/refs`, fd, true);
    renderStepLibrary(currentProject);
  } catch (e) { alert(e.message); }
}

async function deleteRef(fname) {
  if (!confirm(`Delete ref "${fname}"?`)) return;
  try {
    currentProject = await api('DELETE', `/projects/${currentProject.id}/refs/${encodeURIComponent(fname)}`);
    renderStepLibrary(currentProject);
  } catch (e) { alert(e.message); }
}

function renderStepMetadata(p) {
  if (!p.metadata) {
    return `
      <div class="card">
        <div class="text-sm text-2 mb-12">
          YouTube 제목/설명/태그 메타데이터를 바로 생성합니다.
          음악·이미지 업로드 없이 미리 확인할 수 있습니다.
        </div>
        <div style="display:flex;gap:8px;align-items:center">
          <button class="btn btn-primary" id="gen-metadata-btn" onclick="handleGenMetadata()">
            Generate YouTube Metadata
          </button>
          <button class="btn btn-secondary" onclick="handleAdvanceToLibrary()">
            Skip to Library &rarr;
          </button>
        </div>
      </div>
    `;
  }
  return `
    ${renderMetadataCard(p.metadata)}
    <div class="mt-16" style="display:flex;gap:8px">
      <button class="btn btn-secondary" id="regen-metadata-btn" onclick="handleGenMetadata()">
        Regenerate
      </button>
      <button class="btn btn-primary" onclick="handleAdvanceToLibrary()">
        Next: Library &rarr;
      </button>
    </div>
  `;
}

// --- Step: Prompts ---

function renderStepPrompts(p) {
  if (p.bpm) {
    return `
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-value">${p.bpm}</div>
          <div class="stat-label">BPM</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">${p.duration_sec.toFixed(0)}s</div>
          <div class="stat-label">Duration</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">${p.scenes.length}</div>
          <div class="stat-label">Scenes</div>
        </div>
      </div>
      ${p.duration_sec > 58 ? '<div class="text-sm mb-12" style="color:var(--warning)">Duration exceeds 58s Shorts limit</div>' : ''}
      <button class="btn btn-primary" id="gen-prompts-btn" onclick="handleGenPrompts()">
        Generate Scene Prompts
      </button>
    `;
  }
  return '<div class="card text-sm text-2">Upload music first.</div>';
}

// --- Step: Assets ---

function renderStepAssets(p) {
  const currentStyle = p.style || '';
  const regenBtn = `
    <div class="regen-row mb-12" style="display:flex;gap:8px;align-items:center">
      <select class="form-input" id="regen-style-select" style="flex:1">
        <option value="" ${!currentStyle ? 'selected' : ''}>Default (genre-based)</option>
        <option value="anime" ${currentStyle === 'anime' ? 'selected' : ''}>Anime (Japanese animation)</option>
        <option value="cyberpunk" ${currentStyle === 'cyberpunk' ? 'selected' : ''}>Cyberpunk</option>
        <option value="retro" ${currentStyle === 'retro' ? 'selected' : ''}>Retro / Vaporwave</option>
        <option value="watercolor" ${currentStyle === 'watercolor' ? 'selected' : ''}>Watercolor</option>
      </select>
      <button class="btn btn-secondary" id="regen-prompts-btn" onclick="handleRegenPrompts()">
        Regenerate
      </button>
    </div>`;

  const scenePrompts = p.scenes.map(s => `
    <div class="scene-item" data-copy="${attr(s.image_prompt || '')}">
      <div class="scene-header">
        <div>
          <span class="scene-id">Scene ${String(s.id).padStart(2, '0')}</span>
          <span class="scene-time">${s.start_sec.toFixed(1)}s ~ ${s.end_sec.toFixed(1)}s</span>
        </div>
        <button class="copy-btn" onclick="copyText(this)">Copy</button>
      </div>
      <div class="scene-prompt">${esc(s.image_prompt || '')}</div>
    </div>
  `).join('');

  return `
    <div class="assets-toolbar">
      <div id="assets-status"></div>
      <div id="assets-dropzone" class="dropzone-compact">
        <span class="dropzone-label">Drop images or click</span>
        <input type="file" accept=".png,.jpg,.jpeg,.webp,.mp4,.mov" multiple style="display:none">
      </div>
      <label class="form-check bounce-toggle">
        <input type="checkbox" id="bounce-check">
        Bounce Loop
        <span class="text-3 text-sm">(forward+reverse repeat for video assets)</span>
      </label>
      <button class="btn btn-primary" id="compose-btn" onclick="handleCompose()">
        Compose Video
      </button>
    </div>
    ${regenBtn}
    <div class="scene-list">${scenePrompts}</div>
  `;
}

async function loadAssetsStatus() {
  if (!currentProject) return;
  try {
    const data = await api('GET', `/projects/${currentProject.id}/assets-status`);
    const el = document.getElementById('assets-status');
    if (!el) return;
    const total = data.scenes.length;
    const done = data.scenes.filter(s => s.has_asset).length;
    const pct = total ? Math.round((done / total) * 100) : 0;
    const missing = data.scenes.filter(s => !s.has_asset);
    const uploaded = data.scenes.filter(s => s.has_asset);

    el.innerHTML = `
      <div class="asset-progress-bar">
        <div class="asset-progress-fill" style="width:${pct}%"></div>
      </div>
      <div class="asset-progress-label">
        <span>${done} / ${total} uploaded</span>
        <span class="text-3">${pct}%</span>
      </div>
      ${missing.length && missing.length <= total ? `
        <details class="asset-details mt-12">
          <summary class="scene-summary">${missing.length} missing</summary>
          <div class="asset-grid">
            ${data.scenes.map(s => `
              <span class="asset-tag ${s.has_asset ? 'uploaded' : ''}">${String(s.id).padStart(2, '0')}</span>
            `).join('')}
          </div>
        </details>
      ` : ''}
    `;
  } catch (_) {}
}

// --- Step: Compose ---

function renderStepCompose(p) {
  const meta = p.metadata || { title: p.genre };
  return `
    ${renderMetadataCard(meta)}
    <div class="card mt-12">
      <video class="video-preview" controls preload="metadata">
        <source src="/api/projects/${p.id}/download" type="video/mp4">
      </video>
      <div class="mt-16 flex-between">
        <a href="/api/projects/${p.id}/download" class="btn btn-primary" download>Download MP4</a>
      </div>
    </div>
  `;
}

// --- Handlers ---

async function handleMusicUpload(file) {
  if (!file || !currentProject) return;

  const content = document.getElementById('step-content');
  content.innerHTML = `<div class="loading-overlay"><div class="spinner"></div>Analyzing beats...</div>`;

  const fd = new FormData();
  fd.append('file', file);

  try {
    currentProject = await api('POST', `/projects/${currentProject.id}/music`, fd, true);
    renderProject();
  } catch (err) {
    content.innerHTML = `<div class="empty-state" style="color:var(--error)">${err.message}</div>`;
  }
}

async function handleRegenPrompts() {
  const btn = document.getElementById('regen-prompts-btn');
  const style = document.getElementById('regen-style-select').value || null;
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Regenerating...';

  try {
    await api('PATCH', `/projects/${currentProject.id}`, { style });
    currentProject = await api('POST', `/projects/${currentProject.id}/prompts`);
    renderProject();
  } catch (err) {
    alert(err.message);
    btn.disabled = false;
    btn.textContent = 'Regenerate';
  }
}

async function handleGenMetadata() {
  const btn = document.getElementById('gen-metadata-btn') || document.getElementById('regen-metadata-btn');
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Generating...';
  }
  try {
    currentProject = await api('POST', `/projects/${currentProject.id}/metadata`);
    document.getElementById('step-content').innerHTML = renderStepMetadata(currentProject);
    renderSteps(getActiveStep(currentProject), currentProject);
  } catch (err) {
    alert(err.message);
    if (btn) {
      btn.disabled = false;
      btn.textContent = btn.id === 'regen-metadata-btn' ? 'Regenerate' : 'Generate YouTube Metadata';
    }
  }
}

function handleAdvanceToLibrary() {
  metadataAcknowledged = true;
  renderProject();
}

function handleAdvanceToMusic() {
  metadataAcknowledged = true;
  libraryAcknowledged = true;
  renderProject();
}

async function handleGenPrompts() {
  const btn = document.getElementById('gen-prompts-btn');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Generating...';

  try {
    currentProject = await api('POST', `/projects/${currentProject.id}/prompts`);
    renderProject();
  } catch (err) {
    alert(err.message);
    btn.disabled = false;
    btn.textContent = 'Generate Scene Prompts';
  }
}

async function handleAssetsUpload(files) {
  if (!files.length || !currentProject) return;

  const fd = new FormData();
  for (const f of files) fd.append('files', f);

  try {
    await api('POST', `/projects/${currentProject.id}/assets`, fd, true);
    loadAssetsStatus();
  } catch (err) {
    alert(err.message);
  }
}


async function handleCompose() {
  const btn = document.getElementById('compose-btn');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Composing...';

  const bounce = document.getElementById('bounce-check')?.checked || false;

  try {
    currentProject = await api('POST', `/projects/${currentProject.id}/compose`, { bounce });
    renderProject();
  } catch (err) {
    alert(err.message);
    btn.disabled = false;
    btn.textContent = 'Compose Video';
  }
}

async function deleteProject(id) {
  if (!confirm('Delete this project?')) return;
  try {
    await api('DELETE', `/projects/${id}`);
    loadDashboard();
  } catch (err) {
    alert(err.message);
  }
}

// --- Dropzone ---

function setupDropzone(id, handler) {
  setTimeout(() => {
    const el = document.getElementById(id);
    if (!el || el._dz) return;
    el._dz = true;
    const input = el.querySelector('input[type=file]');

    el.addEventListener('click', (e) => {
      if (e.target === input) return;
      input.click();
    });
    input.addEventListener('change', () => {
      if (input.files.length) handler(Array.from(input.files));
    });
    el.addEventListener('dragover', (e) => { e.preventDefault(); el.classList.add('dragover'); });
    el.addEventListener('dragleave', () => el.classList.remove('dragover'));
    el.addEventListener('drop', (e) => {
      e.preventDefault();
      el.classList.remove('dragover');
      handler(Array.from(e.dataTransfer.files));
    });
  }, 0);
}

// --- Utility ---

function esc(s) {
  if (!s) return '';
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

function attr(s) {
  if (!s) return '';
  return String(s).replace(/&/g, '&amp;').replace(/"/g, '&quot;');
}

function copyText(btn) {
  const row = btn.closest('[data-copy]');
  if (!row) return;
  const text = row.dataset.copy;
  navigator.clipboard.writeText(text).then(() => {
    btn.style.color = 'var(--t1)';
    setTimeout(() => { btn.style.color = ''; }, 1400);
  });
}

// --- Toggle ---

// --- Tab switching ---

let currentTab = 'shorts';

function switchTab(tab) {
  currentTab = tab;
  document.querySelectorAll('.ntab').forEach(t => t.classList.remove('on'));
  const activeTab = document.querySelector(`.ntab[onclick="switchTab('${tab}')"]`);
  if (activeTab) activeTab.classList.add('on');

  document.getElementById('view-dashboard').classList.add('hidden');
  document.getElementById('view-project').classList.add('hidden');
  document.getElementById('view-editor')?.classList.add('hidden');

  if (tab === 'shorts') {
    loadDashboard();
  } else if (tab === 'editor') {
    showEditor();
  }
}

// --- Editor ---

let editorSongs = [];
let editorImages = [];

function showEditor() {
  document.getElementById('view-editor').classList.remove('hidden');
  document.getElementById('nav-right').innerHTML = '';

  editorSongs = [];
  editorImages = [];
  renderEditorFiles();
  updateEditorBtn();
  loadEditorHistory();

  setupDropzone('editor-songs-dropzone', (files) => {
    editorSongs.push(...files);
    renderEditorFiles();
    updateEditorBtn();
  });
  setupDropzone('editor-images-dropzone', (files) => {
    editorImages.push(...files);
    renderEditorFiles();
    updateEditorBtn();
  });
}

function renderEditorFiles() {
  const songsList = document.getElementById('editor-songs-list');
  const imagesList = document.getElementById('editor-images-list');

  songsList.innerHTML = editorSongs.map((f, i) => `
    <div class="editor-file-tag">
      <span>${f.name}</span>
      <button class="remove-btn" onclick="removeEditorFile('songs', ${i})">&times;</button>
    </div>
  `).join('');

  imagesList.innerHTML = editorImages.map((f, i) => `
    <div class="editor-file-tag">
      <span>${f.name}</span>
      <button class="remove-btn" onclick="removeEditorFile('images', ${i})">&times;</button>
    </div>
  `).join('');
}

function removeEditorFile(type, index) {
  if (type === 'songs') editorSongs.splice(index, 1);
  else editorImages.splice(index, 1);
  renderEditorFiles();
  updateEditorBtn();
}

function updateEditorBtn() {
  const btn = document.getElementById('editor-compose-btn');
  btn.disabled = editorSongs.length === 0 || editorImages.length === 0;
}

async function handleEditorCompose() {
  const btn = document.getElementById('editor-compose-btn');
  const status = document.getElementById('editor-status');

  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Composing...';
  status.textContent = `Processing ${editorSongs.length} song(s) × ${editorImages.length} image(s)...`;

  const fd = new FormData();
  for (const f of editorSongs) fd.append('songs', f);
  for (const f of editorImages) fd.append('images', f);

  try {
    const result = await api('POST', '/editor/compose', fd, true);
    status.textContent = '';
    renderEditorResults(result.files);
  } catch (err) {
    status.textContent = '';
    alert(err.message);
  } finally {
    btn.disabled = false;
    btn.textContent = 'Compose Videos';
  }
}

function renderEditorResults(files) {
  const el = document.getElementById('editor-results');
  if (!files.length) {
    el.innerHTML = '<div class="text-sm text-3">No output.</div>';
    return;
  }
  el.innerHTML = `
    <div class="section-title mb-12">Output</div>
    ${files.map(f => `
      <div class="editor-result-item">
        <span class="editor-result-name">${f}</span>
        <a href="/api/editor/download/${f}" class="btn btn-primary btn-sm" download>Download</a>
      </div>
    `).join('')}
  `;
}

async function loadEditorHistory() {
  try {
    const data = await api('GET', '/editor/files');
    if (data.files.length) renderEditorResults(data.files);
  } catch (_) {}
}

// --- Substyle ---

const SHRANZ_ALIASES = ['shranz', 'schranz', 'hard techno', 'hardtechno', 'hard-techno', 'dark shranz', 'new shrantz', 'new shranz'];
let substyleCache = null;

function isShranzGenre(genre) {
  const g = (genre || '').toLowerCase().trim();
  return SHRANZ_ALIASES.some(a => g.includes(a));
}

async function loadSubstyles() {
  if (substyleCache) return substyleCache;
  try {
    substyleCache = await api('GET', '/substyles');
  } catch (_) {
    substyleCache = [];
  }
  return substyleCache;
}

async function updateSubstyleVisibility() {
  const genreInput = document.querySelector('#create-form [name=genre]');
  const group = document.getElementById('substyle-group');
  const select = document.getElementById('substyle-select');
  const hint = document.getElementById('substyle-hint');
  if (!genreInput || !group) return;

  const show = isShranzGenre(genreInput.value);
  group.classList.toggle('hidden', !show);

  if (show && select.options.length <= 1) {
    const substyles = await loadSubstyles();
    select.innerHTML = '<option value="">Auto (avoid recent)</option>';
    for (const s of substyles) {
      const used = s.used_count ? ` (x${s.used_count})` : '';
      const opt = document.createElement('option');
      opt.value = s.name;
      opt.textContent = `${s.label} [${s.bpm_range[0]}-${s.bpm_range[1]} BPM]${used}`;
      select.appendChild(opt);
    }
  }

  if (show) {
    select.addEventListener('change', () => {
      const substyles = substyleCache || [];
      const selected = substyles.find(s => s.name === select.value);
      hint.textContent = selected ? selected.mood : '';
    }, { once: false });
  }
}

// --- Init ---

document.addEventListener('DOMContentLoaded', () => {
  // Genre input change → toggle substyle selector
  const observer = new MutationObserver(() => {
    const genreInput = document.querySelector('#create-form [name=genre]');
    if (genreInput && !genreInput._substyleWired) {
      genreInput._substyleWired = true;
      genreInput.addEventListener('input', updateSubstyleVisibility);
    }
  });
  observer.observe(document.body, { childList: true, subtree: true });
});

loadDashboard();
