/* RCS-2000 Control Center — Main Application */
const App = (() => {
  let currentPage = 'dashboard';
  let refreshTimer = null;
  const REFRESH_MS = 5000;

  async function init() {
    const key = API.getApiKey();
    if (!key) {
      showLogin();
    } else {
      const valid = await API.validateApiKey(key);
      if (valid) boot();
      else { API.clearApiKey(); showLogin(); }
    }
  }

  function showLogin() {
    document.querySelector('.sidebar').style.display = 'none';
    document.querySelector('.main-content').style.marginLeft = '0';
    document.querySelector('.main-content').style.padding = '0';
    document.getElementById('page-content').innerHTML = `
      <div class="login-wrapper" style="display:flex;align-items:center;justify-content:center;min-height:100vh;background:var(--bg-primary);">
        <div class="glass-panel" style="width:100%;max-width:400px;padding:40px;">
          <div style="text-align:center;margin-bottom:30px;">
            <div class="logo-icon" style="margin:0 auto 16px;width:56px;height:56px;font-size:24px;">R</div>
            <h2>RCS-2000</h2>
            <p style="color:var(--text-secondary);margin-top:8px;">Control Center Girişi</p>
          </div>
          <div class="form-group">
            <label class="form-label">${UI.icon('lock')} API Anahtarı</label>
            <input id="login-key" class="form-input" type="password" placeholder="X-API-Key..." autofocus>
          </div>
          <button id="login-btn" class="btn btn-primary" style="width:100%;padding:12px;margin-top:10px;" onclick="App.login()">Bağlan</button>
        </div>
      </div>`;
  }

  async function login() {
    const v = document.getElementById('login-key')?.value?.trim();
    if (!v) return UI.toast('Lütfen API anahtarını girin', 'error');
    const btn = document.getElementById('login-btn');
    btn.disabled = true; btn.textContent = 'Doğrulanıyor...';
    
    const valid = await API.validateApiKey(v);
    if (valid) {
      API.setApiKey(v);
      document.querySelector('.sidebar').style.display = '';
      document.querySelector('.main-content').style.marginLeft = '';
      document.querySelector('.main-content').style.padding = '';
      boot();
    } else {
      UI.toast('Geçersiz API Anahtarı veya bağlantı hatası', 'error');
      btn.disabled = false; btn.textContent = 'Bağlan';
    }
  }

  function logout() {
    API.clearApiKey();
    if (refreshTimer) clearInterval(refreshTimer);
    showLogin();
  }

  function boot() {
    renderSidebar();
    navigate('dashboard');
    startAutoRefresh();
    checkConnection();
    checkAlerts();
  }

  function renderSidebar() {
    document.getElementById('sidebar-nav').innerHTML = `
      <div class="nav-section">
        <div class="nav-section-title">Ana Menü</div>
        <a class="nav-item active" data-page="dashboard" onclick="App.navigate('dashboard')">${UI.icon('dashboard')}<span>Dashboard</span></a>
        <a class="nav-item" data-page="map" onclick="App.navigate('map')">${UI.icon('map')}<span>Robot Haritası</span></a>
        <a class="nav-item" data-page="robots" onclick="App.navigate('robots')">${UI.icon('robot')}<span>Robot Durumları</span></a>
        <a class="nav-item" data-page="tasks" onclick="App.navigate('tasks')">${UI.icon('task')}<span>Görev Yönetimi</span></a>
      </div>
      <div class="nav-section">
        <div class="nav-section-title">İzleme</div>
        <a class="nav-item" data-page="alerts" onclick="App.navigate('alerts')">
          ${UI.icon('bell')}<span>Alarmlar</span><span id="alert-badge" style="display:none;background:var(--accent-red);color:white;border-radius:10px;padding:2px 6px;font-size:10px;margin-left:auto;"></span>
        </a>
        <a class="nav-item" data-page="webhooks" onclick="App.navigate('webhooks')">${UI.icon('webhook')}<span>Webhook Logları</span></a>
      </div>
      <div class="nav-section">
        <div class="nav-section-title">Sistem</div>
        <a class="nav-item" data-page="settings" onclick="App.navigate('settings')">${UI.icon('settings')}<span>Ayarlar</span></a>
        <a class="nav-item" onclick="App.logout()" style="color:var(--accent-red);">${UI.icon('logout')}<span>Çıkış Yap</span></a>
      </div>`;
  }

  function navigate(page) {
    currentPage = page;
    document.querySelectorAll('.nav-item').forEach(el => {
      el.classList.toggle('active', el.dataset.page === page);
    });
    closeMobileMenu();
    const pages = { 
      dashboard: renderDashboard, robots: renderRobots, tasks: renderTasks, 
      settings: renderSettings, webhooks: renderWebhooks, map: renderMap, alerts: renderAlerts 
    };
    (pages[page] || renderDashboard)();
  }

  /* ── Dashboard ── */
  async function renderDashboard() {
    const el = document.getElementById('page-content');
    el.innerHTML = `
      <div class="topbar">
        <h2>Dashboard</h2>
        <div class="topbar-actions"><span class="refresh-badge"><span class="dot"></span>Canlı</span></div>
      </div>
      <div class="stats-grid" id="stats-grid">${Array(6).fill('<div class="stat-card"><div class="skeleton skeleton-card"></div></div>').join('')}</div>
      <div class="glass-panel"><div class="panel-header"><h3>Aktif Robotlar</h3><button class="btn btn-ghost btn-sm" onclick="App.navigate('robots')">Tümü</button></div><div id="dash-robots">${UI.skeleton(3)}</div></div>`;
    try {
      const [statsRes, robotsRes] = await Promise.all([API.getStats(), API.getRobots()]);
      const s = statsRes.data;
      document.getElementById('stats-grid').innerHTML = `
        ${statCard('Aktif Robot', s.activeRobots, 'robot', 'cyan')}
        ${statCard('Bekleyen Görev', s.pendingTasks, 'task', 'amber')}
        ${statCard('Çalışan Görev', s.runningTasks, 'task', 'blue')}
        ${statCard('Tamamlanan (Bugün)', s.completedTasksToday, 'check', 'green')}
        ${statCard('Başarısız (Bugün)', s.failedTasksToday, 'alert', 'red')}
        ${statCard('Toplam Görev', s.totalTasks, 'task', 'purple')}`;
      renderRobotTable(document.getElementById('dash-robots'), robotsRes.data || [], true);
      updateConnectionDot(s.dbStatus === 'ok' && s.redisStatus === 'ok');
    } catch (e) { console.error(e); }
  }

  function statCard(label, value, iconName, color) {
    return `<div class="stat-card"><div class="stat-icon ${color}">${UI.icon(iconName)}</div><div class="stat-value">${value ?? '—'}</div><div class="stat-label">${label}</div></div>`;
  }

  /* ── Robots ── */
  async function renderRobots() {
    const el = document.getElementById('page-content');
    el.innerHTML = `<div class="topbar"><h2>Robot Durumları</h2><div class="topbar-actions"><span class="refresh-badge"><span class="dot"></span>5s yenileme</span></div></div>
      <div class="glass-panel"><div id="robots-table">${UI.skeleton(5)}</div></div>`;
    try {
      const res = await API.getRobots();
      renderRobotTable(document.getElementById('robots-table'), res.data || [], false);
    } catch (e) { UI.toast('Robot verisi alınamadı', 'error'); }
  }

  function renderRobotTable(container, robots, compact) {
    if (!robots.length) { container.innerHTML = UI.emptyState('Aktif robot bulunamadı'); return; }
    let html = `<table class="data-table"><thead><tr><th>AMR Kodu</th><th>Konum (X, Y)</th><th>Durum</th><th>Son Güncelleme</th></tr></thead><tbody>`;
    (compact ? robots.slice(0, 5) : robots).forEach(r => {
      html += `<tr><td class="mono" style="color:var(--accent-cyan);font-weight:600;">${r.amrCode}</td>
        <td class="mono">${r.x?.toFixed(1) ?? '—'}, ${r.y?.toFixed(1) ?? '—'}</td>
        <td>${UI.badge(r.state)}</td><td>${UI.timeAgo(r.updatedAt)}</td></tr>`;
    });
    html += '</tbody></table>';
    container.innerHTML = html;
  }

  /* ── Map ── */
  let mapCanvas, ctx;
  async function renderMap() {
    const el = document.getElementById('page-content');
    el.innerHTML = `<div class="topbar"><h2>Robot Haritası</h2><div class="topbar-actions"><span class="refresh-badge"><span class="dot"></span>Canlı</span></div></div>
      <div class="glass-panel" style="padding:0;overflow:hidden;position:relative;height:600px;background:var(--bg-secondary);">
        <canvas id="robot-map" style="width:100%;height:100%;display:block;"></canvas>
      </div>`;
    mapCanvas = document.getElementById('robot-map');
    ctx = mapCanvas.getContext('2d');
    resizeMap();
    window.addEventListener('resize', resizeMap);
    await drawMap();
  }
  function resizeMap() {
    if (!mapCanvas) return;
    mapCanvas.width = mapCanvas.parentElement.clientWidth;
    mapCanvas.height = mapCanvas.parentElement.clientHeight;
    if (currentPage === 'map') drawMap();
  }
  async function drawMap() {
    if (!ctx || !mapCanvas || currentPage !== 'map') return;
    ctx.clearRect(0, 0, mapCanvas.width, mapCanvas.height);
    
    // Draw Grid
    ctx.strokeStyle = 'rgba(100, 100, 180, 0.1)';
    ctx.lineWidth = 1;
    const step = 40;
    for (let x = 0; x < mapCanvas.width; x += step) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, mapCanvas.height); ctx.stroke(); }
    for (let y = 0; y < mapCanvas.height; y += step) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(mapCanvas.width, y); ctx.stroke(); }

    try {
      const res = await API.getRobots();
      const robots = res.data || [];
      // Simulated scaling for demo purposes (assuming max map coordinates ~100x100)
      const scaleX = mapCanvas.width / 100;
      const scaleY = mapCanvas.height / 100;

      robots.forEach(r => {
        if (r.x == null || r.y == null) return;
        const px = r.x * scaleX;
        const py = mapCanvas.height - (r.y * scaleY); // invert Y
        
        ctx.fillStyle = r.state === 'running' ? '#00d4ff' : (r.state === 'idle' ? '#10b981' : '#f59e0b');
        ctx.beginPath(); ctx.arc(px, py, 8, 0, Math.PI * 2); ctx.fill();
        ctx.strokeStyle = 'white'; ctx.lineWidth = 2; ctx.stroke();
        
        ctx.fillStyle = '#fff';
        ctx.font = '10px JetBrains Mono';
        ctx.fillText(r.amrCode, px + 12, py + 4);
      });
    } catch (e) { console.error('Map draw error', e); }
  }

  /* ── Tasks ── */
  let taskPage = 1, taskFilter = '';
  async function renderTasks() {
    taskPage = 1; taskFilter = '';
    const el = document.getElementById('page-content');
    el.innerHTML = `
      <div class="topbar"><h2>Görev Yönetimi</h2>
        <div class="topbar-actions">
          <select class="form-select" style="width:140px;padding:7px 10px;font-size:12px;" onchange="App.filterTasks(this.value)">
            <option value="">Tüm Durumlar</option><option value="pending">Bekleyen</option><option value="running">Çalışan</option>
            <option value="completed">Tamamlanan</option><option value="failed">Başarısız</option><option value="cancelled">İptal</option>
          </select>
          <button class="btn btn-primary btn-sm" onclick="App.openCreateModal()">${UI.icon('plus')} Yeni Görev</button>
        </div>
      </div>
      <div class="glass-panel"><div id="tasks-table">${UI.skeleton(5)}</div><div id="tasks-pagination"></div></div>`;
    await loadTasks();
  }
  async function loadTasks() {
    try {
      const res = await API.getTaskHistory(taskPage, 15, taskFilter);
      const d = res.data;
      const cont = document.getElementById('tasks-table');
      if (!d.items?.length) { cont.innerHTML = UI.emptyState('Görev bulunamadı'); document.getElementById('tasks-pagination').innerHTML = ''; return; }
      let html = `<table class="data-table"><thead><tr><th>Görev Kodu</th><th>Durum</th><th>Robot</th><th>Kaynak</th><th>Hedef</th><th>Hata</th></tr></thead><tbody>`;
      d.items.forEach(t => {
        html += `<tr><td class="mono" style="color:var(--accent-purple);font-weight:600;">${t.robotTaskCode}</td>
          <td>${UI.badge(t.status)}</td><td class="mono">${t.robotCode || '—'}</td><td>${t.sourceCode || '—'}</td><td>${t.targetCode || '—'}</td>
          <td style="max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${t.errorMsg || ''}">${t.errorMsg || '—'}</td></tr>`;
      });
      html += '</tbody></table>';
      cont.innerHTML = html;
      document.getElementById('tasks-pagination').innerHTML = UI.pagination(d.page, d.totalPages, 'App.goToTaskPage');
    } catch (e) { UI.toast('Görevler alınamadı', 'error'); }
  }
  function goToTaskPage(p) { taskPage = p; loadTasks(); }
  function filterTasks(v) { taskFilter = v; taskPage = 1; loadTasks(); }

  /* ── Webhooks ── */
  let whPage = 1, whFilter = '';
  async function renderWebhooks() {
    whPage = 1; whFilter = '';
    const el = document.getElementById('page-content');
    el.innerHTML = `
      <div class="topbar"><h2>Webhook Logları</h2>
        <div class="topbar-actions">
          <input type="text" class="form-input" style="width:180px;padding:7px 10px;font-size:12px;" placeholder="Görev Koduna Göre Ara..." onkeyup="if(event.key==='Enter')App.filterWh(this.value)">
          <button class="btn btn-ghost btn-sm" onclick="App.navigate('webhooks')">${UI.icon('refresh')}</button>
        </div>
      </div>
      <div class="glass-panel"><div id="wh-table">${UI.skeleton(8)}</div><div id="wh-pagination"></div></div>`;
    await loadWebhooks();
  }
  async function loadWebhooks() {
    try {
      const res = await API.getWebhookLogs(whPage, 30, whFilter);
      const d = res.data;
      const cont = document.getElementById('wh-table');
      if (!d.items?.length) { cont.innerHTML = UI.emptyState('Log bulunamadı'); document.getElementById('wh-pagination').innerHTML = ''; return; }
      let html = `<table class="data-table"><thead><tr><th>ID</th><th>Zaman</th><th>Görev Kodu</th><th>Method</th><th>AMR</th><th>İmza</th></tr></thead><tbody>`;
      d.items.forEach(w => {
        html += `<tr><td class="mono">#${w.id}</td><td>${UI.timeAgo(w.createdAt)}</td>
          <td class="mono" style="color:var(--accent-purple);">${w.robotTaskCode}</td>
          <td><span class="badge" style="background:rgba(255,255,255,0.05);">${w.method}</span></td>
          <td class="mono">${w.amrCode || '—'}</td>
          <td>${w.signatureValid ? UI.badge('geçerli') : '<span class="badge failed"><span class="badge-dot"></span>Geçersiz</span>'} ${w.duplicate ? '<span style="font-size:10px;color:var(--text-muted);">(Dedupe)</span>' : ''}</td></tr>`;
      });
      html += '</tbody></table>';
      cont.innerHTML = html;
      document.getElementById('wh-pagination').innerHTML = UI.pagination(d.page, d.totalPages, 'App.goToWhPage');
    } catch (e) { UI.toast('Loglar alınamadı', 'error'); }
  }
  function goToWhPage(p) { whPage = p; loadWebhooks(); }
  function filterWh(v) { whFilter = v.trim(); whPage = 1; loadWebhooks(); }

  /* ── Alerts ── */
  async function renderAlerts() {
    const el = document.getElementById('page-content');
    el.innerHTML = `
      <div class="topbar"><h2>Sistem Alarmları</h2><div class="topbar-actions"><span class="refresh-badge"><span class="dot"></span>Otomatik yenilenir</span></div></div>
      <div class="glass-panel" style="max-width:800px;margin:0 auto;"><div id="alerts-list">${UI.skeleton(4)}</div></div>`;
    await loadAlertsList();
  }
  async function loadAlertsList() {
    try {
      const res = await API.getAlerts(50);
      const items = res.data.items || [];
      document.getElementById('alert-badge').style.display = items.length > 0 ? 'inline-block' : 'none';
      document.getElementById('alert-badge').textContent = items.length;

      const cont = document.getElementById('alerts-list');
      if (!items.length) { cont.innerHTML = UI.emptyState('Aktif alarm bulunmuyor'); return; }
      
      let html = '<div style="display:flex;flex-direction:column;gap:12px;">';
      items.forEach(a => {
        const isErr = a.severity === 'error';
        html += `<div style="display:flex;gap:16px;padding:16px;border-radius:var(--radius-md);background:${isErr?'rgba(239,68,68,0.05)':'rgba(245,158,11,0.05)'};border:1px solid ${isErr?'rgba(239,68,68,0.2)':'rgba(245,158,11,0.2)'};">
          <div style="color:${isErr?'var(--accent-red)':'var(--accent-amber)'};margin-top:2px;">${UI.icon('alert')}</div>
          <div style="flex:1;">
            <div style="display:flex;justify-content:space-between;margin-bottom:6px;">
              <strong style="color:var(--text-primary);font-size:14px;">${a.message}</strong>
              <span style="font-size:11px;color:var(--text-muted);">${UI.timeAgo(a.timestamp)}</span>
            </div>
            ${a.details ? `<div style="font-size:12px;color:var(--text-secondary);font-family:var(--font-mono);background:var(--bg-primary);padding:8px;border-radius:4px;">${a.details}</div>` : ''}
          </div>
        </div>`;
      });
      html += '</div>';
      cont.innerHTML = html;
    } catch (e) { console.error('Alerts failed', e); }
  }

  /* ── Settings ── */
  function renderSettings() {
    const el = document.getElementById('page-content');
    el.innerHTML = `
      <div class="topbar"><h2>Ayarlar</h2></div>
      <div class="glass-panel" style="max-width:500px;margin-bottom:20px;">
        <h3 style="margin-bottom:16px;">Sistem Bağlantıları</h3>
        <button class="btn btn-primary" onclick="App.testHealth()">Bağlantıları Sına</button>
        <div id="health-result" style="margin-top:20px;"></div>
      </div>
      <div class="glass-panel" style="max-width:500px;">
        <h3 style="margin-bottom:16px;">RCS Sunucu Ayarları</h3>
        <p style="color:var(--text-secondary);font-size:13px;margin-bottom:20px;">RCS-2000 sunucusunun IP adresi ve portunu buradan değiştirebilirsiniz. Değişiklikler anında geçerli olur.</p>
        <div class="form-group">
          <label class="form-label">RCS IP Adresi</label>
          <input type="text" id="set-rcs-ip" class="form-input" placeholder="örn: 10.141.88.12">
        </div>
        <div class="form-group">
          <label class="form-label">RCS Port</label>
          <input type="number" id="set-rcs-port" class="form-input" placeholder="örn: 80">
        </div>
        <div style="margin-top:20px;display:flex;justify-content:space-between;align-items:center;">
          <span id="set-rcs-url" style="font-size:12px;color:var(--accent-cyan);font-family:var(--font-mono);"></span>
          <button class="btn btn-primary" onclick="App.saveSystemConfig()">Kaydet</button>
        </div>
      </div>`;
    testHealth();
    loadSystemConfig();
  }
  async function testHealth() {
    const el = document.getElementById('health-result');
    if (!el) return;
    el.innerHTML = 'Sınanıyor...';
    try {
      const h = await API.healthReady();
      el.innerHTML = `<div style="display:flex;flex-direction:column;gap:12px;margin-top:8px;">
        <div style="padding:12px;border:1px solid var(--border-subtle);border-radius:var(--radius-sm);display:flex;justify-content:space-between;">
          <span>MySQL Veritabanı</span>${h.db === 'ok' ? UI.badge('ok') : '<span class="badge failed"><span class="badge-dot"></span>error</span>'}
        </div>
        <div style="padding:12px;border:1px solid var(--border-subtle);border-radius:var(--radius-sm);display:flex;justify-content:space-between;">
          <span>Redis Önbellek</span>${h.redis === 'ok' ? UI.badge('ok') : '<span class="badge failed"><span class="badge-dot"></span>error</span>'}
        </div>
      </div>`;
    } catch { el.innerHTML = '<span class="badge failed"><span class="badge-dot"></span>Sistemlere ulaşılamıyor</span>'; }
  }
  
  async function loadSystemConfig() {
    try {
      const res = await API.getSystemConfig();
      if (res && res.data) {
        if (res.data.rcs_ip) document.getElementById('set-rcs-ip').value = res.data.rcs_ip;
        if (res.data.rcs_port) document.getElementById('set-rcs-port').value = res.data.rcs_port;
        document.getElementById('set-rcs-url').textContent = res.data.rcs_base_url || '';
      }
    } catch (e) { UI.toast('Ayarlar yüklenemedi', 'error'); }
  }

  async function saveSystemConfig() {
    const ip = document.getElementById('set-rcs-ip').value.trim();
    const port = parseInt(document.getElementById('set-rcs-port').value, 10);
    
    if (!ip || !port) {
      UI.toast('IP ve Port alanları zorunludur', 'error');
      return;
    }
    
    try {
      const res = await API.updateSystemConfig({ rcs_ip: ip, rcs_port: port });
      UI.toast('Ayarlar başarıyla kaydedildi', 'success');
      if (res && res.data) {
        document.getElementById('set-rcs-url').textContent = res.data.rcs_base_url || '';
      }
    } catch (e) { UI.toast('Ayarlar kaydedilemedi: ' + e.message, 'error'); }
  }

  /* ── Background Tasks ── */
  async function checkConnection() {
    try {
      const h = await API.healthReady();
      updateConnectionDot(h.db === 'ok' && h.redis === 'ok');
    } catch { updateConnectionDot(false); }
  }
  function updateConnectionDot(ok) {
    const dot = document.getElementById('conn-dot');
    const txt = document.getElementById('conn-text');
    if (dot) dot.className = ok ? 'status-dot' : 'status-dot error';
    if (txt) txt.textContent = ok ? 'Bağlı' : 'Bağlantı yok';
  }
  async function checkAlerts() {
    try {
      const res = await API.getAlerts(1);
      const count = res.data.total || 0;
      const b = document.getElementById('alert-badge');
      if (b) {
        b.textContent = count;
        b.style.display = count > 0 ? 'inline-block' : 'none';
      }
    } catch (e) {}
  }
  function startAutoRefresh() {
    if (refreshTimer) clearInterval(refreshTimer);
    refreshTimer = setInterval(() => {
      checkAlerts();
      if (currentPage === 'dashboard') renderDashboard();
      else if (currentPage === 'robots') renderRobots();
      else if (currentPage === 'map') drawMap();
      else if (currentPage === 'webhooks') loadWebhooks();
      else if (currentPage === 'alerts') loadAlertsList();
    }, REFRESH_MS);
  }

  /* ── Modals ── */
  function openCreateModal() {
    document.getElementById('modal-overlay').innerHTML = `
      <div class="modal modal-postman">
        <div class="modal-title">Yeni Görev Oluştur</div>
        <div class="task-modal-tabs">
          <button type="button" class="task-modal-tab active" data-tab="quick" onclick="App.switchTaskModalTab('quick')">Hızlı form</button>
          <button type="button" class="task-modal-tab" data-tab="rcs" onclick="App.switchTaskModalTab('rcs')">RCS isteği (Postman)</button>
        </div>
        <div id="task-tab-quick">
          <div class="form-group"><label class="form-label">Robot Tipi</label>
            <select id="m-robotType" class="form-select"><option value="LMR">LMR — Light Mobile</option><option value="FMR">FMR — Forklift</option><option value="CT7">CT7 — Container</option></select>
          </div>
          <div class="form-row">
            <div class="form-group"><label class="form-label">Kaynak</label><input id="m-source" class="form-input" placeholder="örn: WH-A01"></div>
            <div class="form-group"><label class="form-label">Hedef</label><input id="m-target" class="form-input" placeholder="örn: WH-B03"></div>
          </div>
          <div class="form-group"><label class="form-label">Öncelik</label><input id="m-priority" class="form-input" type="number" value="10" min="1" max="100"></div>
        </div>
        <div id="task-tab-rcs" style="display:none;">
          <p class="rcs-editor-hint" style="margin-bottom:12px;">Ayarlar sayfasındaki IP ve port, taban URL olarak kullanılır. Varsayılan gönderim Postman ile aynıdır (imzasız + <code>X-LR-REQUEST-ID</code> header).</p>
          <div class="form-group">
            <label class="form-label">Taban URL (salt okunur)</label>
            <input type="text" id="rcs-preview-base" class="form-input code-editor-sm" readonly placeholder="Önizleme yükleniyor…">
          </div>
          <div class="form-group">
            <label class="form-label">Path veya tam URL</label>
            <input type="text" id="rcs-editor-path" class="form-input code-editor-sm" placeholder="/rcs/rtas/api/robot/controller/task/submit">
            <div class="rcs-editor-hint" id="rcs-full-url-hint"></div>
          </div>
          <div class="form-group">
            <label class="form-label">JSON body</label>
            <textarea id="rcs-editor-body" class="code-editor" spellcheck="false" placeholder="{ }"></textarea>
          </div>
          <div class="form-group" style="display:flex;align-items:center;gap:10px;">
            <input type="checkbox" id="rcs-persist" checked style="width:auto;">
            <label for="rcs-persist" style="margin:0;font-size:13px;color:var(--text-secondary);">RCS cevabında görev kodu varsa geçmişe kaydet</label>
          </div>
          <div class="form-group" style="display:flex;align-items:center;gap:10px;">
            <input type="checkbox" id="rcs-send-signed" style="width:auto;">
            <label for="rcs-send-signed" style="margin:0;font-size:13px;color:var(--text-secondary);">İmzalı gönder (HMAC + sign query)</label>
          </div>
          <div style="margin-top:8px;">
            <button type="button" class="btn btn-ghost btn-sm" onclick="App.refreshRcsPreview()">${UI.icon('refresh')} Önizlemeyi yenile</button>
          </div>
        </div>
        <div class="modal-actions">
          <button type="button" class="btn btn-ghost" onclick="App.closeModal()">İptal</button>
          <button type="button" class="btn btn-primary" id="m-submit-quick" onclick="App.submitTask()">Gönder</button>
          <button type="button" class="btn btn-primary" id="m-submit-rcs" style="display:none;" onclick="App.submitRcsRawTask()">RCS'e gönder</button>
        </div>
      </div>`;
    document.getElementById('modal-overlay').classList.add('active');
    refreshRcsPreview();
  }

  function switchTaskModalTab(tab) {
    document.querySelectorAll('.task-modal-tab').forEach((b) => {
      b.classList.toggle('active', b.dataset.tab === tab);
    });
    const q = document.getElementById('task-tab-quick');
    const r = document.getElementById('task-tab-rcs');
    if (q) q.style.display = tab === 'quick' ? 'block' : 'none';
    if (r) r.style.display = tab === 'rcs' ? 'block' : 'none';
    const bq = document.getElementById('m-submit-quick');
    const br = document.getElementById('m-submit-rcs');
    if (bq) bq.style.display = tab === 'quick' ? '' : 'none';
    if (br) br.style.display = tab === 'rcs' ? '' : 'none';
  }

  async function refreshRcsPreview() {
    try {
      const res = await API.getRcsSubmitPreview();
      const d = res.data;
      const baseEl = document.getElementById('rcs-preview-base');
      const pathEl = document.getElementById('rcs-editor-path');
      const bodyEl = document.getElementById('rcs-editor-body');
      const hintEl = document.getElementById('rcs-full-url-hint');
      if (!baseEl || !pathEl || !bodyEl) return;
      baseEl.value = d.resolvedBaseUrl || '';
      pathEl.value = d.path || '';
      bodyEl.value = JSON.stringify(d.exampleBody || {}, null, 2);
      if (hintEl) {
        hintEl.textContent = d.fullUrlWithoutSign
          ? `Örnek tam URL (sign hariç): ${d.fullUrlWithoutSign}`
          : '';
      }
    } catch (e) {
      UI.toast('RCS önizlemesi alınamadı: ' + (e.message || 'hata'), 'error');
    }
  }

  function closeModal() { document.getElementById('modal-overlay').classList.remove('active'); }
  async function submitTask() {
    const btn = document.getElementById('m-submit-quick');
    if (!btn) return;
    btn.disabled = true; btn.textContent = 'Gönderiliyor…';
    try {
      const payload = {
        robotType: document.getElementById('m-robotType').value,
        sourceCode: document.getElementById('m-source').value.trim(),
        targetCode: document.getElementById('m-target').value.trim(),
        priority: parseInt(document.getElementById('m-priority').value, 10) || 10,
      };
      if (!payload.sourceCode || !payload.targetCode) throw new Error('Kaynak ve hedef kodu boş olamaz');
      await API.createTask(payload);
      UI.toast('Görev başarıyla oluşturuldu', 'success');
      closeModal();
      if (currentPage === 'tasks') loadTasks();
      else if (currentPage === 'dashboard') renderDashboard();
    } catch (e) {
      UI.toast(e.message, 'error');
      btn.disabled = false; btn.textContent = 'Gönder';
    }
  }

  async function submitRcsRawTask() {
    const btn = document.getElementById('m-submit-rcs');
    if (!btn) return;
    const path = document.getElementById('rcs-editor-path')?.value?.trim() || '';
    const rawBody = document.getElementById('rcs-editor-body')?.value?.trim() || '';
    if (!path) {
      UI.toast('Path veya tam URL gerekli', 'error');
      return;
    }
    let body;
    try {
      body = rawBody ? JSON.parse(rawBody) : {};
    } catch (err) {
      UI.toast('JSON body geçersiz', 'error');
      return;
    }
    const persistTask = document.getElementById('rcs-persist')?.checked !== false;
    const sendSigned = document.getElementById('rcs-send-signed')?.checked === true;
    btn.disabled = true;
    btn.textContent = 'Gönderiliyor…';
    try {
      const res = await API.submitRcsRaw({
        method: 'POST',
        path,
        body,
        sendSigned,
        persistTask,
      });
      const d = res.data;
      const code = d.robotTaskCode || d.rcsResponse?.data?.robotTaskCode;
      UI.toast(
        code ? `RCS yanıtı alındı — ${code}` : 'RCS isteği tamamlandı',
        'success',
      );
      closeModal();
      if (currentPage === 'tasks') loadTasks();
      else if (currentPage === 'dashboard') renderDashboard();
    } catch (e) {
      UI.toast(e.message || 'RCS isteği başarısız', 'error');
      btn.disabled = false;
      btn.textContent = "RCS'e gönder";
    }
  }

  function toggleMobileMenu() {
    document.getElementById('sidebar').classList.toggle('open');
    document.getElementById('sidebar-backdrop').classList.toggle('open');
  }
  function closeMobileMenu() {
    document.getElementById('sidebar').classList.remove('open');
    document.getElementById('sidebar-backdrop').classList.remove('open');
  }

  return { 
    init, navigate, login, logout, testHealth,
    filterTasks, goToTaskPage, filterWh, goToWhPage,
    openCreateModal, closeModal, submitTask, submitRcsRawTask,
    switchTaskModalTab, refreshRcsPreview,
    toggleMobileMenu,
    saveSystemConfig
  };
})();

document.addEventListener('DOMContentLoaded', App.init);
