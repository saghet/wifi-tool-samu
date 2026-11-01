// HackingTool Web Suite — Frontend Application Logic
// Uses Vanilla JS, WebSocket for Realtime Streaming, AnsiUp for Terminal Output

const state = {
  system: null,
  categories: [],
  tools: [],
  tags: [],
  activeCategory: null,
  activeTag: null,
  searchQuery: '',
  installedOnly: false,
  activeTool: null,
  engagements: [],
  selectedEngagement: null,
  ws: null,
  wsConnected: false,
  isRunningCommand: false,
};

const ansiUp = new AnsiUp();
ansiUp.use_classes = false;

// ── Initialization ─────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  initApp();
  initWebSocket();
});

async function initApp() {
  try {
    await Promise.all([
      loadSystemInfo(),
      loadSystemDependencies(),
      loadCategories(),
      loadTools(),
      loadTags(),
      loadConfiguration(),
      loadEngagements(),
    ]);
  } catch (err) {
    console.error('Initialization error:', err);
  }
}

// ── Tab Navigation ─────────────────────────────────────────────────────────────

function switchTab(tabName) {
  document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
  const target = document.getElementById(`tab-${tabName}`);
  if (target) target.classList.remove('hidden');

  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.classList.remove('bg-purple-600/20', 'text-purple-400', 'border', 'border-purple-500/30');
    btn.classList.add('text-gray-400');
  });

  const activeBtn = document.getElementById(`nav-${tabName}`);
  if (activeBtn) {
    activeBtn.classList.remove('text-gray-400');
    activeBtn.classList.add('bg-purple-600/20', 'text-purple-400', 'border', 'border-purple-500/30');
  }

  if (tabName === 'catalog') {
    setTimeout(() => document.getElementById('catalog-search')?.focus(), 50);
  } else if (tabName === 'terminal') {
    setTimeout(() => document.getElementById('terminal-input')?.focus(), 50);
  }
}

// ── System Information & Stats ─────────────────────────────────────────────────

async function loadSystemInfo() {
  try {
    const res = await fetch('/api/system');
    if (!res.ok) return;
    state.system = await res.json();

    document.getElementById('header-version').textContent = state.system.hackingtool_version;
    document.getElementById('stat-total-tools').textContent = state.system.total_tools;
    document.getElementById('stat-installed-tools').textContent = state.system.installed_tools;
    document.getElementById('stat-categories').textContent = state.system.total_categories;
    const distroName = state.system.distro_family === 'arch' ? 'Garuda/Arch' : (state.system.distro_family === 'rhel' ? 'Red Hat/Fedora' : (state.system.distro_family === 'debian' ? 'Ubuntu/Debian' : state.system.os_name));
    document.getElementById('stat-host-os').textContent = `${distroName} (${state.system.pkg_manager || 'sys'})`;
    document.getElementById('stat-python-ver').textContent = `Python ${state.system.python_version}`;

    document.getElementById('dash-hero-tools').textContent = state.system.total_tools;
    document.getElementById('dash-hero-cats').textContent = state.system.total_categories;

    const pct = Math.round((state.system.installed_tools / (state.system.total_tools || 1)) * 100);
    document.getElementById('stat-installed-pct').textContent = `${pct}% del catálogo listo`;
  } catch (err) {
    console.warn('Failed to load system info:', err);
  }
}

// ── System Dependencies & Forensic Audit ───────────────────────────────────────

async function loadSystemDependencies() {
  try {
    const res = await fetch('/api/system/dependencies');
    if (!res.ok) return;
    state.dependencies = await res.json();
    renderSystemDependencies();
  } catch (err) {
    console.warn('Failed to load system dependencies:', err);
  }
}

function renderSystemDependencies() {
  const deps = state.dependencies;
  if (!deps) return;

  const pct = Math.round((deps.installed_count / (deps.total || 1)) * 100);
  const bar = document.getElementById('deps-progress-bar');
  if (bar) bar.style.width = `${pct}%`;

  const pill = document.getElementById('deps-status-pill');
  if (pill) {
    if (deps.missing_count === 0) {
      pill.className = 'px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-green-500/10 text-green-400 border border-green-500/30';
      pill.textContent = '100% Componentes Listos';
    } else {
      pill.className = 'px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-yellow-500/10 text-yellow-400 border border-yellow-500/30';
      pill.textContent = `${deps.installed_count}/${deps.total} Instalados (${deps.missing_count} faltantes)`;
    }
  }

  const desc = document.getElementById('deps-status-desc');
  if (desc) {
    desc.textContent = `Distribución: ${deps.distro_family.toUpperCase()} | Gestor: ${deps.pkg_manager}. ${deps.missing_count > 0 ? `Faltan herramientas esenciales como ${deps.tools.filter(t => !t.installed).slice(0, 3).map(t => t.name).join(', ')}...` : 'Todos los paquetes base de pentesting están instalados correctamente.'}`;
  }

  // Populate audit table in modal
  const tbody = document.getElementById('deps-table-body');
  if (tbody) {
    tbody.innerHTML = deps.tools.map(t => `
      <tr class="hover:bg-[#1A202C]/40 transition">
        <td class="p-2.5 font-medium text-white flex items-center space-x-2">
          <span>${t.name}</span>
        </td>
        <td class="p-2.5 text-gray-400">${t.category}</td>
        <td class="p-2.5">
          ${t.installed 
            ? '<span class="px-2 py-0.5 rounded text-[10px] font-medium bg-green-500/10 text-green-400 border border-green-500/20"><i class="fa-solid fa-check text-[9px] mr-1"></i>Instalado</span>'
            : '<span class="px-2 py-0.5 rounded text-[10px] font-medium bg-red-500/10 text-red-400 border border-red-500/20"><i class="fa-solid fa-xmark text-[9px] mr-1"></i>Faltante</span>'}
        </td>
        <td class="p-2.5 font-mono text-[11px] text-gray-400">${t.path}</td>
      </tr>
    `).join('');
  }

  const cmdText = document.getElementById('deps-setup-cmd-text');
  if (cmdText) cmdText.textContent = deps.setup_command;

  const countText = document.getElementById('deps-modal-count-text');
  if (countText) countText.textContent = `${deps.installed_count} de ${deps.total} componentes listos en ${deps.distro_family}`;
}

