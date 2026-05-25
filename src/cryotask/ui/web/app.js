// --- App State ---
const state = {
    currentTab: 'dashboard',
    safeMode: true,
    searchQuery: '',
    filterMode: 'all',
    sortBy: 'memory',
    processes: [],
    presets: {},
    rules: {
        periodic_trim: {},
        ram_threshold: { enabled: false, threshold: 80, apps: [] }
    },
    // Chart History (Max 30 points, 2s intervals = 60s history)
    chartHistory: {
        cpu: [],
        ram: [],
        labels: []
    },
    activeScheduleApp: null,
    editingPresetName: null,
    tempPresetApps: {}, // Temp dictionary for builder: { appName: action }
    timers: {
        stats: null,
        processes: null
    }
};

// --- Initialization ---
window.addEventListener('pywebviewready', () => {
    initApp();
});

// Fallback for development outside pywebview environment
setTimeout(() => {
    if (!window.pywebview) {
        console.warn("Pywebview not detected. Running in browser simulation mode.");
        setupMockApi();
        initApp();
    }
}, 500);

async function initApp() {
    setupTabNavigation();
    setupEventListeners();
    setupChart();
    
    // Load initial data
    await refreshData();
    await loadRules();
    await loadPresets();
    
    // Start periodic background updates
    startPeriodicUpdates();
    
    setStatusBar("Ready", "ready");
}

// --- Tab Navigation ---
function setupTabNavigation() {
    const menuItems = document.querySelectorAll('.menu-item');
    const tabContents = document.querySelectorAll('.tab-content');
    const searchContainer = document.getElementById('headerSearchContainer');
    
    menuItems.forEach(item => {
        item.addEventListener('click', () => {
            const tabId = item.getAttribute('data-tab');
            
            // Toggle active menu class
            menuItems.forEach(m => m.classList.remove('active'));
            item.classList.add('active');
            
            // Toggle active tab content
            tabContents.forEach(content => content.classList.remove('active'));
            document.getElementById(`tab-${tabId}`).classList.add('active');
            
            state.currentTab = tabId;
            
            // Update titles
            const titleEl = document.getElementById('tabTitle');
            const subEl = document.getElementById('tabSubtitle');
            
            if (tabId === 'dashboard') {
                titleEl.textContent = 'Dashboard';
                subEl.textContent = 'Real-time system resource monitor';
                searchContainer.style.display = 'none';
            } else if (tabId === 'processes') {
                titleEl.textContent = 'System Processes';
                subEl.textContent = 'Suspend CPU usage or trim memory footprint';
                searchContainer.style.display = 'flex';
                // Trigger refresh immediately on switching to process tab
                refreshProcesses();
            } else if (tabId === 'presets') {
                titleEl.textContent = 'Custom Presets';
                subEl.textContent = 'Batch process managers';
                searchContainer.style.display = 'none';
                loadPresets();
            } else if (tabId === 'settings') {
                titleEl.textContent = 'Rules & Safety';
                subEl.textContent = 'Automate memory management and process controls';
                searchContainer.style.display = 'none';
                loadRules();
            }
        });
    });
}

