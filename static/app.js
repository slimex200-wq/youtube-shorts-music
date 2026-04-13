/* YouTube Shorts Music — Frontend */

const API = '/api';
const SETTINGS_BTN = '<button class="nav-settings-btn" onclick="showSettingsModal()" title="Settings"><svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M6.5 1.5L6.8 3.1a5 5 0 011.4.6l1.3-.9 1.4 1.4-.9 1.3a5 5 0 01.6 1.4l1.6.3v2l-1.6.3a5 5 0 01-.6 1.4l.9 1.3-1.4 1.4-1.3-.9a5 5 0 01-1.4.6L9.5 14.5h-2l-.3-1.6a5 5 0 01-1.4-.6l-1.3.9-1.4-1.4.9-1.3a5 5 0 01-.6-1.4L1.5 9.5v-2l1.6-.3a5 5 0 01.6-1.4l-.9-1.3 1.4-1.4 1.3.9a5 5 0 011.4-.6L6.5 1.5z" stroke="currentColor" stroke-width="1.2"/><circle cx="8.5" cy="8.5" r="2" stroke="currentColor" stroke-width="1.2"/></svg></button>';
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
  type: '',     // '' | 'shorts' | 'video'
  sort: 'newest',  // 'newest' | 'oldest' | 'views' | 'genre'
};
let saveTimers = {}; // per-card debounce timers for notes/title_lock
let expandedCards = new Set(); // track which cards are expanded