function toggleDepsDetailModal() {
  const modal = document.getElementById('deps-modal');
  if (!modal) return;
  modal.classList.toggle('hidden');
}

function runInstallSystemDeps() {
  if (!state.dependencies || !state.dependencies.setup_command) {
    alert('No se ha podido resolver el comando de instalación para esta distribución.');
    return;
  }
  switchTab('terminal');
  runCommand(state.dependencies.setup_command);
}

// ── Categories ─────────────────────────────────────────────────────────────────

async function loadCategories() {
  try {
    const res = await fetch('/api/categories');
    if (!res.ok) return;
    state.categories = await res.json();

    const dashGrid = document.getElementById('dash-categories-grid');
    dashGrid.innerHTML = '';
    state.categories.slice(0, 9).forEach(cat => {
      const card = document.createElement('div');
      card.className = 'bg-[#151921] border border-[#262D3D] rounded-xl p-4 hover:border-purple-500/50 hover:bg-[#1A202C] cursor-pointer transition flex items-center justify-between group';
      card.onclick = () => {
        filterCategory(cat.id);
        switchTab('catalog');
      };
      card.innerHTML = `
        <div class="flex items-center space-x-3">
          <div class="w-10 h-10 rounded-lg bg-purple-500/10 text-purple-400 group-hover:bg-purple-600 group-hover:text-white flex items-center justify-center text-lg transition">
            ${cat.icon || '🛠'}
          </div>
          <div>
            <h4 class="text-sm font-bold text-white group-hover:text-purple-300 transition">${cat.menu_label || cat.title}</h4>
            <span class="text-[11px] text-gray-400">${cat.total_tools} herramientas (${cat.installed_tools} instaladas)</span>
          </div>
        </div>
        <i class="fa-solid fa-chevron-right text-gray-500 group-hover:text-purple-400 text-xs transition"></i>
      `;
      dashGrid.appendChild(card);
    });

    const pillsContainer = document.getElementById('category-pills');
    pillsContainer.querySelectorAll('.cat-pill-dynamic').forEach(el => el.remove());
    state.categories.forEach(cat => {
      const btn = document.createElement('button');
      btn.id = `cat-pill-${cat.id}`;
      btn.className = 'cat-pill cat-pill-dynamic px-3 py-1 rounded-lg text-xs font-medium bg-[#0B0E14] border border-[#262D3D] text-gray-300 hover:text-white hover:border-gray-500 transition whitespace-nowrap';
      btn.textContent = `${cat.icon || ''} ${cat.menu_label || cat.title} (${cat.total_tools})`;
      btn.onclick = () => filterCategory(cat.id);
      pillsContainer.appendChild(btn);
    });
  } catch (err) {
    console.error('Failed to load categories:', err);
  }
}

// ── Tags ───────────────────────────────────────────────────────────────────────

async function loadTags() {
  try {
    const res = await fetch('/api/tags');
    if (!res.ok) return;
    state.tags = await res.json();

    const tagPills = document.getElementById('tag-pills');
    tagPills.innerHTML = '';
    state.tags.filter(t => t.count > 0).sort((a, b) => b.count - a.count).slice(0, 16).forEach(t => {
      const pill = document.createElement('button');
      pill.className = 'text-[11px] px-2.5 py-0.5 rounded-full bg-[#1A202C] border border-[#262D3D] text-gray-400 hover:text-purple-300 hover:border-purple-500/50 transition';
      pill.textContent = `#${t.tag} (${t.count})`;
      pill.onclick = () => filterTag(t.tag);
      tagPills.appendChild(pill);
    });
  } catch (err) {
    console.error('Failed to load tags:', err);
  }
}

// ── Tools Catalog ──────────────────────────────────────────────────────────────

async function loadTools() {
  try {
    const res = await fetch('/api/tools');
    if (!res.ok) return;
    state.tools = await res.json();
    document.getElementById('nav-tools-badge').textContent = state.tools.length;
    applyFilters();
  } catch (err) {
    console.error('Failed to load tools:', err);
  }
}

