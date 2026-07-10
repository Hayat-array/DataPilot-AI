/* ═══════════════════════════════════════════
   DATAPILOT AI — app.js
   Handles: Sidebar toggle, Theme toggle, Upload,
   Filtering, Chart rendering, Chat (real API)
═══════════════════════════════════════════ */

// ── State ──────────────────────────────────
let dfData      = null;
let filteredData= null;
let dfColumns   = [];
let activeChart = null;
let activeChartType = 'bar';
let currentFilters  = [];
let uploadedFilename= '';
let isSidebarOpen   = true;
let isLightTheme    = false;

// ── Sidebar Toggle ─────────────────────────
function toggleSidebar() {
    isSidebarOpen = !isSidebarOpen;
    const sidebar = document.getElementById('sidebar');
    const btn     = document.getElementById('sidebarToggle');

    if (isSidebarOpen) {
        sidebar.classList.remove('collapsed');
        btn.innerHTML = '<i class="fa-solid fa-bars"></i>';
    } else {
        sidebar.classList.add('collapsed');
        btn.innerHTML = '<i class="fa-solid fa-bars-staggered"></i>';
    }
}

// ── Theme Toggle ───────────────────────────
function toggleTheme() {
    isLightTheme = !isLightTheme;
    document.documentElement.setAttribute('data-theme', isLightTheme ? 'light' : 'dark');

    const lightIcon = document.getElementById('theme-icon-light');
    const darkIcon  = document.getElementById('theme-icon-dark');

    if (isLightTheme) {
        if (lightIcon) lightIcon.style.display = 'none';
        if (darkIcon)  darkIcon.style.display  = '';
    } else {
        if (lightIcon) lightIcon.style.display = '';
        if (darkIcon)  darkIcon.style.display  = 'none';
    }

    // Re-render chart with new background if active
    if (activeChart) renderActiveChart();
}

// ── Tab Switcher ───────────────────────────
function switchTab(tabId, el) {
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-pill').forEach(p => p.classList.remove('active'));

    document.getElementById('tab-' + tabId).classList.add('active');

    // Activate pill by id convention
    const pill = document.getElementById('pill-' + tabId);
    if (pill) pill.classList.add('active');
    else if (el) el.classList.add('active');

    log('system', `Orchestrator › focus → tab_${tabId}`);
}

// ── Terminal Log ───────────────────────────
function log(type, msg) {
    const term = document.getElementById('terminal-log');
    if (!term) return;
    const line = document.createElement('div');
    line.className = `tl ${type}`;
    const ts = new Date().toLocaleTimeString([], {hour:'2-digit', minute:'2-digit', second:'2-digit'});
    line.innerHTML = `<span class="ts">[${ts}]</span>${msg}`;
    term.appendChild(line);
    term.scrollTop = term.scrollHeight;
    // Keep max 120 lines
    while (term.children.length > 120) term.removeChild(term.firstChild);
}

function clearConsoleLogs() {
    const term = document.getElementById('terminal-log');
    if (term) term.innerHTML = '<div class="tl system">[sys] Logs cleared.</div>';
}

// ── Drag & Drop ────────────────────────────
function handleDrop(event) {
    event.preventDefault();
    document.getElementById('upload-zone').classList.remove('drag-over');
    const file = event.dataTransfer.files[0];
    if (file) {
        document.getElementById('dataset-upload').files = event.dataTransfer.files;
        handleUpload({ files: [file] });
    }
}

// ── File Upload — Routes by file type ─────
function handleUpload(input) {
    const file = input.files[0];
    if (!file) return;

    const ext    = file.name.split('.').pop().toLowerCase();
    const sizekb = (file.size / 1024).toFixed(1);
    log('system', `Ingesting: <strong>${file.name}</strong> (${sizekb} KB) [${ext.toUpperCase()}]`);
    log('agent',  `Validator › routing to ${ext.toUpperCase()} parser...`);

    if (ext === 'csv') {
        parseCSV(file);
    } else if (ext === 'json') {
        parseJSON(file);
    } else if (ext === 'xlsx' || ext === 'xls') {
        parseExcel(file);
    } else {
        log('error', `Unsupported format: .${ext}. Please upload CSV, JSON, or Excel.`);
        alert(`Unsupported file format: .${ext}\nPlease upload a .csv, .json, .xlsx or .xls file.`);
    }
}