// --- Event Listeners Setup ---
function setupEventListeners() {
    // Refresh Button
    document.getElementById('refreshBtn').addEventListener('click', async () => {
        const btnText = document.querySelector('#refreshBtn .btn-text');
        btnText.textContent = 'Scanning...';
        setStatusBar("Scanning processes...", "scanning");
        
        if (state.currentTab === 'processes') {
            await refreshProcesses(true);
        } else {
            await refreshStats(true);
        }
        
        btnText.textContent = 'Refresh';
        setStatusBar("Ready", "ready");
    });
    
    // Mode Toggle Button (Safe Mode vs Advanced Mode)
    document.getElementById('modeToggleBtn').addEventListener('click', async () => {
        if (state.safeMode) {
            // Confirm switching to Advanced Mode
            const confirmed = await showConfirm(
                "Enable Advanced Mode?",
                "Advanced Mode displays ALL running processes. Suspending critical system processes may crash your computer. Proceed with caution."
            );
            if (confirmed) {
                state.safeMode = false;
                const modeBtn = document.getElementById('modeToggleBtn');
                modeBtn.classList.remove('btn-safe');
                modeBtn.classList.add('btn-advanced');
                document.querySelector('#modeToggleBtn .btn-text').textContent = 'Advanced';
                
                // Refresh list
                refreshProcesses();
            }
        } else {
            state.safeMode = true;
            const modeBtn = document.getElementById('modeToggleBtn');
            modeBtn.classList.remove('btn-advanced');
            modeBtn.classList.add('btn-safe');
            document.querySelector('#modeToggleBtn .btn-text').textContent = 'Safe Mode';
            
            // Refresh list
            refreshProcesses();
        }
    });

    // Exit Button
    document.getElementById('exitAppBtn').addEventListener('click', async () => {
        const confirmed = await showConfirm("Exit CryoTask?", "This will stop the background rules scheduler and close the application.");
        if (confirmed) {
            window.pywebview.api.exit_app();
        }
    });
    
    // Search Box
    const searchInput = document.getElementById('processSearch');
    const clearBtn = document.getElementById('searchClearBtn');
    
    searchInput.addEventListener('input', (e) => {
        state.searchQuery = e.target.value.trim();
        clearBtn.style.display = state.searchQuery ? 'block' : 'none';
        renderProcessList();
    });
    
    clearBtn.addEventListener('click', () => {
        searchInput.value = '';
        state.searchQuery = '';
        clearBtn.style.display = 'none';
        renderProcessList();
    });
    
    // Segmented Filters
    document.querySelectorAll('.segment-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.segment-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            state.filterMode = btn.getAttribute('data-filter');
            renderProcessList();
        });
    });
    
    // Sort Select
    document.getElementById('sortBySelect').addEventListener('change', (e) => {
        state.sortBy = e.target.value;
        renderProcessList();
    });

    // Preset Rules: Save Button
    document.getElementById('saveScheduleBtn').addEventListener('click', saveScheduleRules);

    // Preset Builder Actions
    document.getElementById('newPresetBtn').addEventListener('click', () => openPresetModal());
    document.getElementById('addAppToPresetBtn').addEventListener('click', addAppToPresetBuilder);
    document.getElementById('savePresetBtn').addEventListener('click', savePreset);

    // RAM threshold settings UI bindings
    const ramLimitToggle = document.getElementById('ramLimitToggle');
    const ramLimitSlider = document.getElementById('ramLimitSlider');
    const ramLimitSliderVal = document.getElementById('ramLimitSliderVal');
    const ramLimitSettings = document.getElementById('ramLimitSettings');
    const addThresholdAppBtn = document.getElementById('addThresholdAppBtn');
    
    ramLimitToggle.addEventListener('change', (e) => {
        state.rules.ram_threshold.enabled = e.target.checked;
        ramLimitSettings.style.opacity = e.target.checked ? '1' : '0.5';
        ramLimitSettings.style.pointerEvents = e.target.checked ? 'auto' : 'none';
        saveRules();
    });
    
    ramLimitSlider.addEventListener('input', (e) => {
        ramLimitSliderVal.textContent = `${e.target.value}%`;
    });
    
    ramLimitSlider.addEventListener('change', (e) => {
        state.rules.ram_threshold.threshold = parseInt(e.target.value);
        saveRules();
    });
    
    addThresholdAppBtn.addEventListener('click', () => {
        const select = document.getElementById('thresholdAppSelect');
        const app = select.value;
        if (app && !state.rules.ram_threshold.apps.includes(app)) {
            state.rules.ram_threshold.apps.push(app);
            saveRules();
            renderThresholdChips();
        }
        select.value = '';
    });
}

// --- Background Update Loop ---
function startPeriodicUpdates() {
    // 2s stats updates for dashboard graphs
    state.timers.stats = setInterval(refreshStats, 2000);
    
    // 4s process list updates
    state.timers.processes = setInterval(() => {
        if (state.currentTab === 'processes') {
            refreshProcesses(true);
        }
    }, 4000);
}

async function refreshData() {
    await refreshStats();
    if (state.currentTab === 'processes') {
        await refreshProcesses();
    }
}