function renderToolsList(toolsToRender) {
  const grid = document.getElementById('tools-grid');
  const emptyState = document.getElementById('tools-empty');
  const counter = document.getElementById('tools-count-badge');

  counter.textContent = toolsToRender.length;
  grid.innerHTML = '';

  if (toolsToRender.length === 0) {
    emptyState.classList.remove('hidden');
    return;
  } else {
    emptyState.classList.add('hidden');
  }

  toolsToRender.forEach(tool => {
    const card = document.createElement('div');
    card.className = 'tool-card bg-[#151921] border border-[#262D3D] rounded-xl p-4 flex flex-col justify-between hover:border-purple-500/40';

    const tagsHtml = (tool.tags || []).slice(0, 3).map(tg => 
      `<span class="tag-badge text-[10px] px-2 py-0.5 rounded-full">#${tg}</span>`
    ).join(' ');

    const isInst = tool.is_installed;
    const statusBadge = isInst 
      ? `<span class="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full bg-green-500/10 text-green-400 text-[10px] font-mono border border-green-500/20"><i class="fa-solid fa-check text-[9px]"></i><span>Instalada</span></span>`
      : `<span class="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full bg-gray-500/10 text-gray-400 text-[10px] font-mono border border-gray-500/20"><span>No instalada</span></span>`;

    const usageCount = tool.usage ? tool.usage.length : 0;
    const usageBadge = usageCount > 0 
      ? `<span class="text-[10px] text-yellow-400/90 font-mono ml-2"><i class="fa-solid fa-bolt mr-1"></i>${usageCount} comandos</span>` 
      : '';

    const hasInstallCmds = tool.install_commands && tool.install_commands.length > 0;

    card.innerHTML = `
      <div class="space-y-2">
        <div class="flex items-start justify-between gap-2">
          <div>
            <h3 class="text-sm font-bold text-white hover:text-purple-400 cursor-pointer transition" onclick="openToolModal('${tool.id}')">${tool.title}</h3>
            <span class="text-[11px] text-purple-400/80 block mt-0.5 font-medium">${tool.category_title}</span>
          </div>
          <div>${statusBadge}</div>
        </div>

        <p class="text-xs text-gray-400 line-clamp-2 leading-relaxed">
          ${tool.description || 'Herramienta de seguridad para análisis y auditorías especializadas.'}
        </p>

        <div class="flex items-center justify-between pt-1">
          <div class="flex flex-wrap gap-1">${tagsHtml}</div>
          <div>${usageBadge}</div>
        </div>
      </div>

      <div class="mt-4 pt-3 border-t border-[#262D3D] flex items-center justify-between gap-2">
        <button onclick="openToolModal('${tool.id}')" class="px-3 py-1.5 rounded-lg bg-[#262D3D] hover:bg-[#343D52] text-xs text-gray-300 font-medium transition flex items-center space-x-1">
          <i class="fa-solid fa-circle-info text-[11px]"></i>
          <span>Detalles</span>
        </button>

        <div class="flex items-center space-x-1.5">
          ${hasInstallCmds && !isInst ? `
            <button onclick="runInstallTool('${tool.id}')" title="Instalar herramienta con el gestor del sistema" class="px-2.5 py-1.5 rounded-lg bg-blue-600/20 hover:bg-blue-600/40 text-blue-400 border border-blue-500/30 text-xs font-mono transition flex items-center space-x-1">
              <i class="fa-solid fa-download text-[10px]"></i>
              <span class="hidden sm:inline">Instalar</span>
            </button>
          ` : ''}

          <button onclick="runToolCommand('${tool.id}')" title="${isInst ? 'Ejecutar comando' : 'Herramienta no instalada'}" class="px-2.5 py-1.5 rounded-lg ${isInst ? 'bg-green-600/20 hover:bg-green-600/40 text-green-400 border border-green-500/30' : 'bg-gray-600/20 hover:bg-gray-600/40 text-gray-400 border border-gray-500/30'} text-xs font-mono transition flex items-center space-x-1">
            <i class="fa-solid fa-play text-[10px]"></i>
            <span class="hidden sm:inline">Ejecutar</span>
          </button>
        </div>
      </div>
    `;

    grid.appendChild(card);
  });
}

// ── Search & Filter Logic ──────────────────────────────────────────────────────

let searchTimeout = null;
function handleSearchInput() {
  clearTimeout(searchTimeout);
  const val = document.getElementById('catalog-search').value;
  const clearBtn = document.getElementById('search-clear-btn');
  if (val) {
    clearBtn.classList.remove('hidden');
  } else {
    clearBtn.classList.add('hidden');
  }
  searchTimeout = setTimeout(() => {
    state.searchQuery = val.trim();
    applyFilters();
  }, 250);
}

function clearSearch() {
  document.getElementById('catalog-search').value = '';
  document.getElementById('search-clear-btn').classList.add('hidden');
  state.searchQuery = '';
  applyFilters();
}

function filterCategory(catId) {
  state.activeCategory = catId;
  document.querySelectorAll('.cat-pill').forEach(btn => {
    btn.classList.remove('bg-purple-600', 'text-white');
    btn.classList.add('bg-[#0B0E14]', 'text-gray-300');
  });

  const activePill = document.getElementById(catId ? `cat-pill-${catId}` : 'cat-pill-all');
  if (activePill) {
    activePill.classList.remove('bg-[#0B0E14]', 'text-gray-300');
    activePill.classList.add('bg-purple-600', 'text-white');
  }

  applyFilters();
}

function filterTag(tag) {
  state.activeTag = (state.activeTag === tag) ? null : tag;
  applyFilters();
}

function resetFilters() {
  state.searchQuery = '';
  state.activeCategory = null;
  state.activeTag = null;
  state.installedOnly = false;
  document.getElementById('catalog-search').value = '';
  document.getElementById('filter-installed-only').checked = false;
  filterCategory(null);
}