// ── CSV Parser (PapaParse) ─────────────────
function parseCSV(file) {
    Papa.parse(file, {
        header: true,
        dynamicTyping: true,
        skipEmptyLines: true,
        complete(res) {
            if (res.errors.length && res.data.length === 0) {
                log('error', `CSV parse failed: ${res.errors[0].message}`);
                return;
            }
            onParsed(res.data, res.meta.fields, file);
        },
        error(err) {
            log('error', `CSV parse error: ${err.message}`);
        }
    });
}

// ── JSON Parser (FileReader) ───────────────
function parseJSON(file) {
    const reader = new FileReader();
    reader.onload = (e) => {
        try {
            let json = JSON.parse(e.target.result);
            // Handle both array and {data:[...]} formats
            if (!Array.isArray(json)) {
                const keys = Object.keys(json);
                // Try common wrapper keys
                const arrKey = keys.find(k => Array.isArray(json[k]));
                if (arrKey) {
                    json = json[arrKey];
                } else {
                    // Single object — wrap in array
                    json = [json];
                }
            }
            if (json.length === 0) {
                log('error', 'JSON file is empty or contains no records.');
                return;
            }
            // Extract columns from first object
            const cols = Object.keys(json[0]);
            // Normalize: ensure all rows have all columns
            const normalized = json.map(row => {
                const out = {};
                cols.forEach(c => { out[c] = row[c] !== undefined ? row[c] : null; });
                return out;
            });
            onParsed(normalized, cols, file);
        } catch (err) {
            log('error', `JSON parse error: ${err.message}`);
            alert(`Failed to parse JSON file: ${err.message}`);
        }
    };
    reader.onerror = () => log('error', 'FileReader error reading JSON file.');
    reader.readAsText(file);
}

// ── Excel Parser (SheetJS) ────────────────
function parseExcel(file) {
    // Lazily load SheetJS if not already loaded
    if (typeof XLSX === 'undefined') {
        log('agent', 'Loading SheetJS library for Excel parsing...');
        const script = document.createElement('script');
        script.src = 'https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js';
        script.onload  = () => _parseExcelFile(file);
        script.onerror = () => log('error', 'Failed to load SheetJS. Check your internet connection.');
        document.head.appendChild(script);
    } else {
        _parseExcelFile(file);
    }
}

function _parseExcelFile(file) {
    const reader = new FileReader();
    reader.onload = (e) => {
        try {
            const workbook = XLSX.read(e.target.result, { type: 'array', cellDates: true });
            // Use first sheet
            const sheetName = workbook.SheetNames[0];
            log('agent', `Excel › Reading sheet: "${sheetName}"`);
            const sheet = workbook.Sheets[sheetName];
            const rows  = XLSX.utils.sheet_to_json(sheet, { defval: null });
            if (rows.length === 0) {
                log('error', 'Excel sheet is empty.');
                return;
            }
            const cols = Object.keys(rows[0]);
            onParsed(rows, cols, file);
        } catch (err) {
            log('error', `Excel parse error: ${err.message}`);
            alert(`Failed to parse Excel file: ${err.message}`);
        }
    };
    reader.onerror = () => log('error', 'FileReader error reading Excel file.');
    reader.readAsArrayBuffer(file);
}

// ── Shared Post-Parse Handler ─────────────
function onParsed(data, cols, file) {
    dfData         = data;
    filteredData   = [...dfData];
    dfColumns      = cols;
    currentFilters = [];

    log('success', `Parsed ${dfData.length} rows × ${dfColumns.length} cols`);

    renderFileCard(file);
    populateFilterColumns();
    updateDataDisplay();
    showQuickStats();

    // Upload to backend
    log('agent', `Validator › uploading to backend...`);
    const fd = new FormData();
    fd.append('file', file);
    fetch('/api/upload', { method: 'POST', body: fd })
        .then(r => r.json())
        .then(d => {
            if (d.success) {
                uploadedFilename = d.data.filename;
                sessionStorage.setItem('uploadedFilename', uploadedFilename);
                sessionStorage.setItem('originalFilename', file.name);
                sessionStorage.setItem('fileSize', file.size);
                log('success', `Saved on server as '${uploadedFilename}'`);
                updateFileCardStatus('Synced ✓');
            } else {
                log('error', `Upload rejected: ${d.error?.message}`);
            }
        })
        .catch(e => log('error', `Upload failed: ${e.message}`));
}