async function refreshStats(silent = false) {
    try {
        const stats = await window.pywebview.api.get_system_stats();
        if (stats.error) return;
        
        // Update stats widgets
        document.getElementById('ramValue').textContent = `${stats.mem_used_gb} / ${stats.mem_total_gb} GB`;
        document.getElementById('ramPercent').textContent = `${stats.mem_percent}%`;
        document.getElementById('ramProgressBar').style.width = `${stats.mem_percent}%`;
        
        // Progress bar colors based on usage
        const ramProgress = document.getElementById('ramProgressBar');
        if (stats.mem_percent > 85) {
            ramProgress.style.background = 'linear-gradient(90deg, #ef4444, #f87171)';
        } else if (stats.mem_percent > 70) {
            ramProgress.style.background = 'linear-gradient(90deg, #f59e0b, #fbbf24)';
        } else {
            ramProgress.style.background = 'linear-gradient(90deg, var(--accent-blue) 0%, #60a5fa 100%)';
        }
        
        document.getElementById('cpuValue').textContent = `${stats.cpu_percent.toFixed(1)}%`;
        document.getElementById('cpuPercent').textContent = `${Math.round(stats.cpu_percent)}%`;
        document.getElementById('cpuProgressBar').style.width = `${stats.cpu_percent}%`;
        
        document.getElementById('procCountValue').textContent = stats.total_processes;
        
        // Update chart history
        updateChartData(stats.cpu_percent, stats.mem_percent);
        
        // If on dashboard, update suspended list
        if (state.currentTab === 'dashboard') {
            updateDashboardSuspendedList();
        }
    } catch (e) {
        console.error("Error refreshing stats:", e);
    }
}

async function refreshProcesses(silent = false) {
    try {
        const list = await window.pywebview.api.get_processes(state.searchQuery, state.safeMode);
        if (list.error) return;
        
        state.processes = list;
        renderProcessList();
        
        // Populate dropdown elements if they are empty
        populatePresetAppDropdowns();
    } catch (e) {
        console.error("Error refreshing processes:", e);
    }
}

// --- Chart rendering ---
let chartCanvas, chartCtx;
function setupChart() {
    chartCanvas = document.getElementById('resourceChart');
    chartCtx = chartCanvas.getContext('2d');
    
    // Fit canvas resolution to CSS size
    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);
}

function resizeCanvas() {
    if (!chartCanvas) return;
    const rect = chartCanvas.parentElement.getBoundingClientRect();
    chartCanvas.width = rect.width;
    chartCanvas.height = rect.height;
    drawChart();
}

function updateChartData(cpu, ram) {
    const history = state.chartHistory;
    history.cpu.push(cpu);
    history.ram.push(ram);
    
    if (history.cpu.length > 30) {
        history.cpu.shift();
        history.ram.shift();
    }
    
    drawChart();
}

function drawChart() {
    if (!chartCtx || !chartCanvas) return;
    const ctx = chartCtx;
    const width = chartCanvas.width;
    const height = chartCanvas.height;
    
    ctx.clearRect(0, 0, width, height);
    
    // Draw Grid lines
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.04)';
    ctx.lineWidth = 1;
    const rows = 4;
    for (let i = 0; i <= rows; i++) {
        const y = (height - 20) * (i / rows) + 10;
        ctx.beginPath();
        ctx.moveTo(40, y);
        ctx.lineTo(width - 10, y);
        ctx.stroke();
        
        // Draw labels
        ctx.fillStyle = 'var(--text-muted)';
        ctx.font = '10px Plus Jakarta Sans';
        ctx.fillText(`${100 - (i * 25)}%`, 8, y + 4);
    }
    
    const dataLength = state.chartHistory.cpu.length;
    if (dataLength < 2) return;
    
    // Draw lines helper
    const drawLine = (data, color, gradientStart, gradientStop) => {
        const points = [];
        const xStep = (width - 50) / 29;
        
        ctx.beginPath();
        for (let i = 0; i < data.length; i++) {
            const x = 40 + i * xStep;
            const y = height - 20 - ((data[i] / 100) * (height - 30)) - 10;
            points.push({ x, y });
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        }
        
        // Draw main line
        ctx.strokeStyle = color;
        ctx.lineWidth = 2.5;
        ctx.shadowColor = color;
        ctx.shadowBlur = 4;
        ctx.stroke();
        ctx.shadowBlur = 0; // Reset shadow
        
        // Fill under line with gradient
        ctx.lineTo(points[points.length - 1].x, height - 10);
        ctx.lineTo(points[0].x, height - 10);
        ctx.closePath();
        
        const gradient = ctx.createLinearGradient(0, 0, 0, height);
        gradient.addColorStop(0, gradientStart);
        gradient.addColorStop(1, gradientStop);
        ctx.fillStyle = gradient;
        ctx.fill();
        
        // Draw current value circle
        const lastPt = points[points.length - 1];
        ctx.beginPath();
        ctx.arc(lastPt.x, lastPt.y, 4, 0, Math.PI * 2);
        ctx.fillStyle = '#ffffff';
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.fill();
        ctx.stroke();
    };
    
    // Draw RAM (Blue)
    drawLine(
        state.chartHistory.ram, 
        '#0078d4', 
        'rgba(0, 120, 212, 0.15)', 
        'rgba(0, 120, 212, 0.0)'
    );
    
    // Draw CPU (Purple)
    drawLine(
        state.chartHistory.cpu, 
        '#7c3aed', 
        'rgba(124, 58, 237, 0.15)', 
        'rgba(124, 58, 237, 0.0)'
    );
}