function applyFilters() {
  state.installedOnly = document.getElementById('filter-installed-only').checked;

  let filtered = state.tools;

  if (state.activeCategory) {
    filtered = filtered.filter(t => t.category_slug === state.activeCategory);
  }

  if (state.activeTag) {
    filtered = filtered.filter(t => t.tags && t.tags.includes(state.activeTag));
  }

  if (state.installedOnly) {
    filtered = filtered.filter(t => t.is_installed);
  }

  if (state.searchQuery) {
    const q = state.searchQuery.toLowerCase();
    filtered = filtered.filter(t => {
      const matchTitle = t.title.toLowerCase().includes(q);
      const matchDesc = (t.description || '').toLowerCase().includes(q);
      const matchTags = (t.tags || []).some(tg => tg.toLowerCase().includes(q));
      const matchUsage = (t.usage || []).some(u => u.task.toLowerCase().includes(q) || u.command.toLowerCase().includes(q));
      return matchTitle || matchDesc || matchTags || matchUsage;
    });
  }

  renderToolsList(filtered);
}

// ── Smart Install & Run Handlers ───────────────────────────────────────────────

function runInstallTool(toolId) {
  const tool = state.tools.find(t => t.id === toolId);
  if (!tool) return;

  let cmds = tool.install_commands || [];
  if (cmds.length === 0) {
    alert(`No hay comandos de instalación definidos para ${tool.title}.`);
    return;
  }

  const fullInstallCmd = cmds.join(' && ');
  switchTab('terminal');
  runCommand(fullInstallCmd);
}

function runToolCommand(toolId) {
  const tool = state.tools.find(t => t.id === toolId);
  if (!tool) return;

  // Resolve best command to run
  let cmd = '';
  if (tool.run_commands && tool.run_commands.length > 0) {
    cmd = tool.run_commands[0];
  } else if (tool.usage && tool.usage.length > 0) {
    cmd = tool.usage[0].command;
  }

  if (!tool.is_installed) {
    const wantInstall = confirm(
      `⚠️ La herramienta '${tool.title}' no está instalada en tu sistema aún.\n\n` +
      `¿Deseas ejecutar su instalación ahora?\n` +
      `(Si eliges 'Cancelar', se intentará ejecutar el comando de todos modos).`
    );
    if (wantInstall) {
      runInstallTool(toolId);
      return;
    }
  }

  if (!cmd) {
    openToolModal(toolId);
    return;
  }

  switchTab('terminal');
  runCommand(cmd);
}

// ── Tool Modal ─────────────────────────────────────────────────────────────────

function openToolModal(toolId) {
  const tool = state.tools.find(t => t.id === toolId);
  if (!tool) return;
  state.activeTool = tool;

  document.getElementById('modal-tool-title').textContent = tool.title;
  document.getElementById('modal-tool-category').textContent = tool.category_title;
  document.getElementById('modal-tool-desc').textContent = tool.description || 'Sin descripción detallada disponible.';

  const statusEl = document.getElementById('modal-tool-status');
  if (tool.is_installed) {
    statusEl.className = 'text-[10px] px-2 py-0.5 rounded-full font-mono bg-green-500/10 text-green-400 border border-green-500/20';
    statusEl.textContent = 'Instalada en sistema';
  } else {
    statusEl.className = 'text-[10px] px-2 py-0.5 rounded-full font-mono bg-gray-500/10 text-gray-400 border border-gray-500/20';
    statusEl.textContent = 'No instalada';
  }

  const urlBox = document.getElementById('modal-tool-url-box');
  const urlLink = document.getElementById('modal-tool-url');
  if (tool.project_url) {
    urlBox.classList.remove('hidden');
    urlLink.href = tool.project_url;
    urlLink.textContent = tool.project_url;
  } else {
    urlBox.classList.add('hidden');
  }

  const tagsBox = document.getElementById('modal-tool-tags');
  tagsBox.innerHTML = '';
  (tool.tags || []).forEach(tg => {
    const sp = document.createElement('span');
    sp.className = 'tag-badge text-xs px-2.5 py-0.5 rounded-full';
    sp.textContent = `#${tg}`;
    tagsBox.appendChild(sp);
  });

  const usageBox = document.getElementById('modal-tool-usage-box');
  const usageList = document.getElementById('modal-tool-usage-list');
  usageList.innerHTML = '';
  if (tool.usage && tool.usage.length > 0) {
    usageBox.classList.remove('hidden');
    tool.usage.forEach(u => {
      const item = document.createElement('div');
      item.className = 'bg-[#0B0E14] border border-[#262D3D] rounded-lg p-2.5 flex items-center justify-between gap-2';
      item.innerHTML = `
        <div class="flex-1 overflow-hidden">
          <span class="text-gray-400 block font-sans text-[11px] mb-0.5">${u.task}</span>
          <code class="text-purple-300 font-mono text-xs block truncate select-all">${u.command}</code>
        </div>
        <div class="flex items-center space-x-1 shrink-0">
          <button onclick="copyToClipboard('${u.command.replace(/'/g, "\\'")}')" class="p-1.5 text-gray-400 hover:text-white rounded bg-[#151921] border border-[#262D3D] text-[11px]" title="Copiar comando">
            <i class="fa-regular fa-copy"></i>
          </button>
          <button onclick="closeToolModal(); runCommand('${u.command.replace(/'/g, "\\'")}')" class="px-2 py-1 bg-purple-600/20 hover:bg-purple-600/40 text-purple-300 border border-purple-500/30 rounded text-[11px] font-mono" title="Ejecutar en terminal">
            <i class="fa-solid fa-play text-[9px] mr-1"></i>Lanzar
          </button>
        </div>
      `;
      usageList.appendChild(item);
    });
  } else {
    usageBox.classList.add('hidden');
  }

  const installBox = document.getElementById('modal-tool-install-box');
  const installCmds = document.getElementById('modal-tool-install-cmds');
  installCmds.innerHTML = '';
  if (tool.install_commands && tool.install_commands.length > 0) {
    installBox.classList.remove('hidden');
    tool.install_commands.forEach(cmd => {
      const d = document.createElement('div');
      d.className = 'text-gray-300 select-all';
      d.textContent = `$ ${cmd}`;
      installCmds.appendChild(d);
    });
  } else {
    installBox.classList.add('hidden');
  }

  const btnInstall = document.getElementById('modal-btn-install');
  if (tool.install_commands && tool.install_commands.length > 0) {
    btnInstall.classList.remove('hidden');
  } else {
    btnInstall.classList.add('hidden');
  }

  document.getElementById('tool-detail-modal').classList.remove('hidden');
  document.getElementById('tool-detail-modal').classList.add('flex');
}