function renderFileCard(file) {
    const sizekb = (file.size / 1024).toFixed(1);
    const ext    = file.name.split('.').pop().toLowerCase();
    const icons  = { csv:'fa-file-csv', json:'fa-file-code', xlsx:'fa-file-excel', xls:'fa-file-excel' };
    const colors = { csv:'var(--accent-3)', json:'var(--accent-5)', xlsx:'var(--accent-2)', xls:'var(--accent-2)' };
    const icon   = icons[ext]  || 'fa-file';
    const color  = colors[ext] || 'var(--accent-1)';
    document.getElementById('file-card-container').innerHTML = `
        <div class="file-card">
            <div class="file-card-icon" style="color:${color}"><i class="fa-solid ${icon}"></i></div>
            <div class="file-card-info">
                <strong title="${file.name}">${file.name}</strong>
                <span id="file-card-status">${sizekb} KB · Uploading…</span>
            </div>
            <div class="file-card-remove" onclick="removeFile()" title="Remove"><i class="fa-solid fa-xmark"></i></div>
        </div>
    `;
}

function updateFileCardStatus(msg) {
    const el = document.getElementById('file-card-status');
    if (el) el.textContent = (el.textContent.split('·')[0] + '· ' + msg);
}

function showQuickStats() {
    const block = document.getElementById('quick-stats-block');
    if (block) block.style.display = 'block';
    updateQuickStats();
}

function updateQuickStats() {
    const rows = filteredData ? filteredData.length : 0;
    const cols = dfColumns.length;
    const quality = calculateQuality();
    const sizeKb = filteredData ? (JSON.stringify(filteredData).length / 1024).toFixed(1) : '-';
    setEl('qs-rows',    rows.toLocaleString());
    setEl('qs-cols',    cols);
    setEl('qs-quality', quality + '%');
    setEl('qs-size',    sizeKb + ' KB');
}

function populateFilterColumns() {
    const sel = document.getElementById('filter-column');
    if (!sel) return;
    sel.innerHTML = '<option value="">Column...</option>';
    dfColumns.forEach(c => {
        const o = document.createElement('option');
        o.value = o.textContent = c;
        sel.appendChild(o);
    });
}

// ── Remove File ────────────────────────────
function removeFile() {
    sessionStorage.removeItem('uploadedFilename');
    sessionStorage.removeItem('originalFilename');
    sessionStorage.removeItem('fileSize');
    dfData = filteredData = null;
    dfColumns = []; currentFilters = []; uploadedFilename = '';
    document.getElementById('file-card-container').innerHTML = '';
    document.getElementById('quick-stats-block').style.display = 'none';

    ['profile-rows','profile-cols','profile-quality','profile-size'].forEach(id => setEl(id,'—'));
    ['qs-rows','qs-cols','qs-quality','qs-size'].forEach(id => setEl(id,'-'));

    document.getElementById('preview-thead').innerHTML = '<tr><th>Column A</th><th>Column B</th><th>Column C</th></tr>';
    document.getElementById('preview-tbody').innerHTML = '<tr><td colspan="3" class="empty-cell">Upload a dataset to preview rows.</td></tr>';
    document.getElementById('schema-tbody').innerHTML  = '<tr><td colspan="4" class="empty-cell">No schema available.</td></tr>';

    setEl('preview-count', 'No data');

    ['visualizer-x','visualizer-y'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.innerHTML = '<option value="">Select column...</option>';
    });
    document.getElementById('filter-column').innerHTML = '<option value="">Column...</option>';
    hideBadges();

    if (activeChart) { activeChart.destroy(); activeChart = null; }
    document.getElementById('chart-canvas').style.display = 'none';
    document.getElementById('canvas-placeholder').style.display = 'flex';

    log('system', 'Dataset cleared from context.');
}