// --- Dashboard Suspended List ---
function updateDashboardSuspendedList() {
    const listEl = document.getElementById('frozenList');
    const suspended = state.processes.filter(p => p.status === 'Suspended');
    
    if (suspended.length === 0) {
        listEl.innerHTML = `
            <div class="empty-state">
                <span class="empty-icon">❄️</span>
                <p>No suspended applications</p>
            </div>`;
        return;
    }
    
    listEl.innerHTML = '';
    suspended.forEach(app => {
        const item = document.createElement('div');
        item.className = 'frozen-item';
        item.innerHTML = `
            <span class="frozen-item-name">${app.name}</span>
            <div class="frozen-item-actions">
                <span class="frozen-item-mem">${app.memory} MB</span>
                <button class="btn-icon-only" onclick="resumeAppDashboard('${app.name}')" title="Resume App">▶</button>
            </div>
        `;
        listEl.appendChild(item);
    });
}

async function resumeAppDashboard(name) {
    setStatusBar(`Resuming ${name}...`, "scanning");
    const res = await window.pywebview.api.toggle_suspend(name, false);
    if (res.success) {
        // Refresh immediately
        await refreshProcesses();
        await refreshStats();
        setStatusBar("Ready", "ready");
    } else {
        setStatusBar(`Failed to resume ${name}`, "error");
    }
}

// --- Processes Rendering ---
function renderProcessList() {
    const listEl = document.getElementById('processList');
    
    // Filter
    let filtered = [...state.processes];
    if (state.filterMode === 'pinned') {
        filtered = filtered.filter(p => p.is_pinned);
    } else if (state.filterMode === 'suspended') {
        filtered = filtered.filter(p => p.status === 'Suspended');
    } else if (state.filterMode === 'scheduled') {
        filtered = filtered.filter(p => p.has_schedule);
    }
    
    // Sort
    if (state.sortBy === 'memory') {
        filtered.sort((a, b) => b.memory - a.memory);
    } else if (state.sortBy === 'cpu') {
        filtered.sort((a, b) => b.cpu - a.cpu);
    } else if (state.sortBy === 'name') {
        filtered.sort((a, b) => a.name.localeCompare(b.name));
    }
    
    // Pin sort hierarchy (always keep pinned at top unless explicitly searching/sorting by name)
    if (state.sortBy !== 'name' && state.filterMode !== 'pinned') {
        filtered.sort((a, b) => (b.is_pinned ? 1 : 0) - (a.is_pinned ? 1 : 0));
    }
    
    if (filtered.length === 0) {
        listEl.innerHTML = `
            <div class="empty-state">
                <span class="empty-icon">⚙️</span>
                <p>${state.searchQuery ? 'No processes match your search.' : 'No running processes found.'}</p>
            </div>`;
        
        // Update footer info count
        document.getElementById('statusMemorySummary').textContent = '';
        document.getElementById('statusBarText').textContent = '● No applications found';
        return;
    }
    
    listEl.innerHTML = '';
    
    filtered.forEach(proc => {
        const card = document.createElement('div');
        card.className = `proc-card ${proc.status === 'Suspended' ? 'suspended' : ''}`;
        
        let statusClass = '';
        if (proc.status === 'Suspended') statusClass = 'suspended';
        else if (proc.is_critical) statusClass = 'critical';
        
        // Buttons template
        let actionBtnText = '⏸ Suspend';
        let actionBtnClass = 'btn-secondary';
        if (proc.status === 'Suspended') {
            actionBtnText = '▶ Resume';
            actionBtnClass = 'btn-primary';
        } else if (proc.is_critical) {
            actionBtnText = '⚠️ Suspend';
            actionBtnClass = 'btn-secondary';
        }
        
        // Detail chips
        let chipsHtml = '';
        if (proc.is_pinned) chipsHtml += `<span class="badge badge-pin">⭐ PINNED</span>`;
        if (proc.has_schedule) chipsHtml += `<span class="badge badge-sch">🕐 SCH</span>`;
        if (proc.is_critical) chipsHtml += `<span class="badge badge-sys">⚠️ SYSTEM</span>`;
        
        card.innerHTML = `
            <div class="status-dot-wrapper">
                <div class="status-dot ${statusClass}"></div>
            </div>
            
            <button class="action-icon-btn ${proc.is_pinned ? 'pinned' : ''}" onclick="togglePin('${proc.name}')" title="Pin application">
                ${proc.is_pinned ? '★' : '☆'}
            </button>
            
            <button class="action-icon-btn ${proc.has_schedule ? 'scheduled' : ''}" onclick="openScheduleModal('${proc.name}')" title="Rules scheduler">
                ⏰
            </button>
            
            <div class="proc-info">
                <span class="proc-name" title="${proc.name}">${proc.name}</span>
                <div class="proc-details">
                    <span>${proc.memory} MB</span>
                    <span class="bullet">•</span>
                    <span>${proc.count} process${proc.count > 1 ? 'es' : ''}</span>
                    ${proc.cpu > 0 ? `<span class="bullet">•</span><span>CPU: ${proc.cpu}%</span>` : ''}
                    ${chipsHtml}
                </div>
            </div>
            
            <div class="proc-actions" style="grid-column: 5;">
                <button class="btn btn-secondary btn-trim-action" onclick="trimProcess(this, '${proc.name}')" ${proc.status === 'Suspended' ? 'disabled' : ''}>
                    ⚡ Trim
                </button>
            </div>
            
            <div class="proc-actions" style="grid-column: 6;">
                <button class="btn ${actionBtnClass}" onclick="toggleSuspend(this, '${proc.name}', ${proc.status !== 'Suspended'})">
                    ${actionBtnText}
                </button>
            </div>
        `;
        
        listEl.appendChild(card);
    });
    
    // Update footer info
    const totalManagedMemory = (state.processes.reduce((acc, p) => acc + p.memory, 0) / 1024).toFixed(2);
    document.getElementById('statusMemorySummary').textContent = `Total Memory: ${totalManagedMemory} GB`;
    
    const count = filtered.length;
    const modeText = state.safeMode ? 'Safe Mode' : 'Advanced Mode';
    document.getElementById('statusBarText').textContent = `● Showing ${count} of ${state.processes.length} apps (${modeText})`;
}

