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

async function loadDashboard() {
  document.getElementById('view-dashboard').classList.remove('hidden');
  document.getElementById('view-project').classList.add('hidden');
  document.getElementById('nav-left').innerHTML = '<span class="nav-title">YouTube Shorts Music</span>';
  document.getElementById('nav-right').innerHTML = '';
  currentProject = null;

  const list = document.getElementById('project-list');
  list.innerHTML = '<div class="loading-overlay"><div class="spinner"></div></div>';

  try {
    const projects = (await api('GET', '/projects')).reverse();
    if (!projects.length) {
      list.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-title">No projects yet</div>
          <div class="text-sm text-3">Create a project to get started</div>
        </div>`;
      return;
    }
    list.innerHTML = projects.map(p => `
      <div class="card card-clickable project-item" onclick="openProject('${p.id}')">
        <div class="project-info">
          <span class="project-id">${p.id}</span>
          <span class="project-meta">
            ${p.genre}
            ${p.bpm ? `&middot; ${p.bpm} BPM` : ''}
            ${p.duration_sec ? `&middot; ${p.duration_sec.toFixed(0)}s` : ''}
          </span>
        </div>
        ${statusBadge(p.status)}
      </div>
    `).join('');
  } catch (e) {
    list.innerHTML = `<div class="empty-state text-sm" style="color:var(--error)">${e.message}</div>`;
  }
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
  { key: 'music', label: 'Music' },
  { key: 'prompts', label: 'Prompts' },
  { key: 'assets', label: 'Assets' },
  { key: 'compose', label: 'Compose' },
];

async function openProject(id) {
  document.getElementById('view-dashboard').classList.add('hidden');
  document.getElementById('view-project').classList.remove('hidden');

  document.getElementById('nav-left').innerHTML =
    `<button class="nav-back" onclick="loadDashboard()">&larr; Projects</button>`;

  const content = document.getElementById('step-content');
  content.innerHTML = '<div class="loading-overlay"><div class="spinner"></div></div>';

  try {
    currentProject = await api('GET', `/projects/${id}`);
    document.getElementById('nav-right').innerHTML =
      `<button class="btn btn-danger btn-sm" onclick="deleteProject('${id}')">Delete</button>`;
    renderProject();
  } catch (err) {
    content.innerHTML = `<div class="empty-state" style="color:var(--error)">${err.message}</div>`;
  }
}

function getActiveStep(p) {
  if (p.steps_completed.includes('compose')) return 'compose';
  if (p.steps_completed.includes('prompts')) return 'assets';
  if (p.steps_completed.includes('music')) return 'prompts';
  if (p.steps_completed.includes('create')) return 'music';
  return 'create';
}

function renderSteps(activeKey, completed) {
  const bar = document.getElementById('steps-bar');
  bar.innerHTML = STEPS.map((s, i) => {
    const done = completed.includes(s.key) || (s.key === 'assets' && completed.includes('compose'));
    const active = s.key === activeKey;
    const cls = done ? 'completed' : active ? 'active' : '';
    const check = done ? '&#10003;' : (i + 1);
    return `
      <div class="step ${cls}">
        <span class="step-num">${check}</span>
        <span>${s.label}</span>
      </div>
      ${i < STEPS.length - 1 ? '<div class="step-line"></div>' : ''}
    `;
  }).join('');
}

function renderProject() {
  const p = currentProject;
  const active = getActiveStep(p);
  renderSteps(active, p.steps_completed);

  const el = document.getElementById('step-content');

  if (active === 'create') {
    el.innerHTML = renderStepCreate(p);
    setupDropzone('music-dropzone', (files) => handleMusicUpload(files[0]));
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
  return renderSunoPrompt(p) + renderMusicUpload();
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
  const meta = p.metadata || {};
  return `
    <div class="card">
      <div class="text-sm text-3" style="margin-bottom:4px">TITLE</div>
      <div style="font-size:16px;font-weight:600;margin-bottom:16px">${esc(meta.title || p.genre)}</div>
      ${meta.description ? `<div class="text-sm text-2 mb-12">${esc(meta.description)}</div>` : ''}
      ${meta.tags ? `<div class="text-sm text-3 mb-12">${meta.tags.map(t => '#' + t).join(' ')}</div>` : ''}
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
  const card = btn.closest('[data-copy]');
  if (!card) return;
  const text = card.getAttribute('data-copy');
  navigator.clipboard.writeText(text).then(() => {
    btn.textContent = 'Copied';
    btn.classList.add('copied');
    card.classList.add('copied');
  });
}

// --- Toggle ---

// --- Tab switching ---

let currentTab = 'shorts';

function switchTab(tab) {
  currentTab = tab;
  document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
  document.querySelector(`.nav-tab[onclick="switchTab('${tab}')"]`).classList.add('active');

  document.getElementById('view-dashboard').classList.add('hidden');
  document.getElementById('view-project').classList.add('hidden');
  document.getElementById('view-editor').classList.add('hidden');

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
  document.getElementById('nav-left').innerHTML = '<span class="nav-title">YouTube Shorts Music</span>';
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