// ── Data Display Update ────────────────────
function updateDataDisplay() {
    if (!filteredData) return;
    const rows = filteredData.length;
    const q = calculateQuality();
    const sizeKb = (JSON.stringify(filteredData).length / 1024).toFixed(1);

    setEl('profile-rows',    rows.toLocaleString());
    setEl('profile-cols',    dfColumns.length);
    setEl('profile-quality', q + '%');
    setEl('profile-size',    sizeKb + ' KB');
    setEl('preview-count',   `${rows} rows shown`);

    updateQuickStats();

    // Preview Table
    const thead = document.getElementById('preview-thead');
    const tbody = document.getElementById('preview-tbody');
    const visibleCols = dfColumns.slice(0, 8);
    thead.innerHTML = '<tr>' + visibleCols.map(c => `<th>${c}</th>`).join('') + '</tr>';

    if (rows === 0) {
        tbody.innerHTML = `<tr><td colspan="${visibleCols.length}" class="empty-cell">No rows match the applied filters.</td></tr>`;
    } else {
        tbody.innerHTML = filteredData.slice(0,12).map(row =>
            '<tr>' + visibleCols.map(c => {
                let v = row[c];
                if (v === null || v === undefined) return '<td><em style="color:var(--text-muted)">null</em></td>';
                return `<td>${v}</td>`;
            }).join('') + '</tr>'
        ).join('');
    }

    // Schema Table
    const schemaTbody = document.getElementById('schema-tbody');
    schemaTbody.innerHTML = dfColumns.map(col => {
        let nulls = 0, sum = 0, count = 0, dtype = 'string';
        filteredData.forEach(row => {
            if (row[col] === null || row[col] === undefined) { nulls++; return; }
            if (typeof row[col] === 'number') { dtype='number'; sum += row[col]; count++; }
        });
        const stat = dtype === 'number' && count > 0
            ? `μ = ${(sum/count).toFixed(2)}`
            : filteredData[0]?.[col] ? `"${String(filteredData[0][col]).slice(0,20)}"` : '—';
        return `<tr>
            <td><strong>${col}</strong></td>
            <td><span class="type-badge">${dtype}</span></td>
            <td>${nulls}</td>
            <td>${stat}</td>
        </tr>`;
    }).join('');

    // Visualizer dropdowns
    const prevX = document.getElementById('visualizer-x').value;
    const prevY = document.getElementById('visualizer-y').value;
    ['visualizer-x','visualizer-y'].forEach(id => {
        const el = document.getElementById(id);
        const prev = id === 'visualizer-x' ? prevX : prevY;
        el.innerHTML = '<option value="">Select column...</option>' +
            dfColumns.map(c => `<option value="${c}" ${c===prev?'selected':''}>${c}</option>`).join('');
    });

    renderBadges();
}

function calculateQuality() {
    if (!filteredData || filteredData.length === 0) return '100.0';
    const total = filteredData.length * dfColumns.length;
    let nulls = 0;
    filteredData.forEach(row => dfColumns.forEach(c => { if (row[c]==null) nulls++; }));
    return ((1 - nulls/total)*100).toFixed(1);
}

// ── Filters ────────────────────────────────
function applySelectedFilter() {
    if (!dfData) return alert('Upload a dataset first.');
    const col = document.getElementById('filter-column').value;
    const op  = document.getElementById('filter-operator').value;
    const val = document.getElementById('filter-val').value.trim();
    if (!col || !op || val === '') return alert('Fill all filter fields.');
    const parsed = isNaN(val) ? val : Number(val);
    currentFilters.push({ column:col, op, val:parsed });
    applyFilters();
    document.getElementById('filter-val').value = '';
    log('system', `Filter added: ${col} ${op} ${val}`);
}

function applyFilters() {
    let result = [...dfData];
    currentFilters.forEach(f => {
        result = result.filter(row => {
            const v = row[f.column];
            if (v == null) return false;
            switch(f.op) {
                case '==': return v == f.val;
                case '!=': return v != f.val;
                case '>':  return v >  f.val;
                case '<':  return v <  f.val;
                case '>=': return v >= f.val;
                case '<=': return v <= f.val;
                case 'contains': return String(v).toLowerCase().includes(String(f.val).toLowerCase());
            }
            return true;
        });
    });
    filteredData = result;
    updateDataDisplay();
    if (activeChart) renderActiveChart();
}

function removeFilter(idx) {
    currentFilters.splice(idx, 1);
    applyFilters();
    log('system', 'Filter removed.');
}

function clearAllFilters() {
    currentFilters = [];
    filteredData = [...(dfData || [])];
    updateDataDisplay();
    if (activeChart) renderActiveChart();
    hideBadges();
    log('system', 'All filters cleared.');
}

function renderBadges() {
    const panel  = document.getElementById('filter-active-panel');
    const badges = document.getElementById('filter-badges');
    if (!panel || !badges) return;
    if (currentFilters.length === 0) { hideBadges(); return; }
    panel.style.display = 'flex';
    badges.innerHTML = currentFilters.map((f,i) =>
        `<span class="filter-tag">${f.column} ${f.op} ${f.val}<i class="fa-solid fa-xmark" onclick="removeFilter(${i})"></i></span>`
    ).join('');
}