// --- Action Bindings ---
async function togglePin(name) {
    const res = await window.pywebview.api.toggle_pin(name);
    if (res.success) {
        refreshProcesses(true);
    }
}

async function trimProcess(btn, name) {
    btn.disabled = true;
    const originalText = btn.textContent;
    btn.textContent = 'Working...';
    
    const res = await window.pywebview.api.trim_process(name);
    if (res.success) {
        btn.textContent = '✓ Done';
        btn.style.borderColor = 'var(--accent-green)';
        btn.style.color = '#a7f3d0';
        
        // Refresh this specific card after a delay
        setTimeout(async () => {
            await refreshProcesses(true);
            await refreshStats(true);
        }, 1200);
    } else {
        btn.textContent = 'Failed';
        btn.disabled = false;
        setTimeout(() => btn.textContent = originalText, 2000);
    }
}

async function toggleSuspend(btn, name, shouldSuspend) {
    btn.disabled = true;
    const originalText = btn.textContent;
    btn.textContent = shouldSuspend ? 'Pausing...' : 'Resuming...';
    
    const res = await window.pywebview.api.toggle_suspend(name, shouldSuspend);
    if (res.success) {
        await refreshProcesses(true);
        await refreshStats(true);
    } else {
        showConfirm("Error", `Failed to change state for ${name}`);
        btn.textContent = originalText;
        btn.disabled = false;
    }
}