async function loadDashboard() {
  document.getElementById('view-dashboard').classList.remove('hidden');
  document.getElementById('view-project').classList.add('hidden');

  // Update nav-right for dashboard
  document.getElementById('nav-right').innerHTML = `
    <label class="lite-toggle"><input type="checkbox" ${isLiteMode() ? 'checked' : ''} onchange="handleLiteToggle(this.checked)"><span>Lite</span></label>
    <button class="btn btn-s" id="sync-yt-btn" onclick="handleYouTubeSync()">YouTube 동기화</button>
    <button class="btn btn-p" onclick="showCreateModal()">+ 새 프로젝트</button>
    ${SETTINGS_BTN}
  `;
  currentProject = null;
  const list = document.getElementById('project-list');
  list.innerHTML = '<div class="loading-overlay"><div class="spinner"></div></div>';
  try {
    dashboardProjects = await api('GET', '/projects');
    renderProjectList();
  } catch (e) {
    list.innerHTML = `<div style="text-align:center;padding:40px;color:var(--error)">${esc(e.message)}</div>`;
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

function projectIsShorts(p) {
  return (p.aspect_ratio || '9:16') === '9:16';
}

function filterProjects() {
  const q = dashboardFilters.query.trim().toLowerCase();
  const wantMoods = dashboardFilters.moods;
  const wantSubstyle = dashboardFilters.substyle;
  const wantType = dashboardFilters.type;
  const sortKey = dashboardFilters.sort;

  const filtered = dashboardProjects.filter(p => {
    if (wantType === 'shorts' && !projectIsShorts(p)) return false;
    if (wantType === 'video' && projectIsShorts(p)) return false;
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

  filtered.sort((a, b) => {
    if (sortKey === 'oldest') return (a.created_at || '').localeCompare(b.created_at || '');
    if (sortKey === 'views') return ((b.youtube_stats || {}).views || 0) - ((a.youtube_stats || {}).views || 0);
    if (sortKey === 'genre') return (a.genre || '').localeCompare(b.genre || '');
    // newest (default)
    return (b.created_at || '').localeCompare(a.created_at || '');
  });

  return filtered;
}

async function renderProjectList() {
  const list = document.getElementById('project-list');
  if (!moodsCache) {
    try { moodsCache = await api('GET', '/tags/moods'); }
    catch { moodsCache = []; }
  }
  if (!dashboardProjects.length) {
    list.innerHTML = `
      <div style="text-align:center;padding:60px 20px;color:var(--t3)">
        <div style="font-size:20px;font-weight:600;color:var(--t1);margin-bottom:12px">Welcome to TuneBoard</div>
        <div style="font-size:13px;color:var(--t2);margin-bottom:20px;max-width:400px;margin-left:auto;margin-right:auto">
          YouTube Shorts 음악 채널을 위한 콘텐츠 라이브러리입니다.<br>
          시작하려면 설정에서 API 키를 입력하세요.
        </div>
        <div style="display:flex;gap:8px;justify-content:center">
          <button class="btn btn-p" onclick="showSettingsModal()">Settings</button>
          <button class="btn btn-s" onclick="showCreateModal()">New Project</button>
        </div>
      </div>`;
    return;
  }
  const filtered = filterProjects();
  const shorts = filtered.filter(p => projectIsShorts(p));
  const videos = filtered.filter(p => !projectIsShorts(p));

  const shortsHtml = shorts.length
    ? `<div class="shorts-grid">${shorts.map(p => renderShortsGridCard(p)).join('')}</div>`
    : (videos.length ? '' : '<div style="padding:40px 20px;text-align:center;color:var(--t3)">필터와 일치하는 프로젝트가 없습니다.</div>');

  const videosHtml = videos.length
    ? videos.map(p => renderVideoCard(p)).join('')
    : '';

  const shortsSection = shorts.length || !videos.length ? `
    <div class="section-hdr" onclick="toggleSection('shorts-section', this)">
      <div class="section-accent accent-shorts"></div>
      <span class="section-hdr-label">Shorts</span>
      <span class="section-hdr-count">${shorts.length}</span>
      <div class="section-hdr-line"></div>
      <span class="section-hdr-chevron">&#9662;</span>
    </div>
    <div id="shorts-section">${shortsHtml}</div>
  ` : '';

  const videosSection = videos.length ? `
    <div class="section-hdr" onclick="toggleSection('videos-section', this)" style="margin-top:32px">
      <div class="section-accent accent-video"></div>
      <span class="section-hdr-label">Videos</span>
      <span class="section-hdr-count">${videos.length}</span>
      <div class="section-hdr-line"></div>
      <span class="section-hdr-chevron">&#9662;</span>
    </div>
    <div id="videos-section">${videosHtml}</div>
  ` : '';

  list.innerHTML = renderStatsBar() + renderFilterBar(filtered.length, dashboardProjects.length) + shortsSection + videosSection;
}

function toggleSection(id, hdr) {
  const el = document.getElementById(id);
  const chevron = hdr.querySelector('.section-hdr-chevron');
  if (el.style.display === 'none') {
    el.style.display = '';
    chevron.classList.remove('collapsed');
  } else {
    el.style.display = 'none';
    chevron.classList.add('collapsed');
  }
}

function renderFilterBar(matchCount, totalCount) {
  const moodChips = (moodsCache || []).map(m => {
    const on = dashboardFilters.moods.has(m.name);
    return `<button class="mchip ${on ? 'on' : ''}" data-m="${m.name}" onclick="toggleFilterMood('${m.name}')" title="${esc(m.description)}">${esc(m.label)}</button>`;
  }).join('');

  const substyles = collectSubstyles();
  const substyleOptions = ['<option value="">전체 장르</option>']
    .concat(substyles.map(s =>
      `<option value="${attr(s)}" ${dashboardFilters.substyle === s ? 'selected' : ''}>${esc(s)}</option>`
    )).join('');

  const hasFilter = dashboardFilters.query || dashboardFilters.moods.size || dashboardFilters.substyle;

  const sortOptions = [
    ['newest', '최신순'], ['oldest', '오래된순'], ['views', '조회수순'], ['genre', '장르순']
  ].map(([k, l]) =>
    `<option value="${k}" ${dashboardFilters.sort === k ? 'selected' : ''}>${l}</option>`
  ).join('');

  return `
    <div class="filter-wrap">
      <div class="filter-row">
        <div class="filter-search-wrap">
          <svg width="12" height="12" viewBox="0 0 16 16" fill="none"><circle cx="6.5" cy="6.5" r="4.5" stroke="currentColor" stroke-width="1.5"/><path d="M10 10L14 14" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
          <input class="filter-search" type="text" placeholder="트랙, 장르, 무드 검색..."
                 value="${attr(dashboardFilters.query)}"
                 oninput="handleDashboardSearch(this.value)">
        </div>
        <select class="sort-select" onchange="handleSort(this.value)">${sortOptions}</select>
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

function handleSort(value) {
  dashboardFilters.sort = value;
  renderProjectList();
}

function clearFilters() {
  dashboardFilters = { query: '', moods: new Set(), substyle: '', type: '', sort: 'newest' };
  renderProjectList();
}

// --- Stats bar ---

function renderStatsBar() {
  const total = dashboardProjects.length;
  if (!total) return '';
  let totalViews = 0;
  let synced = 0;
  let shortsCount = 0;
  let videosCount = 0;
  const genreCounts = {};
  for (const p of dashboardProjects) {
    totalViews += (p.youtube_stats || {}).views || 0;
    if (p.youtube_video_id) synced++;
    if (projectIsShorts(p)) shortsCount++; else videosCount++;
    const g = p.genre || 'unknown';
    genreCounts[g] = (genreCounts[g] || 0) + 1;
  }
  const topGenre = Object.entries(genreCounts).sort((a,b) => b[1]-a[1])[0];
  return `
    <div class="stats-strip">
      <div class="stat-item"><span class="stat-val">${total}</span><span class="stat-lbl">프로젝트</span></div>
      <div class="stat-item"><span class="stat-lbl">Shorts</span><span class="stat-val">${shortsCount}</span></div>
      ${videosCount ? `<div class="stat-item"><span class="stat-lbl">Videos</span><span class="stat-val">${videosCount}</span></div>` : ''}
      ${totalViews ? `<div class="stat-item"><span class="stat-val">${totalViews.toLocaleString()}</span><span class="stat-lbl">총 조회수</span></div>` : ''}
      ${synced ? `<div class="stat-item"><span class="stat-val">${synced}</span><span class="stat-lbl">동기화</span></div>` : ''}
      ${topGenre ? `<div class="stat-item"><span class="stat-lbl">인기 장르</span><span class="stat-badge">${esc(topGenre[0])}</span></div>` : ''}
    </div>
  `;
}

// --- Shorts grid card ---

function renderShortsGridCard(p) {
  const title = p.title_lock || (p.metadata && p.metadata.title) || p.id;
  const sp = p.suno_prompt || {};
  const meta = p.metadata || {};
  const stats = p.youtube_stats || {};
  const isGold = (stats.views || 0) >= 1000;
  const dur = p.duration_sec ? `${Math.round(p.duration_sec)}s` : '';

  const thumbSrc = p.thumbnail_url
    || ((p.visual_refs && p.visual_refs.length)
        ? `/api/projects/${p.id}/refs/${encodeURIComponent(p.visual_refs[0])}`
        : '');
  const thumbHtml = thumbSrc
    ? `<img src="${thumbSrc}" alt="" loading="lazy">`
    : `<div class="sgcard-thumb-ph">${esc(p.genre).slice(0,6).toUpperCase()}</div>`;

  const moodDots = (p.mood_tags || []).map(m => {
    const colorMap = {crimson:'var(--crimson)',void:'var(--void)',frost:'var(--frost)',steel:'var(--steel)',ember:'var(--ember)',shadow:'var(--shadow)'};
    return `<span class="mdot" style="background:${colorMap[m] || 'var(--acc)'}"></span>`;
  }).join('');

  const viewsText = stats.views ? Number(stats.views).toLocaleString() : '';

  return `
    <div class="sgcard ${isGold ? 'gold' : ''}" onclick="openProject('${p.id}')">
      <div class="sgcard-thumb">
        ${thumbHtml}
        ${dur ? `<span class="sgcard-dur">${dur}</span>` : ''}
        ${viewsText ? `<span class="sgcard-views ${isGold ? 'hot' : ''}">${viewsText}</span>` : ''}
        ${moodDots ? `<div class="sgcard-moods">${moodDots}</div>` : ''}
        ${p.youtube_video_id ? `<button class="sgcard-play" onclick="event.stopPropagation();showMiniPlayer('${attr(p.youtube_video_id)}',true)" title="Preview"><svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><path d="M4 2.5v11l9-5.5z"/></svg></button>` : ''}
      </div>
      <div class="sgcard-body">
        <div class="sgcard-title">${esc(title)}</div>
        ${sp.style
          ? `<div class="sgcard-suno">${esc(sp.style)}</div>`
          : (meta.description ? `<div class="sgcard-suno">${esc(meta.description)}</div>` : '')}
        <div class="sgcard-meta">
          <span class="sgcard-genre">${esc(p.genre)}</span>
          <div class="sgcard-copy">
            ${sp.style ? `<button class="cb" data-copy="${attr(sp.style)}" onclick="event.stopPropagation();navigator.clipboard.writeText(this.dataset.copy)">S</button>` : ''}
            ${meta.title ? `<button class="cb" data-copy="${attr(meta.title)}" onclick="event.stopPropagation();navigator.clipboard.writeText(this.dataset.copy)">T</button>` : ''}
            ${meta.first_comment ? `<button class="cb" data-copy="${attr(meta.first_comment)}" onclick="event.stopPropagation();navigator.clipboard.writeText(this.dataset.copy)">1</button>` : ''}
          </div>
        </div>
      </div>
    </div>
  `;
}

// --- Video list card ---

function renderVideoCard(p) {
  const title = p.title_lock || (p.metadata && p.metadata.title) || p.id;
  const sp = p.suno_prompt || {};
  const meta = p.metadata || {};
  const stats = p.youtube_stats || {};
  const dur = p.duration_sec ? formatDuration(p.duration_sec) : '';
  const sceneCount = (p.scenes || []).length;

  const thumbSrc = p.thumbnail_url
    || ((p.visual_refs && p.visual_refs.length)
        ? `/api/projects/${p.id}/refs/${encodeURIComponent(p.visual_refs[0])}`
        : '');
  const thumbHtml = thumbSrc
    ? `<img src="${thumbSrc}" alt="" loading="lazy">`
    : `<div style="width:100%;height:100%;display:flex;align-items:center;justify-content:center;font-family:var(--fm);font-size:9px;color:var(--t4)">16:9</div>`;

  const moodChips = (p.mood_tags || []).map(m => {
    const colorMap = {crimson:'var(--crimson)',void:'var(--void)',frost:'var(--frost)',steel:'var(--steel)',ember:'var(--ember)',shadow:'var(--shadow)'};
    return `<span class="vcard-chip" style="border-color:${colorMap[m] || 'var(--b2)'};color:${colorMap[m] || 'var(--t3)'}">${esc(m)}</span>`;
  }).join('');

  const desc = meta.description || '';

  return `
    <div class="vcard" onclick="openProject('${p.id}')">
      <div class="vcard-thumb">
        ${thumbHtml}
        ${dur ? `<span class="vcard-dur">${dur}</span>` : ''}
        ${p.youtube_video_id ? `<button class="sgcard-play" onclick="event.stopPropagation();showMiniPlayer('${attr(p.youtube_video_id)}',false)" title="Preview"><svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><path d="M4 2.5v11l9-5.5z"/></svg></button>` : ''}
      </div>
      <div class="vcard-body">
        <div class="vcard-title">${esc(title)}</div>
        <div class="vcard-meta">
          <code>${esc(p.genre)}</code>
          ${sceneCount ? `<span>${sceneCount} scenes</span>` : ''}
          <span>${p.created_at ? formatDate(p.created_at) : ''}</span>
        </div>
        ${sp.style ? `<div class="vcard-desc" style="color:var(--t2);font-family:var(--fm)">${esc(sp.style)}</div>` : ''}
        ${desc ? `<div class="vcard-desc">${esc(desc)}</div>` : ''}
        ${moodChips ? `<div class="vcard-chips">${moodChips}</div>` : ''}
        <div class="vcard-stats">
          <span class="vcard-stat"><strong>${stats.views ? Number(stats.views).toLocaleString() : '—'}</strong> views</span>
          <span class="vcard-stat"><strong>${stats.likes || '—'}</strong> likes</span>
        </div>
      </div>
      <div class="vcard-actions">
        ${meta.title ? `<button class="cb" data-copy="${attr(meta.title)}" onclick="event.stopPropagation();navigator.clipboard.writeText(this.dataset.copy)">Copy Meta</button>` : ''}
      </div>
    </div>
  `;
}

function formatDuration(sec) {
  const m = Math.floor(sec / 60);
  const s = Math.round(sec % 60);
  return `${m}:${String(s).padStart(2, '0')}`;
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
        ${sp.style ? `<button class="cb" data-copy="${attr(sp.style)}" onclick="event.stopPropagation();navigator.clipboard.writeText(this.dataset.copy)">Style</button>` : ''}
        ${meta.title ? `<button class="cb" data-copy="${attr(meta.title)}" onclick="event.stopPropagation();navigator.clipboard.writeText(this.dataset.copy)">Title</button>` : ''}
        ${meta.first_comment ? `<button class="cb" data-copy="${attr(meta.first_comment)}" onclick="event.stopPropagation();navigator.clipboard.writeText(this.dataset.copy)">1st</button>` : ''}
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
  btn.innerHTML = '<span class="spinner"></span> 동기화 중...';
  showToast('YouTube 채널 데이터 동기화 시작...', 'info');
  try {
    const result = await api('POST', '/sync/youtube');
    const msg = `동기화 완료 — ${result.synced}개 신규, ${result.updated}개 업데이트`;
    showToast(msg, 'success');
    btn.textContent = 'YouTube 동기화';
    btn.disabled = false;
    loadDashboard();
  } catch (e) {
    showToast(`동기화 실패: ${e.message}`, 'error');
    btn.textContent = 'YouTube 동기화';
    btn.disabled = false;
  }
}

function showToast(message, type) {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    document.body.appendChild(container);
  }
  const toast = document.createElement('div');
  toast.className = `toast toast-${type || 'info'}`;
  toast.textContent = message;
  container.appendChild(toast);
  requestAnimationFrame(() => toast.classList.add('show'));
  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

function showMiniPlayer(videoId, isShorts) {
  // Validate YouTube video ID format (11 alphanumeric + hyphen + underscore)
  if (!/^[a-zA-Z0-9_-]{11}$/.test(videoId)) return;

  const existing = document.getElementById('mini-player-overlay');
  if (existing) existing.remove();

  const w = isShorts ? 315 : 560;
  const h = isShorts ? 560 : 315;

  const overlay = document.createElement('div');
  overlay.id = 'mini-player-overlay';
  overlay.className = 'mini-player-overlay';
  overlay.onclick = (e) => { if (e.target === overlay) overlay.remove(); };
  overlay.innerHTML = `
    <div class="mini-player" style="width:${w}px;max-width:95vw">
      <button class="mini-player-close" onclick="this.closest('.mini-player-overlay').remove()">&times;</button>
      <iframe
        width="${w}" height="${h}"
        src="https://www.youtube.com/embed/${encodeURIComponent(videoId)}?autoplay=1"
        frameborder="0"
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
        allowfullscreen
        style="border-radius:8px;width:100%;aspect-ratio:${isShorts ? '9/16' : '16/9'};height:auto"
      ></iframe>
    </div>
  `;
  document.body.appendChild(overlay);
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

// --- Settings ---

async function showSettingsModal() {
  document.getElementById('settings-modal').classList.remove('hidden');
  document.getElementById('settings-status').textContent = '';
  try {
    const settings = await api('GET', '/settings');
    const form = document.getElementById('settings-form');
    for (const [key, val] of Object.entries(settings)) {
      const input = form.querySelector(`[name="${key}"]`);
      if (input) input.value = val || '';
    }
  } catch (e) {
    document.getElementById('settings-status').textContent = 'Failed to load settings';
  }
}

function hideSettingsModal() {
  document.getElementById('settings-modal').classList.add('hidden');
}

async function handleSaveSettings(e) {
  e.preventDefault();
  const form = e.target;
  const fd = new FormData(form);
  const settings = {};
  for (const [k, v] of fd.entries()) settings[k] = v;

  const status = document.getElementById('settings-status');
  try {
    await api('PUT', '/settings', { settings });
    status.textContent = 'Saved!';
    status.style.color = 'var(--acc)';
    setTimeout(() => hideSettingsModal(), 1000);
  } catch (err) {
    status.textContent = err.message;
    status.style.color = 'var(--error)';
  }
}

// --- Create Modal ---

let genreDefaults = null;

async function loadGenreDefaults() {
  if (!genreDefaults) {
    try { genreDefaults = await api('GET', '/genres'); } catch { genreDefaults = {}; }
  }
}

function autoSetInstrumental(genre) {
  if (!genreDefaults || !genre) return;
  const g = genre.toLowerCase().trim();
  const info = genreDefaults[g];
  const instrumental = info ? info.default_instrumental : true;
  const checkbox = document.querySelector('#create-form [name=instrumental]');
  if (checkbox) checkbox.checked = instrumental;
}

function showCreateModal() {
  document.getElementById('create-modal').classList.remove('hidden');
  const genreInput = document.querySelector('#create-form [name=genre]');
  genreInput.focus();
  loadGenreDefaults();
  // Populate genre presets
  const presetsEl = document.getElementById('genre-presets');
  if (presetsEl) {
    const genres = {};
    for (const p of dashboardProjects) {
      if (p.genre) genres[p.genre] = (genres[p.genre] || 0) + 1;
    }
    const sorted = Object.entries(genres).sort((a,b) => b[1]-a[1]).slice(0, 8);
    presetsEl.innerHTML = sorted.map(([g]) =>
      `<button type="button" class="gpchip" onclick="this.parentElement.querySelectorAll('.gpchip').forEach(c=>c.classList.remove('on'));this.classList.add('on');document.querySelector('#create-form [name=genre]').value='${esc(g)}';updateSubstyleVisibility();autoSetInstrumental('${esc(g)}')">${esc(g)}</button>`
    ).join('');
  }
  if (!genreInput._substyleWired) {
    genreInput._substyleWired = true;
    genreInput.addEventListener('input', () => { updateSubstyleVisibility(); autoSetInstrumental(genreInput.value); });
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
  const substyle = fd.get('substyle') || null;
  const aspect_ratio = fd.get('aspect_ratio') || '9:16';
  const model = fd.get('model') || 'sonnet';
  const instrumental = !!document.querySelector('#create-form [name=instrumental]')?.checked;
  const body = {
    genre: fd.get('genre'),
    substyle,
    aspect_ratio,
    model,
    instrumental,
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
  { key: 'create', label: 'Create', sunoOnly: true },
  { key: 'metadata', label: 'Metadata' },
  { key: 'library', label: 'Library' },
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

function visibleSteps(p) {
  const hasSuno = p && p.suno_prompt;
  return STEPS.filter(s => {
    if (s.fullOnly && isLiteMode()) return false;
    if (s.sunoOnly && !hasSuno) return false;
    return true;
  });
}

// Tag caches
let moodsCache = null;
let motifsCache = null;

async function openProject(id) {
  document.getElementById('view-dashboard').classList.add('hidden');
  document.getElementById('view-project').classList.remove('hidden');


  // nav-right gets back + lite toggle + clone + delete
  document.getElementById('nav-right').innerHTML =
    `<button class="btn btn-s" onclick="switchTab('shorts')">← 목록</button>${renderLiteToggle()}<button class="btn btn-s" onclick="cloneProject('${id}')">복제</button><button class="btn btn-s" style="color:var(--error)" onclick="deleteProject('${id}')">삭제</button>${SETTINGS_BTN}`;

  const content = document.getElementById('step-content');
  content.innerHTML = '<div class="loading-overlay"><div class="spinner"></div></div>';
  metadataAcknowledged = false;
  libraryAcknowledged = false;

  try {
    currentProject = await api('GET', `/projects/${id}`);
    const topTitle = currentProject.title_lock || (currentProject.metadata && currentProject.metadata.title) || currentProject.id;
    document.getElementById('project-topbar-title').textContent = topTitle;
    renderProject();
  } catch (err) {
    content.innerHTML = `<div style="text-align:center;padding:40px;color:var(--error)">${esc(err.message)}</div>`;
  }
}

function getActiveStep(p) {
  const lite = isLiteMode();
  const hasSuno = !!p.suno_prompt;
  if (!lite && p.steps_completed.includes('compose')) return 'compose';
  if (!lite && p.steps_completed.includes('prompts')) return 'assets';
  if (!lite && p.steps_completed.includes('music')) return 'prompts';
  if (!lite && libraryAcknowledged && p.steps_completed.includes('create')) return 'music';
  if (metadataAcknowledged && p.steps_completed.includes('create')) return 'library';
  if (p.steps_completed.includes('create')) return hasSuno ? 'metadata' : 'metadata';
  return hasSuno ? 'create' : 'metadata';
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
  const steps = visibleSteps(p);
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
  } else if (active === 'metadata') {
    el.innerHTML = renderStepMetadata(p);
  } else if (active === 'library') {
    renderStepLibrary(p);
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

async function handleRegenSuno() {
  if (!currentProject) return;
  const btn = document.getElementById('regen-suno-btn');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Generating...';
  try {
    currentProject = await api('POST', `/projects/${currentProject.id}/regenerate-suno`);
    renderProject();
    showToast('새 변주 생성 완료', 'success');
  } catch (err) {
    alert(err.message);
  } finally {
    btn.disabled = false;
    btn.textContent = '변주 생성';
  }
}

async function restoreSuno(index) {
  if (!currentProject) return;
  try {
    currentProject = await api('POST', `/projects/${currentProject.id}/restore-suno/${index}`);
    renderProject();
    showToast('이전 프롬프트 복원', 'success');
  } catch (err) { alert(err.message); }
}

function renderSunoHistory(p) {
  const history = p.suno_prompt_history || [];
  if (!history.length) return '';
  return `
    <div class="suno-history mt-12">
      <div class="prompt-card-title" style="margin-bottom:8px">History (${history.length})</div>
      ${history.map((h, i) => `
        <div class="suno-hist-item">
          <span class="text-sm text-2">${esc(h.title_suggestion || h.substyle || 'variant ' + (i+1))}</span>
          <span class="text-sm text-3" style="flex:1;margin-left:8px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc((h.style || '').slice(0, 60))}</span>
          <button class="btn btn-s btn-sm" onclick="restoreSuno(${i})">복원</button>
        </div>
      `).join('')}
    </div>
  `;
}

function renderStepCreate(p) {
  if (!p.suno_prompt) {
    return `<div class="card"><div class="text-2 text-sm">Suno prompt not generated. Check API key.</div></div>`;
  }
  return renderSunoPrompt(p)
    + `<div class="mt-12"><button class="btn btn-s" id="regen-suno-btn" onclick="handleRegenSuno()">변주 생성</button></div>`
    + renderSunoHistory(p)
    + renderVideoPrompts(p);
}

function renderVideoPrompts(p) {
  if (!p.video_prompts || !p.video_prompts.length) return '';
  const copyIcon = '<svg width="12" height="12" viewBox="0 0 16 16" fill="none"><rect x="5" y="5" width="9" height="9" rx="1.5" stroke="currentColor" stroke-width="1.5"/><path d="M11 5V3.5A1.5 1.5 0 009.5 2h-6A1.5 1.5 0 002 3.5v6A1.5 1.5 0 003.5 11H5" stroke="currentColor" stroke-width="1.5"/></svg>';

  const cards = p.video_prompts.map(vp => {
    const strength = vp.motion_strength || 3;
    const dots = Array.from({length: 5}, (_, i) =>
      `<span class="hf-dot ${i < strength ? 'on' : ''}"></span>`
    ).join('');

    return `
      <div class="hf-card" data-copy="${attr(vp.prompt)}">
        <div class="hf-card-head">
          <span class="hf-card-type" data-type="${vp.type}">${esc(vp.label || vp.type)}</span>
          <div class="hf-card-meta">
            <span>${esc(vp.camera || '')}</span>
            <span>${esc(vp.duration || '5s')}</span>
          </div>
        </div>
        <div class="hf-card-prompt">${esc(vp.prompt)}</div>
        <div class="hf-card-foot">
          <div class="hf-strength" title="Motion Strength ${strength}">${dots}<span class="text-sm text-3" style="margin-left:4px">MS ${strength}</span></div>
          <button class="copy-btn" onclick="copyText(this)">${copyIcon} Copy</button>
        </div>
      </div>
    `;
  }).join('');

  return `
    <div class="mt-16">
      <div class="prompt-card-title" style="margin-bottom:10px">Video Prompts</div>
      <div class="hf-output">${cards}</div>
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
    <div class="suno-workflow mt-16 mb-12">
      <div class="flex-between" style="margin-bottom:8px">
        <div class="prompt-card-title">Suno Workflow</div>
        <a href="https://suno.com/create" target="_blank" class="btn btn-p btn-sm">Open Suno</a>
      </div>
      <div class="suno-wf-steps">
        <button class="btn btn-s btn-sm suno-wf-btn" onclick="navigator.clipboard.writeText(${attr(JSON.stringify(sp.style))});this.textContent='Copied!';setTimeout(()=>this.textContent='1. Style',1000)">1. Style</button>
        <button class="btn btn-s btn-sm suno-wf-btn" onclick="navigator.clipboard.writeText(${attr(JSON.stringify(sp.prompt))});this.textContent='Copied!';setTimeout(()=>this.textContent='2. Description',1000)">2. Description</button>
        ${sp.lyrics ? `<button class="btn btn-s btn-sm suno-wf-btn" onclick="navigator.clipboard.writeText(${attr(JSON.stringify(sp.lyrics))});this.textContent='Copied!';setTimeout(()=>this.textContent='3. Lyrics',1000)">3. Lyrics</button>` : ''}
        ${sp.exclude_styles ? `<button class="btn btn-s btn-sm suno-wf-btn" onclick="navigator.clipboard.writeText(${attr(JSON.stringify(sp.exclude_styles))});this.textContent='Copied!';setTimeout(()=>this.textContent='${sp.lyrics ? '4' : '3'}. Exclude',1000)">${sp.lyrics ? '4' : '3'}. Exclude</button>` : ''}
      </div>
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
        <div style="display:flex;gap:4px">
          ${currentProject && currentProject.youtube_video_id ? `<button class="btn btn-p btn-sm" onclick="postFirstComment()">게시</button>` : ''}
          <button class="copy-btn" onclick="copyText(this)">Copy</button>
        </div>
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

  const sunoCard = renderSunoCard(p);

  el.innerHTML = `
    ${sunoCard}
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
      <button class="btn btn-secondary" onclick="handleBackToMetadata()">
        &larr; Metadata
      </button>
      <button class="btn btn-primary" onclick="saveLibrary(this)">Save Library</button>
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

async function saveLibrary(btn) {
  const notes = document.getElementById('notes-input').value;
  const titleLock = document.getElementById('title-lock-input').value.trim();
  try {
    currentProject = await api('PATCH', `/projects/${currentProject.id}`, {
      notes,
      title_lock: titleLock,
    });
    if (btn) {
      const prev = btn.textContent;
      btn.textContent = 'Saved';
      setTimeout(() => { btn.textContent = prev; }, 1200);
    }
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

function renderSunoCard(p) {
  if (!p.suno_prompt) return '';
  return renderSunoPrompt(p);
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
          ${p.suno_prompt ? `<button class="btn btn-secondary" onclick="handleBackToCreate()">&larr; Create</button>` : ''}
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
    ${renderYouTubeEmbed(p)}
    ${renderMetadataCard(p.metadata)}
    <div class="mt-16" style="display:flex;gap:8px">
      ${p.suno_prompt ? `<button class="btn btn-secondary" onclick="handleBackToCreate()">&larr; Create</button>` : ''}
      <button class="btn btn-secondary" id="regen-metadata-btn" onclick="handleGenMetadata()">
        Regenerate
      </button>
      <button class="btn btn-primary" onclick="handleAdvanceToLibrary()">
        Next: Library &rarr;
      </button>
      ${p.youtube_video_id ? `<button class="btn btn-s" onclick="analyzeComments()">댓글 분석</button>` : ''}
    </div>
    <div id="comment-analysis"></div>
  `;
}

async function analyzeComments() {
  if (!currentProject) return;
  const el = document.getElementById('comment-analysis');
  el.innerHTML = '<div class="loading-overlay" style="padding:20px"><div class="spinner"></div> 댓글 분석 중...</div>';
  try {
    const data = await api('GET', `/projects/${currentProject.id}/comments`);
    if (!data.analysis) {
      el.innerHTML = '<div class="card mt-12 text-sm text-3">댓글이 없습니다.</div>';
      return;
    }
    const a = data.analysis;
    const themes = (a.top_themes || []).map(t => `<span class="cov-cell used" style="padding:4px 8px;font-size:11px">${esc(t)}</span>`).join('');
    const quotes = (a.notable_quotes || []).map(q => `<div class="text-sm text-2" style="padding:4px 0;border-bottom:1px solid var(--b1)">"${esc(q)}"</div>`).join('');
    el.innerHTML = `
      <div class="card mt-12">
        <div class="flex-between" style="margin-bottom:8px">
          <div class="prompt-card-title">Comment Analysis (${data.comment_count} comments)</div>
          <span class="badge badge-${a.sentiment === 'positive' ? 'composed' : a.sentiment === 'negative' ? 'created' : 'music'}">${esc(a.sentiment)}</span>
        </div>
        <div class="text-sm text-2 mb-12">${esc(a.summary || '')}</div>
        ${themes ? `<div style="display:flex;gap:4px;flex-wrap:wrap;margin-bottom:8px">${themes}</div>` : ''}
        ${quotes ? `<div class="prompt-card-title" style="margin-top:8px;margin-bottom:4px">Notable</div>${quotes}` : ''}
      </div>
    `;
  } catch (err) {
    el.innerHTML = `<div class="card mt-12 text-sm" style="color:var(--error)">${esc(err.message)}</div>`;
  }
}

function renderYouTubeEmbed(p) {
  if (!p.youtube_video_id) return '';
  const isShorts = projectIsShorts(p);
  const w = isShorts ? 270 : 480;
  const h = isShorts ? 480 : 270;
  return `
    <div class="yt-embed mb-12" style="max-width:${w}px">
      <iframe
        width="${w}" height="${h}"
        src="https://www.youtube.com/embed/${p.youtube_video_id}"
        frameborder="0"
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
        allowfullscreen
        style="border-radius:8px;width:100%;aspect-ratio:${isShorts ? '9/16' : '16/9'};height:auto"
      ></iframe>
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
      <div style="display:flex;gap:8px;flex-wrap:wrap">
        <button class="btn btn-primary" id="gen-prompts-btn" onclick="handleGenPrompts()">
          Generate Scene Prompts
        </button>
        <a href="/api/projects/${p.id}/beat-markers.srt" class="btn btn-s" download>Beat Markers (SRT)</a>
        <a href="/api/projects/${p.id}/beat-markers.json" class="btn btn-s" download="${p.id}_beats.json">Beat Data (JSON)</a>
      </div>
      <div class="text-sm text-3 mt-12">SRT를 CapCut에 자막으로 import하면 비트 마커로 사용할 수 있습니다.</div>
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
    content.innerHTML = `<div class="empty-state" style="color:var(--error)">${esc(err.message)}</div>`;
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

function handleBackToCreate() {
  metadataAcknowledged = false;
  libraryAcknowledged = false;
  renderProject();
}

function handleBackToMetadata() {
  libraryAcknowledged = false;
  metadataAcknowledged = false;
  // re-enter metadata by acknowledging nothing
  // getActiveStep will land on metadata since create is completed
  renderProject();
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

async function postFirstComment() {
  if (!currentProject) return;
  if (!confirm('YouTube에 첫 번째 댓글을 게시할까요?')) return;
  try {
    await api('POST', `/projects/${currentProject.id}/comment`);
    showToast('댓글 게시 완료', 'success');
  } catch (err) {
    alert(err.message);
  }
}

async function cloneProject(id) {
  try {
    const cloned = await api('POST', `/projects/${id}/clone`);
    openProject(cloned.id);
    showToast('프로젝트 복제 완료', 'success');
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
  document.getElementById('view-analytics')?.classList.add('hidden');
  if (tab === 'shorts') {
    loadDashboard();
  } else if (tab === 'analytics') {
    showAnalytics();
  }
}

function selectRatio(el, value) {
  el.closest('.form-row,.form-group').querySelectorAll('.ratio-chip').forEach(c => c.classList.remove('on'));
  el.classList.add('on');
  el.querySelector('input').checked = true;
}

function selectModel(el, value) {
  el.closest('.form-group').querySelectorAll('.ratio-chip').forEach(c => c.classList.remove('on'));
  el.classList.add('on');
  el.querySelector('input').checked = true;
}

// --- Analytics (M5 + M6) ---

async function showAnalytics() {
  document.getElementById('view-analytics').classList.remove('hidden');
  document.getElementById('nav-right').innerHTML = SETTINGS_BTN;
  const el = document.getElementById('analytics-content');
  el.innerHTML = '<div class="text-sm text-3" style="padding:40px;text-align:center">Loading...</div>';

  try {
    const [usage, analytics, substyles] = await Promise.all([
      api('GET', '/usage'),
      api('GET', '/analytics'),
      api('GET', '/substyles'),
    ]);
    el.innerHTML = renderUsageSection(usage) + renderAnalyticsSection(analytics) + renderSubstyleCoverage(substyles);
  } catch (e) {
    el.innerHTML = `<div style="padding:40px;color:var(--error)">${esc(e.message)}</div>`;
  }
}

function renderUsageSection(u) {
  const modelRows = Object.entries(u.by_model).map(([m, d]) => `
    <tr>
      <td style="font-weight:600">${esc(m)}</td>
      <td>${d.calls}</td>
      <td>$${d.cost_usd.toFixed(4)}</td>
      <td>${d.input_tokens.toLocaleString()}</td>
      <td>${d.output_tokens.toLocaleString()}</td>
    </tr>
  `).join('');

  const recentRows = u.recent.map(r => `
    <tr>
      <td class="text-3">${r.at ? r.at.slice(5, 16).replace('T', ' ') : ''}</td>
      <td>${esc(r.model || '')}</td>
      <td>$${(r.cost_usd || 0).toFixed(4)}</td>
      <td>${((r.duration_ms || 0) / 1000).toFixed(1)}s</td>
    </tr>
  `).join('');

  return `
    <section>
      <div class="section-header"><span class="section-title">LLM Usage</span></div>
      <div class="stats-strip" style="margin-bottom:16px">
        <div class="stat-item"><span class="stat-val">$${u.total_cost.toFixed(2)}</span><span class="stat-lbl">Total Cost</span></div>
        <div class="stat-item"><span class="stat-val">${u.total_calls}</span><span class="stat-lbl">API Calls</span></div>
        <div class="stat-item"><span class="stat-val">${u.total_input_tokens.toLocaleString()}</span><span class="stat-lbl">Input Tokens</span></div>
        <div class="stat-item"><span class="stat-val">${u.total_output_tokens.toLocaleString()}</span><span class="stat-lbl">Output Tokens</span></div>
      </div>
      <div class="analytics-grid">
        <div class="card">
          <div class="prompt-card-title" style="margin-bottom:8px">Model Breakdown</div>
          <table class="analytics-table">
            <thead><tr><th>Model</th><th>Calls</th><th>Cost</th><th>In</th><th>Out</th></tr></thead>
            <tbody>${modelRows}</tbody>
          </table>
        </div>
        <div class="card">
          <div class="prompt-card-title" style="margin-bottom:8px">Recent Calls</div>
          <table class="analytics-table">
            <thead><tr><th>Time</th><th>Model</th><th>Cost</th><th>Duration</th></tr></thead>
            <tbody>${recentRows}</tbody>
          </table>
        </div>
      </div>
    </section>
  `;
}

function renderAnalyticsSection(a) {
  const genreRows = a.genre_ranking.map(g => `
    <tr>
      <td style="font-weight:600">${esc(g.genre)}</td>
      <td>${g.count}</td>
      <td>${g.views.toLocaleString()}</td>
      <td>${g.avg_views.toLocaleString()}</td>
      <td>${g.likes.toLocaleString()}</td>
    </tr>
  `).join('');

  const substyleRows = a.substyle_ranking.map(s => `
    <tr>
      <td style="font-weight:600">${esc(s.substyle)}</td>
      <td>${s.count}</td>
      <td>${s.views.toLocaleString()}</td>
      <td>${s.avg_views.toLocaleString()}</td>
    </tr>
  `).join('');

  const topRows = a.top_performers.slice(0, 10).map((t, i) => `
    <tr style="cursor:pointer" onclick="openProject('${t.id}')">
      <td class="text-3">${i + 1}</td>
      <td style="font-weight:500;max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(t.title)}</td>
      <td>${esc(t.genre)}</td>
      <td>${t.views.toLocaleString()}</td>
      <td>${t.engagement}%</td>
    </tr>
  `).join('');

  return `
    <section style="margin-top:24px">
      <div class="section-header"><span class="section-title">YouTube Analytics</span></div>
      <div class="analytics-grid">
        <div class="card">
          <div class="prompt-card-title" style="margin-bottom:8px">Genre Performance</div>
          <table class="analytics-table">
            <thead><tr><th>Genre</th><th>Count</th><th>Views</th><th>Avg</th><th>Likes</th></tr></thead>
            <tbody>${genreRows || '<tr><td colspan="5" class="text-3">No data</td></tr>'}</tbody>
          </table>
        </div>
        ${substyleRows ? `
        <div class="card">
          <div class="prompt-card-title" style="margin-bottom:8px">Substyle Performance</div>
          <table class="analytics-table">
            <thead><tr><th>Substyle</th><th>Count</th><th>Views</th><th>Avg</th></tr></thead>
            <tbody>${substyleRows}</tbody>
          </table>
        </div>
        ` : ''}
      </div>
      <div class="card" style="margin-top:16px">
        <div class="prompt-card-title" style="margin-bottom:8px">Top Performers</div>
        <table class="analytics-table">
          <thead><tr><th>#</th><th>Title</th><th>Genre</th><th>Views</th><th>Engagement</th></tr></thead>
          <tbody>${topRows || '<tr><td colspan="5" class="text-3">No data</td></tr>'}</tbody>
        </table>
      </div>
    </section>
  `;
}

function renderSubstyleCoverage(substyles) {
  const unused = substyles.filter(s => s.used_count === 0);
  const cells = substyles.map(s => {
    const used = s.used_count > 0;
    return `<div class="cov-cell ${used ? 'used' : 'unused'}" title="${esc(s.label)} (${s.used_count}x)">
      <span class="cov-name">${esc(s.name.replace(/_/g, ' '))}</span>
      <span class="cov-count">${s.used_count}</span>
    </div>`;
  }).join('');

  return `
    <section style="margin-top:24px">
      <div class="section-header">
        <span class="section-title">Substyle Coverage (${substyles.length - unused.length}/${substyles.length})</span>
        ${unused.length ? `<button class="btn btn-p btn-sm" onclick="batchCreateUnused()">미사용 ${unused.length}개 배치 생성</button>` : ''}
      </div>
      <div class="cov-grid">${cells}</div>
    </section>
  `;
}

async function batchCreateUnused() {
  const substyles = substyleCache || await api('GET', '/substyles');
  const unused = substyles.filter(s => s.used_count === 0).map(s => s.name);
  if (!unused.length) { showToast('모든 substyle 사용됨', 'success'); return; }
  if (!confirm(`미사용 substyle ${unused.length}개로 프로젝트를 배치 생성할까요?\n${unused.join(', ')}`)) return;

  try {
    const result = await api('POST', '/projects/batch', { substyles: unused });
    showToast(`${result.created.length}개 프로젝트 생성 완료`, 'success');
    showAnalytics();
  } catch (err) { alert(err.message); }
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

  if (show && !select._hintWired) {
    select._hintWired = true;
    select.addEventListener('change', () => {
      const substyles = substyleCache || [];
      const selected = substyles.find(s => s.name === select.value);
      hint.textContent = selected ? selected.mood : '';
    });
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