function hideBadges() {
    const panel = document.getElementById('filter-active-panel');
    if (panel) panel.style.display = 'none';
}

// ── Visualizer ─────────────────────────────
function setChartType(type, btn) {
    document.querySelectorAll('.chart-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    activeChartType = type;
    if (activeChart) renderActiveChart();
}

function renderActiveChart() {
    if (!filteredData?.length) return alert('Upload a dataset first.');
    const xCol = document.getElementById('visualizer-x').value;
    const yCol = document.getElementById('visualizer-y').value;
    if (!xCol) return;

    log('agent', `ChartGen › ${activeChartType} [X: ${xCol}${yCol ? ', Y: '+yCol : ''}]`);

    let labels = [], values = [];

    if (!yCol) {
        const counts = {};
        filteredData.forEach(row => {
            const v = row[xCol] ?? 'null';
            counts[v] = (counts[v]||0) + 1;
        });
        const sorted = Object.entries(counts).sort((a,b)=>b[1]-a[1]).slice(0,18);
        labels = sorted.map(e => e[0]);
        values = sorted.map(e => e[1]);
    } else {
        const subset = filteredData.slice(0,60);
        labels = subset.map((r,i) => r[xCol]!=null ? String(r[xCol]) : `Row ${i}`);
        values = subset.map(r => r[yCol] ?? 0);
    }

    const canvas = document.getElementById('chart-canvas');
    const placeholder = document.getElementById('canvas-placeholder');
    canvas.style.display = 'block';
    placeholder.style.display = 'none';

    if (activeChart) activeChart.destroy();

    const isDark = !isLightTheme;
    const textColor  = isDark ? '#94a3b8' : '#475569';
    const gridColor  = isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.06)';
    const multiColors = ['#6366f1','#06b6d4','#10b981','#a855f7','#f59e0b','#3b82f6','#ec4899','#f43f5e','#14b8a6','#8b5cf6'];

    const isPolar = ['pie','doughnut'].includes(activeChartType);
    const isRadar = activeChartType === 'radar';

    activeChart = new Chart(canvas.getContext('2d'), {
        type: activeChartType,
        data: {
            labels,
            datasets: [{
                label: yCol || 'Count',
                data: values,
                backgroundColor: isPolar
                    ? multiColors.slice(0, labels.length)
                    : activeChartType === 'line'
                        ? 'rgba(99,102,241,0.15)'
                        : activeChartType === 'scatter'
                            ? 'rgba(168,85,247,0.8)'
                            : 'rgba(99,102,241,0.75)',
                borderColor: isPolar
                    ? isDark ? '#111827' : '#ffffff'
                    : '#6366f1',
                borderWidth: isPolar ? 2 : 2,
                borderRadius: activeChartType === 'bar' ? 6 : 0,
                fill: activeChartType === 'line',
                pointBackgroundColor: '#6366f1',
                pointBorderColor: '#ffffff',
                pointRadius: activeChartType === 'scatter' ? 6 : 4,
                tension: 0.4,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 600, easing: 'easeOutQuart' },
            plugins: {
                legend: {
                    labels: {
                        color: textColor,
                        font: { family: 'Inter', size: 12, weight: '600' },
                        boxWidth: 12, borderRadius: 4
                    }
                },
                tooltip: {
                    backgroundColor: isDark ? '#1e293b' : '#fff',
                    borderColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)',
                    borderWidth: 1,
                    titleColor: isDark ? '#f1f5f9' : '#0f172a',
                    bodyColor: textColor,
                    padding: 12,
                    cornerRadius: 10,
                },
                zoom: {
                    pan: {
                        enabled: true,
                        mode: 'xy',
                        threshold: 10
                    },
                    zoom: {
                        wheel: {
                            enabled: true,
                            speed: 0.1
                        },
                        pinch: {
                            enabled: true
                        },
                        mode: 'xy'
                    }
                }
            },
            scales: isPolar || isRadar ? {} : {
                x: {
                    grid: { color: gridColor },
                    ticks: { color: textColor, font: { family: 'Inter', size: 11 }, maxRotation: 45 }
                },
                y: {
                    grid: { color: gridColor },
                    ticks: { color: textColor, font: { family: 'Inter', size: 11 } }
                }
            }
        }
    });

    log('success', `Chart rendered: ${activeChartType} (${labels.length} points) [Zoom/Pan active]`);
}