// --- Presets Tab Rendering ---
function renderPresetGrid() {
    const grid = document.getElementById('presetsGrid');
    grid.innerHTML = '';
    
    const keys = Object.keys(state.presets);
    if (keys.length === 0) {
        grid.innerHTML = `
            <div class="empty-state" style="grid-column: 1/-1;">
                <span class="empty-icon">⚡</span>
                <p>No presets created yet. Click "+ New Preset" to configure one.</p>
            </div>`;
        return;
    }
    
    keys.forEach(name => {
        const apps = state.presets[name];
        const appCount = Object.keys(apps).length;
        
        // Create summaries string
        const summaryParts = [];
        Object.entries(apps).slice(0, 3).forEach(([app, action]) => {
            summaryParts.push(`${app} (${action})`);
        });
        let summaryText = summaryParts.join(', ');
        if (appCount > 3) summaryText += '...';
        
        const card = document.createElement('div');
        card.className = 'preset-card';
        card.innerHTML = `
            <div class="preset-header">
                <h4>${name}</h4>
                <span class="preset-apps-count">${appCount} app${appCount !== 1 ? 's' : ''}</span>
            </div>
            <div class="preset-body">
                <p class="preset-summary">${summaryText}</p>
            </div>
            <div class="preset-footer-actions">
                <button class="btn btn-secondary btn-sm" onclick="editPreset('${name}')">✏️ Edit</button>
                <button class="btn btn-secondary btn-sm" style="color: var(--accent-red);" onclick="deletePreset('${name}')">🗑️ Delete</button>
                <button class="btn btn-primary btn-sm" onclick="applyPreset('${name}')">▶ Apply</button>
            </div>
        `;
        
        grid.appendChild(card);
    });
}

async function loadPresets() {
    const presets = await window.pywebview.api.get_presets();
    state.presets = presets || {};
    renderPresetGrid();
}

async function applyPreset(name) {
    setStatusBar(`Applying preset ${name}...`, "scanning");
    const res = await window.pywebview.api.apply_preset(name);
    
    if (res.success) {
        showAlert(
            "Preset Applied",
            `Successfully ran preset '${name}'\n\nTargeted: ${res.targeted} apps\nSuccessfully actioned: ${res.success_count} apps`,
            "✅"
        );
        refreshProcesses();
        refreshStats();
        setStatusBar("Ready", "ready");
    } else {
        showAlert("Error", `Failed to apply preset: ${res.error}`, "❌");
        setStatusBar("Ready", "ready");
    }
}

async function deletePreset(name) {
    const confirmed = await showConfirm("Delete Preset?", `Are you sure you want to delete preset '${name}'?`);
    if (confirmed) {
        delete state.presets[name];
        await window.pywebview.api.save_presets(state.presets);
        loadPresets();
    }
}

// Preset builder actions
function openPresetModal(name = null) {
    state.editingPresetName = name;
    state.tempPresetApps = name ? { ...state.presets[name] } : {};
    
    document.getElementById('presetModalTitle').textContent = name ? `Edit Preset: ${name}` : 'Create Preset';
    document.getElementById('presetNameInput').value = name || '';
    
    if (name) {
        document.getElementById('presetNameInput').disabled = true; // Lock name edit
    } else {
        document.getElementById('presetNameInput').disabled = false;
    }
    
    renderPresetBuilderList();
    openModal('presetModal');
}

function renderPresetBuilderList() {
    const listEl = document.getElementById('presetAppsList');
    listEl.innerHTML = '';
    
    const entries = Object.entries(state.tempPresetApps);
    if (entries.length === 0) {
        listEl.innerHTML = `
            <div class="empty-state">
                <p>No actions added yet.</p>
            </div>`;
        return;
    }
    
    entries.forEach(([app, action]) => {
        const item = document.createElement('div');
        item.className = 'builder-item';
        item.innerHTML = `
            <div class="builder-item-info">
                <span class="builder-item-name">${app}</span>
                <span class="builder-item-action">${action}</span>
            </div>
            <button class="builder-item-remove" onclick="removeAppFromPresetBuilder('${app}')">✕</button>
        `;
        listEl.appendChild(item);
    });
}

function addAppToPresetBuilder() {
    const select = document.getElementById('presetAppSelect');
    const actionSelect = document.getElementById('presetActionSelect');
    
    const app = select.value;
    const action = actionSelect.value;
    
    if (app) {
        state.tempPresetApps[app] = action;
        renderPresetBuilderList();
    }
}

function removeAppFromPresetBuilder(app) {
    delete state.tempPresetApps[app];
    renderPresetBuilderList();
}

async function savePreset() {
    const nameInput = document.getElementById('presetNameInput');
    const name = nameInput.value.trim();
    
    if (!name) {
        showAlert("Validation Error", "Please provide a preset name.", "⚠️");
        return;
    }
    
    if (Object.keys(state.tempPresetApps).length === 0) {
        showAlert("Validation Error", "Add at least one application to the preset.", "⚠️");
        return;
    }
    
    state.presets[name] = state.tempPresetApps;
    const res = await window.pywebview.api.save_presets(state.presets);
    if (res.success) {
        closeModal('presetModal');
        loadPresets();
    } else {
        showAlert("Error", "Failed to save preset.", "❌");
    }
}