function closeToolModal() {
  const m = document.getElementById('tool-detail-modal');
  m.classList.add('hidden');
  m.classList.remove('flex');
}

function executeCurrentToolInstall() {
  if (!state.activeTool) return;
  const toolId = state.activeTool.id;
  closeToolModal();
  runInstallTool(toolId);
}

function executeCurrentToolRun() {
  if (!state.activeTool) return;
  const toolId = state.activeTool.id;
  closeToolModal();
  runToolCommand(toolId);
}

// ── WebSocket & Terminal ───────────────────────────────────────────────────────

function initWebSocket() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}/ws/terminal`;
  
  state.ws = new WebSocket(wsUrl);

  state.ws.onopen = () => {
    state.wsConnected = true;
    updateWsStatus(true);
  };

  state.ws.onclose = () => {
    state.wsConnected = false;
    updateWsStatus(false);
    setTimeout(initWebSocket, 3000);
  };

  state.ws.onerror = (err) => {
    console.warn('WebSocket error:', err);
    state.wsConnected = false;
    updateWsStatus(false);
  };

  state.ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      handleWsMessage(msg);
    } catch (e) {
      appendTerminalOutput(event.data);
    }
  };
}

function updateWsStatus(connected) {
  const badge = document.getElementById('ws-status-badge');
  const txt = document.getElementById('ws-status-text');
  if (connected) {
    badge.className = 'flex items-center space-x-1.5 text-xs px-2.5 py-1 rounded-full bg-green-500/10 text-green-400 border border-green-500/20 font-mono';
    badge.querySelector('span:first-child').className = 'w-2 h-2 rounded-full bg-green-400 animate-pulse';
    txt.textContent = 'Terminal Conectada';
  } else {
    badge.className = 'flex items-center space-x-1.5 text-xs px-2.5 py-1 rounded-full bg-red-500/10 text-red-400 border border-red-500/20 font-mono';
    badge.querySelector('span:first-child').className = 'w-2 h-2 rounded-full bg-red-400 animate-pulse';
    txt.textContent = 'Desconectado';
  }
}

function updateTerminalInputUI(running) {
  state.isRunningCommand = running;
  const input = document.getElementById('terminal-input');
  const submitBtn = document.getElementById('term-submit-btn');
  const indicator = document.getElementById('term-active-indicator');

  if (running) {
    indicator.textContent = 'EJECUTANDO...';
    indicator.className = 'text-[10px] text-yellow-400 font-mono animate-pulse';
    if (input) input.placeholder = 'Proceso activo: escribe tu respuesta/contraseña y pulsa Enviar (o Interrumpir arriba)...';
    if (submitBtn) {
      submitBtn.textContent = 'Enviar Entrada';
      submitBtn.className = 'px-4 py-1.5 bg-yellow-600 hover:bg-yellow-500 text-white rounded text-xs font-mono font-medium transition';
    }
  } else {
    indicator.textContent = 'LISTO';
    indicator.className = 'text-[10px] text-green-400 font-mono';
    if (input) input.placeholder = 'Introduce comando bash (ej: nmap -sn 192.168.1.0/24)...';
    if (submitBtn) {
      submitBtn.textContent = 'Ejecutar';
      submitBtn.className = 'px-4 py-1.5 bg-purple-600 hover:bg-purple-500 text-white rounded text-xs font-mono font-medium transition';
    }
  }
}

function handleWsMessage(msg) {
  if (msg.type === 'start') {
    updateTerminalInputUI(true);
    appendTerminalOutput(`\n\x1b[36m[START]\x1b[0m Ejecutando: \x1b[1;32m${msg.command}\x1b[0m en \x1b[33m${msg.cwd}\x1b[0m\n`);
  } else if (msg.type === 'stdout') {
    appendTerminalOutput(msg.data);
  } else if (msg.type === 'stderr') {
    appendTerminalOutput(msg.data);
  } else if (msg.type === 'exit') {
    updateTerminalInputUI(false);
    const codeColor = msg.code === 0 ? '\x1b[32m' : '\x1b[31m';
    appendTerminalOutput(`\n\x1b[36m[EXIT]\x1b[0m Proceso finalizado con código: ${codeColor}${msg.code}\x1b[0m\n──────────────────────────────────────────────────────────────────────────\n`);
    // Refresh tools status in background if an install just completed
    if (msg.command && (msg.command.includes('pacman') || msg.command.includes('apt') || msg.command.includes('clone') || msg.command.includes('dnf') || msg.command.includes('zypper'))) {
      setTimeout(loadTools, 1500);
      setTimeout(loadSystemInfo, 1500);
      setTimeout(loadSystemDependencies, 1500);
    }
  }
}

function appendTerminalOutput(rawText) {
  const term = document.getElementById('terminal-output');
  if (!term) return;
  const formattedHtml = ansiUp.ansi_to_html(rawText);
  const span = document.createElement('span');
  span.innerHTML = formattedHtml;
  term.appendChild(span);
  term.scrollTop = term.scrollHeight;
}

function runCommand(command, cwd = null) {
  if (!state.ws || state.ws.readyState !== WebSocket.OPEN) {
    alert('Terminal desconectada del servidor. Reintentando conexión...');
    return;
  }
  switchTab('terminal');
  state.ws.send(JSON.stringify({
    action: 'run',
    command: command,
    cwd: cwd,
  }));
}

function sendProcessInput(data) {
  if (!state.ws || state.ws.readyState !== WebSocket.OPEN) return;
  state.ws.send(JSON.stringify({
    action: 'input',
    data: data,
  }));
}

function runPredefinedCommand(cmd) {
  runCommand(cmd);
}

function killProcess() {
  if (!state.ws || state.ws.readyState !== WebSocket.OPEN) return;
  state.ws.send(JSON.stringify({ action: 'kill' }));
  updateTerminalInputUI(false);
}

function clearTerminal() {
  document.getElementById('terminal-output').innerHTML = `
    <div class="text-purple-400">Terminal de HackingTool limpiada.</div>
  `;
}

function handleTerminalSubmit(e) {
  e.preventDefault();
  const input = document.getElementById('terminal-input');
  const text = input.value;
  if (!text && !state.isRunningCommand) return;

  if (state.isRunningCommand) {
    // Send input directly to stdin of running process
    sendProcessInput(text + '\n');
    appendTerminalOutput(`\x1b[33m${text}\x1b[0m\n`);
  } else {
    runCommand(text.trim());
  }
  input.value = '';
}

// ── AI Assistant Tab ───────────────────────────────────────────────────────────

function setAiPrompt(text) {
  document.getElementById('ai-intent-input').value = text;
  document.getElementById('ai-intent-input').focus();
}

async function handleAiRecommend(e) {
  e.preventDefault();
  const input = document.getElementById('ai-intent-input');
  const intent = input.value.trim();
  if (!intent) return;

  const btn = document.getElementById('ai-submit-btn');
  btn.disabled = true;
  btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i><span>Analizando...</span>`;

  try {
    const res = await fetch('/api/ai/recommend', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ intent })
    });

    const data = await res.json();
    renderAiResults(data);
  } catch (err) {
    alert('Error al consultar el asistente IA: ' + err);
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i class="fa-solid fa-wand-magic-sparkles"></i><span>Consultar</span>`;
  }
}

function renderAiResults(data) {
  const container = document.getElementById('ai-results-container');
  const tagsContainer = document.getElementById('ai-detected-tags');
  const listContainer = document.getElementById('ai-recommendations-list');

  tagsContainer.innerHTML = '';
  listContainer.innerHTML = '';

  (data.tags || []).forEach(tg => {
    const sp = document.createElement('span');
    sp.className = 'text-xs px-2.5 py-0.5 rounded-full bg-purple-600/20 text-purple-300 border border-purple-500/30 font-mono';
    sp.textContent = `#${tg}`;
    tagsContainer.appendChild(sp);
  });

  if (!data.recommendations || data.recommendations.length === 0) {
    listContainer.innerHTML = `
      <div class="col-span-2 text-center py-8 text-gray-400">
        No se encontraron herramientas exactas para este objetivo. Prueba especificando más palabras clave.
      </div>
    `;
  } else {
    data.recommendations.forEach(rec => {
      const tool = rec.tool;
      const card = document.createElement('div');
      card.className = 'bg-[#151921] border border-[#262D3D] rounded-xl p-5 hover:border-purple-500/50 space-y-3 transition';

      const cmdBox = rec.suggested_command ? `
        <div class="bg-[#0B0E14] p-3 rounded-lg border border-[#262D3D] space-y-1">
          <div class="flex items-center justify-between text-[11px]">
            <span class="text-yellow-400 font-semibold flex items-center space-x-1">
              <i class="fa-solid fa-terminal text-[10px]"></i>
              <span>Comando Recomendado (${rec.suggested_command.source})</span>
            </span>
            <button onclick="copyToClipboard('${rec.suggested_command.command.replace(/'/g, "\\'")}')" class="text-gray-400 hover:text-white" title="Copiar"><i class="fa-regular fa-copy"></i></button>
          </div>
          <code class="text-xs text-purple-300 font-mono block select-all break-all">${rec.suggested_command.command}</code>
        </div>
      ` : '';

      card.innerHTML = `
        <div class="flex items-start justify-between">
          <div>
            <h4 class="text-base font-bold text-white">${tool.title}</h4>
            <span class="text-xs text-purple-400">${tool.category_title}</span>
          </div>
          <span class="text-xs px-2 py-0.5 rounded bg-purple-500/10 text-purple-400 border border-purple-500/20 font-mono">
            Score: ${rec.score}
          </span>
        </div>

        <p class="text-xs text-gray-400 leading-relaxed">${tool.description || ''}</p>

        ${cmdBox}

        <div class="pt-2 flex items-center justify-between">
          <button onclick="openToolModal('${tool.id}')" class="text-xs text-purple-400 hover:underline">Ver detalles completos</button>
          ${rec.suggested_command ? `
            <button onclick="runCommand('${rec.suggested_command.command.replace(/'/g, "\\'")}')" class="px-3 py-1.5 rounded-lg bg-purple-600 hover:bg-purple-500 text-white text-xs font-mono font-medium flex items-center space-x-1 transition shadow-lg shadow-purple-600/30">
              <i class="fa-solid fa-play text-[9px]"></i>
              <span>Ejecutar en Terminal</span>
            </button>
          ` : `
            <button onclick="openToolModal('${tool.id}')" class="px-3 py-1.5 rounded-lg bg-[#262D3D] text-gray-300 text-xs hover:bg-[#343D52]">
              Configurar
            </button>
          `}
        </div>
      `;

      listContainer.appendChild(card);
    });
  }

  container.classList.remove('hidden');
}

// ── Engagements & Audits ───────────────────────────────────────────────────────

async function loadEngagements() {
  try {
    const res = await fetch('/api/engagements');
    if (!res.ok) return;
    state.engagements = await res.json();
    renderEngagementsList();
  } catch (err) {
    console.error('Failed to load engagements:', err);
  }
}

function renderEngagementsList() {
  const container = document.getElementById('engagements-list');
  container.innerHTML = '';

  if (state.engagements.length === 0) {
    container.innerHTML = `<div class="text-xs text-gray-500 text-center py-4">No hay auditorías guardadas. Crea una con '+ Nueva Auditoría'.</div>`;
    return;
  }

  state.engagements.forEach(eng => {
    const item = document.createElement('div');
    const isSel = state.selectedEngagement && state.selectedEngagement.name === eng.name;
    item.className = `p-3 rounded-lg border cursor-pointer transition ${isSel ? 'bg-purple-600/20 border-purple-500/50' : 'bg-[#0B0E14] border-[#262D3D] hover:border-gray-500'}`;
    item.onclick = () => selectEngagement(eng.name);
    item.innerHTML = `
      <div class="flex items-center justify-between">
        <h4 class="text-xs font-bold text-white">${eng.name}</h4>
        <span class="text-[10px] text-gray-400 font-mono">${(eng.created || '').slice(0, 10)}</span>
      </div>
      <div class="text-[11px] text-gray-400 mt-1 flex items-center justify-between">
        <span>${(eng.targets || []).length} objetivos</span>
        <span class="text-yellow-400">${eng.findings_count || 0} hallazgos</span>
      </div>
    `;
    container.appendChild(item);
  });
}

async function selectEngagement(name) {
  try {
    const res = await fetch(`/api/engagements/${name}`);
    if (!res.ok) return;
    state.selectedEngagement = await res.json();
    renderSelectedEngagement();
    renderEngagementsList();
  } catch (err) {
    alert('Error al cargar engagement: ' + err);
  }
}

function renderSelectedEngagement() {
  const empty = document.getElementById('engagement-details-empty');
  const view = document.getElementById('engagement-details-view');
  if (!state.selectedEngagement) {
    empty.classList.remove('hidden');
    view.classList.add('hidden');
    return;
  }

  empty.classList.add('hidden');
  view.classList.remove('hidden');

  const eng = state.selectedEngagement;
  document.getElementById('eng-view-name').textContent = eng.name;
  document.getElementById('eng-view-created').textContent = `Iniciada: ${eng.created}`;
  document.getElementById('eng-view-targets').textContent = (eng.targets || []).join(', ') || 'Ninguno especificado';
  document.getElementById('eng-view-scope').textContent = (eng.scope_in || []).join(', ') || 'Todo el target';

  const findingsList = document.getElementById('eng-findings-list');
  document.getElementById('eng-findings-count').textContent = (eng.findings || []).length;
  findingsList.innerHTML = '';
  if (!eng.findings || eng.findings.length === 0) {
    findingsList.innerHTML = `<div class="text-xs text-gray-500 italic py-2">Sin hallazgos registrados aún.</div>`;
  } else {
    eng.findings.forEach(f => {
      const row = document.createElement('div');
      const sevColor = f.severity === 'high' || f.severity === 'critical' ? 'text-red-400 border-red-500/30 bg-red-500/10' : (f.severity === 'medium' ? 'text-yellow-400 border-yellow-500/30 bg-yellow-500/10' : 'text-blue-400 border-blue-500/30 bg-blue-500/10');
      row.className = 'p-2.5 rounded-lg bg-[#0B0E14] border border-[#262D3D] flex items-center justify-between text-xs';
      row.innerHTML = `
        <div>
          <span class="font-bold text-white">${f.name}</span>
          <span class="text-gray-400 ml-2 font-mono text-[11px]">${f.target} (${f.source_tool})</span>
        </div>
        <span class="px-2 py-0.5 rounded-full border text-[10px] font-mono ${sevColor}">${f.severity.toUpperCase()}</span>
      `;
      findingsList.appendChild(row);
    });
  }

  const reportEl = document.getElementById('eng-report-preview');
  if (eng.report) {
    reportEl.innerHTML = marked.parse(eng.report);
  } else {
    reportEl.innerHTML = `<p class="text-gray-500 italic">No hay reporte generado aún.</p>`;
  }
}

function openNewEngagementModal() {
  document.getElementById('new-engagement-modal').classList.remove('hidden');
  document.getElementById('new-engagement-modal').classList.add('flex');
}

function closeNewEngagementModal() {
  document.getElementById('new-engagement-modal').classList.add('hidden');
  document.getElementById('new-engagement-modal').classList.remove('flex');
}

async function handleCreateEngagement(e) {
  e.preventDefault();
  const name = document.getElementById('eng-new-name').value.trim();
  const targets = document.getElementById('eng-new-targets').value.split(',').map(s => s.trim()).filter(Boolean);
  const scopeIn = document.getElementById('eng-new-scope-in').value.split(',').map(s => s.trim()).filter(Boolean);
  const scopeOut = document.getElementById('eng-new-scope-out').value.split(',').map(s => s.trim()).filter(Boolean);

  try {
    const res = await fetch('/api/engagements', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, targets, scope_in: scopeIn, scope_out: scopeOut })
    });
    if (!res.ok) throw new Error(await res.text());
    closeNewEngagementModal();
    await loadEngagements();
    selectEngagement(name);
  } catch (err) {
    alert('Error al crear auditoría: ' + err);
  }
}

function downloadReport() {
  if (!state.selectedEngagement || !state.selectedEngagement.report) {
    alert('No hay reporte disponible para descargar.');
    return;
  }
  const blob = new Blob([state.selectedEngagement.report], { type: 'text/markdown' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `report-${state.selectedEngagement.name}.md`;
  a.click();
}

// ── Configuration ──────────────────────────────────────────────────────────────

async function loadConfiguration() {
  try {
    const res = await fetch('/api/config');
    if (!res.ok) return;
    const cfg = await res.json();
    document.getElementById('cfg-ai-provider').value = cfg.ai_provider || 'auto';
    document.getElementById('cfg-ai-base-url').value = cfg.ai_base_url || '';
    document.getElementById('cfg-ai-model').value = cfg.ai_model || '';
    document.getElementById('cfg-tools-dir').value = cfg.tools_dir || '';

    const keyStatus = document.getElementById('cfg-key-status');
    if (cfg.has_ai_key) {
      keyStatus.textContent = '✓ Clave guardada';
      keyStatus.className = 'absolute right-3 top-2.5 text-[11px] text-green-400 font-mono';
    } else {
      keyStatus.textContent = 'Sin clave';
      keyStatus.className = 'absolute right-3 top-2.5 text-[11px] text-gray-500 font-mono';
    }
  } catch (err) {
    console.error('Failed to load configuration:', err);
  }
}

async function saveConfiguration(e) {
  e.preventDefault();
  const provider = document.getElementById('cfg-ai-provider').value;
  const baseUrl = document.getElementById('cfg-ai-base-url').value;
  const model = document.getElementById('cfg-ai-model').value;
  const key = document.getElementById('cfg-ai-key').value.trim();

  const payload = {
    ai_provider: provider,
    ai_base_url: baseUrl,
    ai_model: model,
  };
  if (key) {
    payload.ai_key = key;
  }

  try {
    const res = await fetch('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error(await res.text());
    alert('Configuración guardada correctamente.');
    document.getElementById('cfg-ai-key').value = '';
    loadConfiguration();
  } catch (err) {
    alert('Error al guardar configuración: ' + err);
  }
}

async function testAiConnection() {
  const btn = document.getElementById('btn-test-ai');
  const resultBox = document.getElementById('ai-test-result');
  btn.disabled = true;
  btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin text-xs"></i><span>Probando conexión...</span>`;
  resultBox.classList.add('hidden');

  try {
    const res = await fetch('/api/config/test-ai', { method: 'POST' });
    const data = await res.json();
    resultBox.classList.remove('hidden');
    if (data.connected) {
      resultBox.className = 'p-3 rounded-lg text-xs font-mono bg-green-500/10 text-green-400 border border-green-500/30';
      resultBox.textContent = `✓ Conexión Exitosa: ${data.detail}`;
    } else {
      resultBox.className = 'p-3 rounded-lg text-xs font-mono bg-red-500/10 text-red-400 border border-red-500/30';
      resultBox.textContent = `✗ Fallo de Conexión: ${data.detail}`;
    }
  } catch (err) {
    resultBox.classList.remove('hidden');
    resultBox.className = 'p-3 rounded-lg text-xs font-mono bg-red-500/10 text-red-400 border border-red-500/30';
    resultBox.textContent = `Error: ${err}`;
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i class="fa-solid fa-network-wired text-xs"></i><span>Probar Conexión de IA</span>`;
  }
}

// ── Utility Functions ──────────────────────────────────────────────────────────

function copyToClipboard(text) {
  navigator.clipboard.writeText(text).then(() => {
    const toast = document.createElement('div');
    toast.className = 'fixed bottom-5 right-5 bg-purple-600 text-white text-xs px-4 py-2 rounded-lg shadow-xl z-50 flex items-center space-x-2 transition animate-bounce';
    toast.innerHTML = `<i class="fa-solid fa-check"></i><span>Comando copiado al portapapeles</span>`;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 2000);
  });
}