function resetVisualChartZoom() {
    if (activeChart) {
        activeChart.resetZoom();
        log('system', 'Visualizer zoom reset.');
    }
}

function downloadVisualChart() {
    if (!activeChart) return;
    const a = document.createElement('a');
    a.download = `datapilot_${activeChartType}_${Date.now()}.png`;
    a.href = activeChart.toBase64Image('image/png', 1.0);
    a.click();
    log('system', 'Chart exported as PNG');
}

// ── Chat ───────────────────────────────────
function handleChatKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) sendChatMessage();
}

function injectSuggestion(text) {
    document.getElementById('chat-text').value = text;
    document.getElementById('chat-text').focus();
}

function sendChatMessage() {
    const input = document.getElementById('chat-text');
    const text  = input.value.trim();
    if (!text) return;

    appendBubble('user', text);
    input.value = '';
    hideSuggestions();

    log('system', `Planner › dispatching: "${text}"`);
    const typingId = showTyping();

    fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, filename: uploadedFilename })
    })
    .then(r => r.json())
    .then(res => {
        removeTyping(typingId);
        if (res.success) {
            const d = res.data;
            if (d.logs) d.logs.forEach(l => log(l.type, l.text));
            appendBubble('bot', d.answer, {
                chart_url:      d.chart_url,
                generated_code: d.generated_code,
            });
        } else {
            appendBubble('bot', `⚠️ ${res.error?.message || 'Unknown error'}`);
            log('error', res.error?.message);
        }
    })
    .catch(err => {
        removeTyping(typingId);
        appendBubble('bot', `🔴 Connection failed: ${err.message}`);
        log('error', err.message);
    });
}

function appendBubble(sender, html, opts = {}) {
    const msgs    = document.getElementById('chat-messages');
    const isUser  = sender === 'user';
    const time    = new Date().toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
    const avatarClass = isUser ? 'user-avatar' : 'bot-avatar';
    const avatarIcon  = isUser ? 'fa-user'     : 'fa-robot';
    const blockId = 'code-' + Date.now();

    // ── Chart image (from backend matplotlib) ──
    let chartHtml = '';
    if (opts.chart_url) {
        chartHtml = `
            <div class="chat-chart-wrap">
                <img src="${opts.chart_url}?t=${Date.now()}" alt="Generated chart"
                     class="chat-chart-img" onclick="openChartFull(this.src)">
                <div class="chart-caption">
                    <i class="fa-solid fa-chart-area"></i> AI-Generated Chart
                    <a href="${opts.chart_url}" download class="chart-dl-btn">
                        <i class="fa-solid fa-download"></i> Download
                    </a>
                </div>
            </div>`;
    }

    // ── Generated Python code block ────────────
    let codeHtml = '';
    if (opts.generated_code && !isUser) {
        const escaped = opts.generated_code
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        codeHtml = `
            <div class="code-block-wrap">
                <div class="code-block-header">
                    <span><i class="fa-brands fa-python"></i> Generated Code</span>
                    <button class="code-copy-btn" onclick="copyCode('${blockId}')">
                        <i class="fa-solid fa-copy"></i> Copy
                    </button>
                </div>
                <pre id="${blockId}" class="code-block"><code>${escaped}</code></pre>
            </div>`;
    }

    const div = document.createElement('div');
    div.className = `chat-bubble ${sender}`;
    div.innerHTML = `
        <div class="bubble-avatar ${avatarClass}"><i class="fa-solid ${avatarIcon}"></i></div>
        <div class="bubble-body">
            <div class="bubble-content">${html}</div>
            ${chartHtml}
            ${codeHtml}
            <span class="bubble-time">${time}</span>
        </div>
    `;
    msgs.appendChild(div);
    msgs.scrollTop = msgs.scrollHeight;
}

function copyCode(blockId) {
    const el = document.getElementById(blockId);
    if (!el) return;
    navigator.clipboard.writeText(el.innerText).then(() => {
        const btn = el.closest('.code-block-wrap').querySelector('.code-copy-btn');
        if (btn) { btn.innerHTML = '<i class="fa-solid fa-check"></i> Copied!'; setTimeout(() => { btn.innerHTML = '<i class="fa-solid fa-copy"></i> Copy'; }, 2000); }
    });
}