function editPreset(name) {
    openPresetModal(name);
}

function populatePresetAppDropdowns() {
    const selectPreset = document.getElementById('presetAppSelect');
    const selectSettings = document.getElementById('thresholdAppSelect');
    
    // Sort process names
    const names = [...new Set(state.processes.map(p => p.name))].sort();
    
    const populate = (selectEl) => {
        const currentVal = selectEl.value;
        selectEl.innerHTML = `<option value="">-- Choose App --</option>`;
        names.forEach(name => {
            const opt = document.createElement('option');
            opt.value = name;
            opt.textContent = name;
            selectEl.appendChild(opt);
        });
        selectEl.value = currentVal;
    };
    
    populate(selectPreset);
    populate(selectSettings);
}

// --- Rules & Safety / Settings Tab ---
async function loadRules() {
    const rules = await window.pywebview.api.get_rules();
    state.rules = rules;
    
    // Update RAM Threshold Settings UI
    const toggle = document.getElementById('ramLimitToggle');
    const slider = document.getElementById('ramLimitSlider');
    const sliderVal = document.getElementById('ramLimitSliderVal');
    const settingsBox = document.getElementById('ramLimitSettings');
    
    const config = rules.ram_threshold || { enabled: false, threshold: 80, apps: [] };
    
    toggle.checked = config.enabled;
    slider.value = config.threshold;
    sliderVal.textContent = `${config.threshold}%`;
    
    settingsBox.style.opacity = config.enabled ? '1' : '0.5';
    settingsBox.style.pointerEvents = config.enabled ? 'auto' : 'none';
    
    renderThresholdChips();
}

function renderThresholdChips() {
    const container = document.getElementById('thresholdAppChips');
    container.innerHTML = '';
    
    const apps = state.rules.ram_threshold.apps || [];
    if (apps.length === 0) {
        container.innerHTML = `<span style="font-size:11px; color:var(--text-muted);">No apps targeted for threshold auto-suspend.</span>`;
        return;
    }
    
    apps.forEach(app => {
        const chip = document.createElement('span');
        chip.className = 'chip';
        chip.innerHTML = `
            ${app}
            <span class="chip-close" onclick="removeThresholdApp('${app}')">✕</span>
        `;
        container.appendChild(chip);
    });
}

function removeThresholdApp(app) {
    state.rules.ram_threshold.apps = state.rules.ram_threshold.apps.filter(a => a !== app);
    saveRules();
    renderThresholdChips();
}

async function saveRules() {
    await window.pywebview.api.save_rules(state.rules);
}

// --- Modal Helper Functions ---
function openModal(id) {
    const el = document.getElementById(id);
    el.classList.add('open');
}

function closeModal(id) {
    const el = document.getElementById(id);
    el.classList.remove('open');
}

// Modal: Schedule rules dialog
function openScheduleModal(appName) {
    state.activeScheduleApp = appName;
    document.getElementById('scheduleAppTitle').textContent = appName;
    
    // Load config
    const trimConfig = state.rules.periodic_trim[appName] || { enabled: false, interval: 15 };
    
    document.getElementById('periodicTrimToggle').checked = trimConfig.enabled;
    document.getElementById('periodicTrimInterval').value = trimConfig.interval;
    
    // Toggle fields based on enabled status
    const trimSettings = document.getElementById('periodicTrimSettings');
    trimSettings.style.opacity = trimConfig.enabled ? '1' : '0.5';
    trimSettings.style.pointerEvents = trimConfig.enabled ? 'auto' : 'none';
    
    // Bind toggle sub-listener
    document.getElementById('periodicTrimToggle').onchange = (e) => {
        trimSettings.style.opacity = e.target.checked ? '1' : '0.5';
        trimSettings.style.pointerEvents = e.target.checked ? 'auto' : 'none';
    };
    
    openModal('scheduleModal');
}

async function saveScheduleRules() {
    const appName = state.activeScheduleApp;
    const enabled = document.getElementById('periodicTrimToggle').checked;
    const interval = parseInt(document.getElementById('periodicTrimInterval').value) || 15;
    
    if (enabled) {
        state.rules.periodic_trim[appName] = {
            enabled: true,
            interval: interval,
            last_run: 0
        };
    } else {
        delete state.rules.periodic_trim[appName];
    }
    
    await saveRules();
    closeModal('scheduleModal');
    refreshProcesses(true);
}