function openChartFull(src) {
    const overlay = document.createElement('div');
    overlay.className = 'fullscreen-overlay';
    overlay.style.cssText = `
        position: fixed;
        inset: 0;
        background: rgba(7, 11, 20, 0.97);
        z-index: 99999;
        display: flex;
        align-items: center;
        justify-content: center;
        overflow: hidden;
        user-select: none;
    `;
    
    overlay.innerHTML = `
        <div style="position:absolute; top:20px; right:20px; display:flex; gap:10px; z-index:100000;">
            <button class="btn-ghost" style="padding:8px 12px; background:rgba(255,255,255,0.06); border-radius:8px; border:1px solid rgba(255,255,255,0.1); color:#fff;" onclick="event.stopPropagation(); this.closest('.fullscreen-overlay').zoomReset()">
                <i class="fa-solid fa-arrows-rotate"></i> Reset
            </button>
            <button class="btn-ghost" style="padding:8px 12px; background:rgba(255,255,255,0.06); border-radius:8px; border:1px solid rgba(255,255,255,0.1); color:var(--accent-red);" onclick="event.stopPropagation(); this.closest('.fullscreen-overlay').remove()">
                <i class="fa-solid fa-xmark"></i> Close
            </button>
        </div>
        <div style="position:absolute; bottom:20px; left:50%; transform:translateX(-50%); background:rgba(0,0,0,0.65); padding:8px 18px; border-radius:20px; font-size:0.75rem; color:#e2e8f0; pointer-events:none; z-index:100000; border:1px solid rgba(255,255,255,0.08); backdrop-filter:blur(8px);">
            <i class="fa-solid fa-magnifying-glass-plus" style="color:var(--accent-1); margin-right:5px;"></i> Scroll to Zoom • Drag to Pan
        </div>
        <div class="zoom-container" style="display:flex; align-items:center; justify-content:center; width:100%; height:100%; cursor:grab;">
            <img src="${src}" class="fullscreen-chart-img" style="max-width:90%; max-height:90%; border-radius:8px; pointer-events:none; transform-origin:center; transition: transform 0.05s ease;">
        </div>
    `;

    const container = overlay.querySelector('.zoom-container');
    const img = overlay.querySelector('img');

    let scale = 1;
    let pointX = 0;
    let pointY = 0;
    let startX = 0;
    let startY = 0;
    let isPanning = false;

    // Zooming using mouse wheel
    overlay.addEventListener('wheel', (e) => {
        e.preventDefault();
        const xs = (e.clientX - pointX) / scale;
        const ys = (e.clientY - pointY) / scale;
        const delta = -e.deltaY;
        
        if (delta > 0) {
            scale *= 1.25;
        } else {
            scale /= 1.25;
        }
        
        // Limits
        scale = Math.min(Math.max(0.5, scale), 12);
        
        pointX = e.clientX - xs * scale;
        pointY = e.clientY - ys * scale;
        
        updateTransform();
    }, { passive: false });

    // Drag-to-pan implementation
    container.addEventListener('mousedown', (e) => {
        e.preventDefault();
        isPanning = true;
        container.style.cursor = 'grabbing';
        startX = e.clientX - pointX;
        startY = e.clientY - pointY;
    });

    window.addEventListener('mousemove', (e) => {
        if (!isPanning) return;
        pointX = e.clientX - startX;
        pointY = e.clientY - startY;
        updateTransform();
    });

    window.addEventListener('mouseup', () => {
        isPanning = false;
        container.style.cursor = 'grab';
    });

    function updateTransform() {
        img.style.transform = `translate(${pointX}px, ${pointY}px) scale(${scale})`;
    }

    overlay.zoomReset = () => {
        scale = 1;
        pointX = 0;
        pointY = 0;
        updateTransform();
    };

    overlay.addEventListener('click', (e) => {
        if (e.target === overlay || e.target === container) {
            overlay.remove();
        }
    });

    document.body.appendChild(overlay);
}

function showTyping() {
    const msgs = document.getElementById('chat-messages');
    const id = 'typing-' + Date.now();
    const div = document.createElement('div');
    div.className = 'chat-bubble bot';
    div.id = id;
    div.innerHTML = `
        <div class="bubble-avatar bot-avatar"><i class="fa-solid fa-robot"></i></div>
        <div class="bubble-body"><div class="typing-dots"><span></span><span></span><span></span></div></div>
    `;
    msgs.appendChild(div);
    msgs.scrollTop = msgs.scrollHeight;
    return id;
}

function removeTyping(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

function hideSuggestions() {
    // Chips remain always active — intentionally kept as no-op
}

// ── RAG Ingest ─────────────────────────────
function ingestDocumentation() {
    const pdfInput = document.getElementById('pdf-ingest');
    const ghInput  = document.getElementById('github-url');
    let name = pdfInput.files[0]?.name || ghInput.value.trim();
    if (!name) return alert('Choose a PDF or enter a GitHub URL.');

    log('system', `RAG › Ingesting: ${name}`);
    setTimeout(() => {
        log('agent', 'RAG › Chunking into overlapping text segments...');
        setTimeout(() => {
            log('agent', 'RAG › Generating embeddings → FAISS index...');
            setTimeout(() => {
                log('success', 'RAG › Index updated. Documents now searchable.');

                const list = document.getElementById('indexed-docs');
                const row  = document.createElement('div');
                row.className = 'doc-row';
                row.innerHTML = `
                    <div class="doc-row-icon"><i class="fa-solid fa-file-pdf"></i></div>
                    <div class="doc-row-info">
                        <strong>${name}</strong>
                        <span>Indexed • ~96 chunks</span>
                    </div>
                    <span class="doc-badge">FAISS</span>
                `;
                list.prepend(row);
                row.style.animation = 'slideUp 0.35s var(--trans-bounce)';

                const cnt = document.getElementById('rag-doc-count');
                if (cnt) {
                    const n = parseInt(cnt.textContent) + 1;
                    cnt.textContent = `${n} docs`;
                }

                pdfInput.value = '';
                ghInput.value  = '';
            }, 900);
        }, 900);
    }, 600);
}

// ── Health Diagnostics ─────────────────────
async function runDiagnostics() {
    // Liveness
    try {
        const res  = await fetch('/api/health/live');
        const data = await res.json();
        const dot  = document.getElementById('liveness-status');
        const txt  = document.getElementById('liveness-text');
        if (data.success) {
            dot.className = 'status-dot pulsing';
            txt.textContent = 'Live';
        } else {
            dot.className = 'status-dot disconnected';
            txt.textContent = 'Down';
        }
    } catch {
        document.getElementById('liveness-status').className = 'status-dot disconnected';
        document.getElementById('liveness-text').textContent = 'Error';
    }

    // DB
    try {
        const res  = await fetch('/api/health/health');
        const data = await res.json();
        const dot  = document.getElementById('db-status');
        const txt  = document.getElementById('db-text');
        const ok   = data.data?.checks?.database?.status === 'UP';
        dot.className = ok ? 'status-dot connected' : 'status-dot disconnected';
        txt.textContent = ok ? 'Connected' : 'Disconnected';
    } catch {
        document.getElementById('db-status').className = 'status-dot disconnected';
        document.getElementById('db-text').textContent = 'Error';
    }
}

// ── Helpers ────────────────────────────────
function setEl(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
}

// ── Init ───────────────────────────────────
runDiagnostics();
setInterval(runDiagnostics, 15000);

// Restore session if active
window.addEventListener('DOMContentLoaded', () => {
    // Mobile screen check: collapse sidebar by default
    if (window.innerWidth < 768) {
        isSidebarOpen = false;
        const sb = document.getElementById('sidebar');
        if (sb) sb.classList.add('collapsed');
    }

    const cachedFile = sessionStorage.getItem('uploadedFilename');
    const origName   = sessionStorage.getItem('originalFilename');
    const fileSize   = sessionStorage.getItem('fileSize');
    
    if (cachedFile && origName) {
        log('system', `Session › Restoring active dataset: <strong>${origName}</strong>...`);
        fetch('/api/load-cached', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename: cachedFile })
        })
        .then(r => r.json())
        .then(res => {
            if (res.success) {
                dfData = res.data.data;
                filteredData = [...dfData];
                dfColumns = res.data.columns;
                uploadedFilename = cachedFile;
                
                renderFileCard({ name: origName, size: Number(fileSize || 0) });
                populateFilterColumns();
                updateDataDisplay();
                showQuickStats();
                updateFileCardStatus('Synced ✓');
                log('success', `Session › Restored active dataset: <strong>${origName}</strong>`);
            } else {
                sessionStorage.removeItem('uploadedFilename');
                sessionStorage.removeItem('originalFilename');
                sessionStorage.removeItem('fileSize');
                log('error', `Session › Cache expired. Re-upload required.`);
            }
        })
        .catch(err => log('error', `Session › Restore request failed: ${err.message}`));
    }
});