// --- Custom Confirmation Dialog & Alert ---
let alertResolve = null;
function showAlert(title, message, icon = '⚠️') {
    document.getElementById('alertTitle').textContent = title;
    document.getElementById('alertMessage').textContent = message;
    document.getElementById('alertIcon').textContent = icon;
    
    document.getElementById('alertCancelBtn').style.display = 'none'; // Only OK button
    document.getElementById('alertConfirmBtn').textContent = 'OK';
    document.getElementById('alertConfirmBtn').onclick = () => {
        closeModal('alertModal');
    };
    
    openModal('alertModal');
}

function showConfirm(title, message, icon = '⚠️') {
    return new Promise((resolve) => {
        document.getElementById('alertTitle').textContent = title;
        document.getElementById('alertMessage').textContent = message;
        document.getElementById('alertIcon').textContent = icon;
        
        const cancelBtn = document.getElementById('alertCancelBtn');
        const confirmBtn = document.getElementById('alertConfirmBtn');
        
        cancelBtn.style.display = 'block';
        cancelBtn.textContent = 'Cancel';
        confirmBtn.textContent = 'Confirm';
        
        cancelBtn.onclick = () => {
            closeModal('alertModal');
            resolve(false);
        };
        
        confirmBtn.onclick = () => {
            closeModal('alertModal');
            resolve(true);
        };
        
        openModal('alertModal');
    });
}

// --- Footer Status helper ---
function setStatusBar(text, mode = "ready") {
    const textEl = document.getElementById('statusBarText');
    const dotEl = document.getElementById('statusDot');
    
    textEl.textContent = `● ${text}`;
    dotEl.className = 'status-dot-pulse';
    
    if (mode === 'scanning') {
        dotEl.classList.add('scanning');
    }
}

// --- Mock API for Local Browser Testing ---
function setupMockApi() {
    window.pywebview = {
        api: {
            get_system_stats: async () => ({
                mem_used_gb: (8.4 + Math.random() * 0.4),
                mem_total_gb: 16.0,
                mem_percent: Math.round(50 + Math.random() * 10),
                cpu_percent: Math.random() * 40,
                total_processes: 210 + Math.floor(Math.random() * 10)
            }),
            get_processes: async (query, safe) => {
                const mock = [
                    { name: "chrome.exe", status: "Running", memory: 1240.5, count: 18, cpu: 12.4, is_critical: false, is_pinned: true, has_schedule: true },
                    { name: "discord.exe", status: "Running", memory: 340.2, count: 4, cpu: 0.5, is_critical: false, is_pinned: true, has_schedule: false },
                    { name: "code.exe", status: "Running", memory: 890.1, count: 8, cpu: 2.1, is_critical: false, is_pinned: false, has_schedule: false },
                    { name: "explorer.exe", status: "Running", memory: 180.4, count: 1, cpu: 0.2, is_critical: true, is_pinned: false, has_schedule: false },
                    { name: "spotify.exe", status: "Suspended", memory: 120.1, count: 3, cpu: 0.0, is_critical: false, is_pinned: false, has_schedule: false },
                    { name: "steam.exe", status: "Running", memory: 280.9, count: 2, cpu: 0.1, is_critical: false, is_pinned: false, has_schedule: false }
                ];
                if (safe) return mock.filter(p => !p.is_critical || p.name === 'explorer.exe'); // explorer window is visible
                return mock;
            },
            toggle_suspend: async (name, state) => ({ success: true }),
            trim_process: async (name) => ({ success: true, new_memory: 50 }),
            toggle_pin: async (name) => ({ success: true, is_pinned: true }),
            get_rules: async () => ({
                periodic_trim: { "chrome.exe": { enabled: true, interval: 15 } },
                ram_threshold: { enabled: true, threshold: 80, apps: ["chrome.exe"] }
            }),
            save_rules: async (rules) => ({ success: true }),
            get_presets: async () => ({
                "Gaming Mode": { "chrome.exe": "Suspend", "discord.exe": "Trim" },
                "Clean Memory": { "chrome.exe": "Trim", "code.exe": "Trim" }
            }),
            save_presets: async (presets) => ({ success: true }),
            apply_preset: async (name) => ({ success: true, targeted: 2, success_count: 2 }),
            exit_app: () => { alert("Exit app triggered!"); }
        }
    };
}
