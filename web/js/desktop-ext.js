/* ═══════════════════════════════════════════════════════
   Web OS v1.0 — Extension Apps
   Advanced apps that integrate with the Window Manager
   ═══════════════════════════════════════════════════════ */

(function() {
  const API = '/api';
  function getToken() { return localStorage.getItem('token') || ''; }

  function extFetch(path, opts) {
    opts = opts || {};
    opts.headers = opts.headers || {};
    opts.headers['Authorization'] = 'Bearer ' + getToken();
    if (opts.body && typeof opts.body === 'object') {
      if (!opts.headers['Content-Type']) opts.headers['Content-Type'] = 'application/json';
      opts.body = JSON.stringify(opts.body);
    }
    return fetch(API + path, opts).then(r => r.json());
  }

  function notify(msg, type) {
    if (window.notify) window.notify(msg, type || 'info');
  }

  function launchWindow(title, icon, html, w, h) {
    if (window.createWindow && window.setWindowContent) {
      const id = window.createWindow({ title, icon, width: w || 800, height: h || 520 });
      window.setWindowContent(id, html);
      return id;
    }
    return null;
  }

  // ─── AI Multi-Agent Chat ─────────────────────────────
  function aiChat() {
    const id = launchWindow('AI Multi-Agent Chat', '\u{1F4AC}', '', 900, 600);
    if (!id) return;
    const html = `
    <style>
      .agent-chat { display:flex; height:100%; gap:0; }
      .agent-sidebar { width:180px; background:var(--bg2); border-right:1px solid var(--border); padding:12px; overflow-y:auto; flex-shrink:0; }
      .agent-item { padding:6px 10px; border-radius:4px; cursor:pointer; font-size:0.82em; margin-bottom:2px; transition:0.15s; display:flex; align-items:center; gap:6px; }
      .agent-item:hover { background:var(--bg3); }
      .agent-item.active { background:var(--primary); color:white; }
      .agent-dot { width:8px; height:8px; border-radius:50%; flex-shrink:0; }
      .agent-main { flex:1; display:flex; flex-direction:column; }
      .agent-msgs { flex:1; overflow-y:auto; padding:16px; display:flex; flex-direction:column; gap:8px; scroll-behavior:smooth; }
      .agent-msg { padding:10px 14px; border-radius:8px; max-width:85%; font-size:0.88em; line-height:1.4; }
      .agent-msg.user { background:var(--primary); color:white; align-self:flex-end; }
      .agent-msg.assistant { background:var(--bg2); border:1px solid var(--border); align-self:flex-start; }
      .agent-msg.system { background:rgba(255,165,2,0.1); border-left:3px solid var(--warning); align-self:center; font-size:0.8em; color:var(--text2); }
      .agent-input { display:flex; gap:8px; padding:12px; border-top:1px solid var(--border); }
      .agent-input input { flex:1; padding:10px 14px; border-radius:6px; background:var(--bg2); border:1px solid var(--border); color:var(--text); }
      .agent-input input:focus { border-color:var(--primary); }
      .agent-input button { padding:10px 20px; border-radius:6px; background:var(--primary); color:white; border:none; cursor:pointer; font-weight:600; }
      .agent-input button:hover { background:var(--primary2); }
      .agent-mode { display:flex; gap:4px; padding:8px 12px; border-bottom:1px solid var(--border); }
      .mode-btn { padding:4px 12px; border-radius:12px; border:1px solid var(--border); background:transparent; color:var(--text2); cursor:pointer; font-size:0.78em; transition:0.15s; }
      .mode-btn.active { background:var(--primary); color:white; border-color:var(--primary); }
      .mode-btn:hover { border-color:var(--primary); }
      .agent-status { display:flex; gap:8px; padding:6px 12px; border-bottom:1px solid var(--border); font-size:0.75em; color:var(--text3); align-items:center; }
      .typing-dots { display:inline-flex; gap:3px; }
      .typing-dots span { width:6px; height:6px; border-radius:50%; background:var(--text3); animation:dotPulse 1.4s infinite; }
      .typing-dots span:nth-child(2) { animation-delay:0.2s; }
      .typing-dots span:nth-child(3) { animation-delay:0.4s; }
      @keyframes dotPulse { 0%,80%,100% { opacity:0.3; transform:scale(0.8); } 40% { opacity:1; transform:scale(1); } }
    </style>
    <div class="agent-chat">
      <div class="agent-sidebar" id="agent-sidebar-${id}"></div>
      <div class="agent-main">
        <div class="agent-status" id="agent-status-${id}">Ready</div>
        <div class="agent-mode" id="agent-mode-${id}"></div>
        <div class="agent-msgs" id="agent-msgs-${id}"></div>
        <div class="agent-input">
          <input type="text" id="agent-input-${id}" placeholder="Type a message..." onkeydown="if(event.key==='Enter')sendAgentMsg('${id}')">
          <button onclick="sendAgentMsg('${id}')">Send</button>
        </div>
      </div>
    </div>`;
    const body = document.getElementById(id + '-body');
    if (body) body.innerHTML = html;

    const agents = [
      { name: 'chat', color: '#7c6bff', label: 'Chat' }, { name: 'code', color: '#2ecc71', label: 'Code' },
      { name: 'search', color: '#3498db', label: 'Search' }, { name: 'translator', color: '#f39c12', label: 'Translate' },
      { name: 'math', color: '#e74c3c', label: 'Math' }, { name: 'file', color: '#1abc9c', label: 'File' },
      { name: 'system', color: '#9b59b6', label: 'System' }, { name: 'network', color: '#e91e63', label: 'Network' },
      { name: 'image', color: '#ff6b6b', label: 'Image' }, { name: 'device', color: '#00b894', label: 'Device' },
      { name: 'data', color: '#6c5ce7', label: 'Data' }, { name: 'scheduler', color: '#fd79a8', label: 'Schedule' },
    ];
    const sidebar = document.getElementById('agent-sidebar-'+id);
    agents.forEach(a => {
      const el = document.createElement('div');
      el.className = 'agent-item';
      el.innerHTML = `<span class="agent-dot" style="background:${a.color}"></span><span>${a.label}</span>`;
      sidebar.appendChild(el);
    });

    const modes = ['auto', 'broadcast', 'chain', 'plan'];
    const modeContainer = document.getElementById('agent-mode-'+id);
    let currentMode = 'auto';
    modes.forEach(m => {
      const btn = document.createElement('button');
      btn.className = 'mode-btn' + (m === currentMode ? ' active' : '');
      btn.textContent = m;
      btn.onclick = () => {
        currentMode = m;
        modeContainer.querySelectorAll('.mode-btn').forEach(b => b.className = 'mode-btn');
        btn.className = 'mode-btn active';
      };
      modeContainer.appendChild(btn);
    });

    const msgs = document.getElementById('agent-msgs-'+id);
    addMsg(msgs, 'Welcome to AI Multi-Agent Chat! ' + agents.length + ' agents ready.', 'system');
    addMsg(msgs, 'Choose a mode: auto (smart routing), broadcast (all agents), chain (sequential), plan (multi-step).', 'system');

    window.sendAgentMsg = function(wid) {
      const input = document.getElementById('agent-input-'+wid);
      const msg = input.value.trim();
      if (!msg) return;
      input.value = '';
      const container = document.getElementById('agent-msgs-'+wid);
      addMsg(container, msg, 'user');
      const status = document.getElementById('agent-status-'+wid);
      status.innerHTML = '<span class="typing-dots"><span></span><span></span><span></span></span> Thinking...';
      extFetch('/agents/smart', { method: 'POST', body: { message: msg, mode: currentMode, session_id: 'desktop-' + wid } }).then(d => {
        status.textContent = 'Ready';
        if (d.primary) {
          const text = d.primary.response || d.primary.result || JSON.stringify(d.primary);
          addMsg(container, '[' + (d.primary.agent || 'AI') + '] ' + text, 'assistant');
          if (d.supporting && Object.keys(d.supporting).length > 0) {
            Object.entries(d.supporting).forEach(([agent, result]) => {
              if (result) addMsg(container, '[' + agent + '] ' + String(result).slice(0, 300), 'system');
            });
          }
        } else if (d.results) {
          Object.entries(d.results).forEach(([agent, result]) => {
            addMsg(container, '[' + agent + '] ' + String(result).slice(0, 300), 'assistant');
          });
        } else {
          addMsg(container, JSON.stringify(d).slice(0, 500), 'assistant');
        }
      }).catch(e => {
        status.textContent = 'Error';
        addMsg(container, 'Error: ' + e.message, 'system');
      });
    };
  }

  function addMsg(container, text, type) {
    const el = document.createElement('div');
    el.className = 'agent-msg ' + type;
    el.textContent = typeof text === 'string' ? text.slice(0, 2000) : JSON.stringify(text).slice(0, 2000);
    container.appendChild(el);
    container.scrollTop = container.scrollHeight;
  }

  // ─── System Info ────────────────────────────────────
  function systemInfo() {
    const id = launchWindow('System Information', '\u{1F4CB}', '<div id="sysinfo-'+id+'"><div class="text-center text-muted" style="padding:40px">Loading...</div></div>', 720, 520);
    extFetch('/system/hardware').then(d => {
      const body = document.getElementById('sysinfo-'+id);
      if (!body) return;
      const h = d;
      body.innerHTML = `
      <style>
        .si-grid { display:grid; grid-template-columns:1fr 1fr; gap:12px; }
        .si-card { background:var(--bg2); border:1px solid var(--border); border-radius:8px; padding:16px; }
        .si-card h3 { font-size:0.85em; color:var(--text2); margin-bottom:8px; text-transform:uppercase; letter-spacing:0.5px; }
        .si-row { display:flex; justify-content:space-between; padding:4px 0; font-size:0.88em; border-bottom:1px solid rgba(255,255,255,0.05); }
        .si-row:last-child { border:none; }
        .si-label { color:var(--text3); }
        .si-value { color:var(--text); font-weight:500; }
      </style>
      <div class="si-grid">
        <div class="si-card">
          <h3>CPU</h3>
          <div class="si-row"><span class="si-label">Model</span><span class="si-value">${h.cpu?.brand || h.cpu?.model || 'N/A'}</span></div>
          <div class="si-row"><span class="si-label">Cores</span><span class="si-value">${h.cpu?.cores || h.cpu?.count || 'N/A'}</span></div>
          <div class="si-row"><span class="si-label">Usage</span><span class="si-value">${h.cpu?.percent || 0}%</span></div>
        </div>
        <div class="si-card">
          <h3>Memory</h3>
          <div class="si-row"><span class="si-label">Total</span><span class="si-value">${h.memory ? (h.memory.total/1073741824).toFixed(1) + ' GB' : 'N/A'}</span></div>
          <div class="si-row"><span class="si-label">Used</span><span class="si-value">${h.memory ? (h.memory.used/1073741824).toFixed(1) + ' GB' : 'N/A'}</span></div>
          <div class="si-row"><span class="si-label">Usage</span><span class="si-value">${h.memory?.percent || 0}%</span></div>
        </div>
        <div class="si-card">
          <h3>Disk</h3>
          <div class="si-row"><span class="si-label">Total</span><span class="si-value">${h.disks ? (h.disks[0]?.total/1073741824).toFixed(1) + ' GB' : 'N/A'}</span></div>
          <div class="si-row"><span class="si-label">Free</span><span class="si-value">${h.disks ? (h.disks[0]?.free/1073741824).toFixed(1) + ' GB' : 'N/A'}</span></div>
          <div class="si-row"><span class="si-label">Usage</span><span class="si-value">${h.disks?.[0]?.percent || 0}%</span></div>
        </div>
        <div class="si-card">
          <h3>Platform</h3>
          <div class="si-row"><span class="si-label">OS</span><span class="si-value">${h.platform || h.os || 'N/A'}</span></div>
          <div class="si-row"><span class="si-label">Python</span><span class="si-value">${h.python || 'N/A'}</span></div>
          <div class="si-row"><span class="si-label">Host</span><span class="si-value">${h.hostname || 'N/A'}</span></div>
        </div>
      </div>`;
    }).catch(() => {});
  }

  // ─── Monitor Pro ────────────────────────────────────
  function monitorPro() {
    const id = launchWindow('Monitor Pro', '\u{1F4CA}', '<div id="monitor-'+id+'"><div class="text-center text-muted" style="padding:40px">Loading...</div></div>', 800, 550);
    const body = document.getElementById(id+'-body');
    if (!body) return;

    let histCpu = [], histMem = [], histCpu2 = [];
    function updateMonitor() {
      const el = document.getElementById('monitor-'+id);
      if (!el) return;
      extFetch('/desktop/stats').then(d => {
        histCpu.push(d.cpu || 0);
        histMem.push(d.memory?.percent || 0);
        if (histCpu.length > 60) { histCpu.shift(); histMem.shift(); }
        histCpu2 = histCpu.slice();

        const cpuPath = histCpu2.map((v,i) => `${i*2},${60 - v*0.6}`).join(' ');
        const memPath = histMem.map((v,i) => `${i*2},${60 - v*0.6}`).join(' ');

        el.innerHTML = `
        <style>
          .mp-grid { display:grid; grid-template-columns:1fr 1fr; gap:12px; padding:12px; }
          .mp-gauge { text-align:center; padding:20px; background:var(--bg2); border-radius:8px; border:1px solid var(--border); }
          .mp-gauge-value { font-size:2em; font-weight:700; }
          .mp-gauge-label { font-size:0.78em; color:var(--text2); margin-top:4px; }
          .mp-chart { grid-column:1/-1; background:var(--bg2); border-radius:8px; border:1px solid var(--border); padding:16px; }
          .mp-chart svg { width:100%; height:80px; }
          .mp-legend { display:flex; gap:16px; justify-content:center; font-size:0.78em; color:var(--text2); }
          .mp-legend span { display:flex; align-items:center; gap:4px; }
          .mp-legend span::before { content:''; width:10px; height:3px; border-radius:2px; display:inline-block; }
        </style>
        <div class="mp-grid">
          <div class="mp-gauge"><div class="mp-gauge-value" style="color:${d.cpu > 80 ? 'var(--danger)' : d.cpu > 50 ? 'var(--warning)' : 'var(--accent)'}">${d.cpu || 0}%</div><div class="mp-gauge-label">CPU</div></div>
          <div class="mp-gauge"><div class="mp-gauge-value" style="color:${d.memory?.percent > 80 ? 'var(--danger)' : d.memory?.percent > 50 ? 'var(--warning)' : 'var(--accent)'}">${d.memory?.percent || 0}%</div><div class="mp-gauge-label">RAM</div></div>
          <div class="mp-gauge"><div class="mp-gauge-value" style="color:${d.disk?.percent > 80 ? 'var(--danger)' : d.disk?.percent > 50 ? 'var(--warning)' : 'var(--accent)'}">${d.disk?.percent || 0}%</div><div class="mp-gauge-label">DISK</div></div>
          <div class="mp-gauge"><div class="mp-gauge-value">${Math.floor((d.uptime || 0) / 3600)}h</div><div class="mp-gauge-label">UPTIME</div></div>
          <div class="mp-chart">
            <svg viewBox="0 0 120 60">
              <polyline fill="none" stroke="var(--primary)" stroke-width="1.5" points="${cpuPath || '0,60'}"/>
              <polyline fill="none" stroke="var(--accent)" stroke-width="1.5" opacity="0.7" points="${memPath || '0,60'}"/>
            </svg>
            <div class="mp-legend">
              <span style="color:var(--primary)">CPU</span>
              <span style="color:var(--accent)">RAM</span>
            </div>
          </div>
        </div>`;
      }).catch(() => {});
    }
    updateMonitor();
    const interval = setInterval(updateMonitor, 2000);
    body._intervals = body._intervals || [];
    body._intervals.push(interval);
    body._cleanup = () => { body._intervals.forEach(i => clearInterval(i)); };
  }

  // ─── Package Manager ────────────────────────────────
  function packageManager() {
    const id = launchWindow('Package Manager', '\u{1F4E6}', '', 750, 500);
    const html = `
    <style>
      .pm-toolbar { display:flex; gap:8px; padding:12px; border-bottom:1px solid var(--border); }
      .pm-toolbar input { flex:1; padding:8px 12px; border-radius:4px; background:var(--bg2); border:1px solid var(--border); color:var(--text); }
      .pm-toolbar button { padding:8px 16px; border-radius:4px; border:none; cursor:pointer; font-weight:600; }
      .pm-install { background:var(--accent); color:white; }
      .pm-uninstall { background:var(--danger); color:white; }
      .pm-refresh { background:var(--bg3); color:var(--text); }
      .pm-list { padding:8px; max-height:380px; overflow-y:auto; }
      .pm-item { display:flex; justify-content:space-between; align-items:center; padding:8px 12px; border-bottom:1px solid rgba(255,255,255,0.05); font-size:0.88em; }
      .pm-item:last-child { border:none; }
      .pm-item-name { font-weight:600; }
      .pm-item-ver { color:var(--text3); font-size:0.8em; }
    </style>
    <div class="pm-toolbar">
      <input type="text" id="pm-input-${id}" placeholder="Package name...">
      <button class="pm-install" onclick="pmAction('${id}','install')">Install</button>
      <button class="pm-uninstall" onclick="pmAction('${id}','uninstall')">Uninstall</button>
      <button class="pm-refresh" onclick="pmList('${id}')">Refresh</button>
    </div>
    <div class="pm-list" id="pm-list-${id}"><div class="text-center text-muted" style="padding:20px">Click Refresh to list packages</div></div>`;
    const body = document.getElementById(id+'-body');
    if (body) body.innerHTML = html;
    window.pmAction = function(wid, action) {
      const pkg = document.getElementById('pm-input-'+wid).value.trim();
      if (!pkg) return;
      extFetch('/system/package/' + action, { method: 'POST', body: { package: pkg } }).then(d => {
        notify(action + 'ed ' + pkg + ': ' + (d.stdout || d.message || 'done'), d.error ? 'error' : 'success');
        pmList(wid);
      });
    };
    window.pmList = function(wid) {
      extFetch('/system/package/list').then(d => {
        const list = document.getElementById('pm-list-'+wid);
        if (!list) return;
        const pkgs = d.packages || d.result || [];
        if (pkgs.length === 0) { list.innerHTML = '<div class="text-center text-muted" style="padding:20px">No packages found</div>'; return; }
        list.innerHTML = pkgs.slice(0, 100).map(p => {
          const parts = p.split(/==|>=|<=|~/);
          return `<div class="pm-item"><span><span class="pm-item-name">${parts[0]}</span> <span class="pm-item-ver">${parts[1] || ''}</span></span></div>`;
        }).join('');
      }).catch(() => list.innerHTML = '<div class="text-center text-muted" style="padding:20px">Failed to load</div>');
    };
  }

  // ─── Update Manager ─────────────────────────────────
  function updateManager() {
    const id = launchWindow('Update Manager', '\u{1F504}', '<div id="upd-'+id+'"><div class="text-center text-muted" style="padding:40px">Checking...</div></div>', 650, 450);
    extFetch('/system/updates').then(d => {
      const el = document.getElementById('upd-'+id);
      if (!el) return;
      const updates = d.outdated || d.packages || [];
      if (updates.length === 0) {
        el.innerHTML = '<div class="text-center" style="padding:40px"><div style="font-size:3em;margin-bottom:16px">\u{2705}</div><div style="font-size:1.1em;color:var(--accent)">All packages are up to date!</div></div>';
        return;
      }
      el.innerHTML = `<div style="padding:16px">
        <div style="margin-bottom:12px;font-weight:600">${updates.length} update(s) available</div>
        ${updates.slice(0, 50).map(u => {
          const parts = u.split('==') || u.split(' ');
          return `<div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.05);font-size:0.88em">
            <span>${u.name || parts[0] || u}</span>
            <span style="color:var(--warning)">${u.installed || parts[1] || ''} \u{2192} ${u.latest || parts[2] || ''}</span>
          </div>`;
        }).join('')}
      </div>`;
    }).catch(() => {});
  }

  // ─── Disk Analyzer ──────────────────────────────────
  function diskAnalyzer() {
    const id = launchWindow('Disk Analyzer', '\u{1F50D}', '<div id="disk-'+id+'"><div class="text-center text-muted" style="padding:40px">Analyzing...</div></div>', 680, 480);
    extFetch('/system/disk/analyze').then(d => {
      const el = document.getElementById('disk-'+id);
      if (!el) return;
      const items = d.files || d.entries || [];
      if (items.length === 0) { el.innerHTML = '<div class="text-center text-muted" style="padding:40px">No data</div>'; return; }
      const total = items.reduce((s, i) => s + (i.size || 0), 0) || 1;
      el.innerHTML = `<div style="padding:16px">
        <div style="margin-bottom:12px;font-weight:600">Disk Usage</div>
        ${items.slice(0, 30).map(i => {
          const pct = ((i.size || 0) / total * 100);
          const color = pct > 30 ? 'var(--danger)' : pct > 15 ? 'var(--warning)' : 'var(--accent)';
          return `<div style="margin-bottom:8px">
            <div style="display:flex;justify-content:space-between;font-size:0.82em;margin-bottom:2px">
              <span>${i.name || i.path || '?'}</span>
              <span>${(i.size/1024/1024).toFixed(1)} MB (${pct.toFixed(1)}%)</span>
            </div>
            <div style="height:6px;background:var(--bg2);border-radius:3px;overflow:hidden">
              <div style="height:100%;width:${pct}%;background:${color};border-radius:3px;transition:width 0.5s"></div>
            </div>
          </div>`;
        }).join('')}
      </div>`;
    }).catch(() => {});
  }

  // ─── Speed Test ─────────────────────────────────────
  function speedTest() {
    const id = launchWindow('Speed Test', '\u{1F4E1}', '<div id="speed-'+id+'"><div class="text-center text-muted" style="padding:40px">Testing...</div></div>', 500, 350);
    const start = Date.now();
    fetch(API + '/system/version').then(() => {
      const ping = Date.now() - start;
      const el = document.getElementById('speed-'+id);
      if (!el) return;
      el.innerHTML = `
      <style>
        .st-result { text-align:center; padding:40px; }
        .st-ping { font-size:3em; font-weight:700; color:${ping < 50 ? 'var(--accent)' : ping < 150 ? 'var(--warning)' : 'var(--danger)'}; }
        .st-label { font-size:0.9em; color:var(--text2); margin-top:8px; }
        .st-details { display:flex; justify-content:center; gap:40px; margin-top:30px; }
        .st-detail { text-align:center; }
        .st-detail-val { font-size:1.3em; font-weight:600; }
        .st-detail-lbl { font-size:0.78em; color:var(--text3); }
      </style>
      <div class="st-result">
        <div class="st-ping">${ping}ms</div>
        <div class="st-label">Response Time</div>
        <div class="st-details">
          <div class="st-detail"><div class="st-detail-val">${ping < 50 ? 'Excellent' : ping < 150 ? 'Good' : 'Slow'}</div><div class="st-detail-lbl">Quality</div></div>
          <div class="st-detail"><div class="st-detail-val">${(navigator.connection?.downlink || '?')}</div><div class="st-detail-lbl">Mbps (est.)</div></div>
        </div>
      </div>`;
    }).catch(() => {});
  }

  // ─── Sensors ────────────────────────────────────────
  function sensorsApp() {
    const id = launchWindow('Sensors', '\u{1F321}\uFE0F', '<div id="sens-'+id+'"><div class="text-center text-muted" style="padding:40px">Loading...</div></div>', 600, 400);
    extFetch('/system/sensors').then(d => {
      const el = document.getElementById('sens-'+id);
      if (!el) return;
      const temps = d.temperatures || d.temps || [];
      const fans = d.fans || [];
      el.innerHTML = `
      <style>
        .sens-grid { display:grid; grid-template-columns:1fr 1fr; gap:12px; padding:16px; }
        .sens-card { background:var(--bg2); border:1px solid var(--border); border-radius:8px; padding:16px; text-align:center; }
        .sens-temp { font-size:2em; font-weight:700; }
        .sens-label { font-size:0.78em; color:var(--text2); margin-top:4px; }
      </style>
      <div class="sens-grid">
        ${(temps.length ? temps : [{name:'CPU',current:0,high:70},{name:'GPU',current:0,high:70}]).map(t => {
          const pct = t.high ? (t.current / t.high * 100) : 0;
          const color = pct > 80 ? 'var(--danger)' : pct > 50 ? 'var(--warning)' : 'var(--accent)';
          return `<div class="sens-card"><div class="sens-temp" style="color:${color}">${t.current ?? 0}\u00B0</div><div class="sens-label">${t.name || t.label || 'Sensor'}</div></div>`;
        }).join('')}
        ${fans.map(f => `<div class="sens-card"><div class="sens-temp" style="color:var(--info)">${f.current || 0} RPM</div><div class="sens-label">${f.name || 'Fan'}</div></div>`).join('')}
        ${!fans.length ? '<div class="sens-card"><div class="sens-temp" style="color:var(--text3);font-size:1.2em">N/A</div><div class="sens-label">Fans</div></div>' : ''}
      </div>`;
    }).catch(() => {});
  }

  // ─── System Logs ────────────────────────────────────
  function systemLogs() {
    const id = launchWindow('System Logs', '\u{1F4E2}', '<div id="logs-'+id+'"><div class="text-center text-muted" style="padding:40px">Loading...</div></div>', 800, 500);
    extFetch('/system/logs').then(d => {
      const el = document.getElementById('logs-'+id);
      if (!el) return;
      const lines = d.logs || d.lines || [];
      el.innerHTML = `
      <style>
        .log-line { padding:2px 0; font-size:0.78em; font-family:monospace; white-space:pre-wrap; word-break:break-all; color:var(--text2); }
        .log-line:hover { background:var(--bg2); }
        .log-line.err { color:var(--danger); }
        .log-line.warn { color:var(--warning); }
        .log-count { padding:8px 12px; font-size:0.8em; color:var(--text3); border-bottom:1px solid var(--border); }
      </style>
      <div class="log-count">${lines.length} entries</div>
      <div style="padding:8px;max-height:420px;overflow-y:auto">
        ${lines.slice(0, 200).map(l => {
          const cls = l.toLowerCase().includes('error') ? 'err' : l.toLowerCase().includes('warn') ? 'warn' : '';
          return `<div class="log-line ${cls}">${l}</div>`;
        }).join('')}
      </div>`;
    }).catch(() => {});
  }

  // ─── WiFi Scanner ───────────────────────────────────
  function wifiScanner() {
    const id = launchWindow('WiFi Scanner', '\u{1F4F6}', '<div id="wifi-'+id+'"><div class="text-center text-muted" style="padding:40px">Scanning...</div></div>', 600, 400);
    extFetch('/system/hardware').then(d => {
      const el = document.getElementById('wifi-'+id);
      if (!el) return;
      const ifaces = d.network || d.networks || d.interfaces || [];
      el.innerHTML = `
      <style>
        .wifi-item { display:flex; justify-content:space-between; padding:10px 16px; border-bottom:1px solid rgba(255,255,255,0.05); font-size:0.88em; }
        .wifi-item:last-child { border:none; }
        .wifi-name { font-weight:600; }
        .wifi-ip { color:var(--text3); font-size:0.82em; }
        .wifi-status { font-size:0.78em; }
      </style>
      <div style="padding:8px">
        <div style="padding:8px 12px;font-weight:600;border-bottom:1px solid var(--border);margin-bottom:8px">Network Interfaces</div>
        ${ifaces.length ? ifaces.map(i => `
          <div class="wifi-item">
            <span><span class="wifi-name">${i.name || i.interface || '?'}</span><br><span class="wifi-ip">${i.ip || i.address || 'No IP'}</span></span>
            <span class="wifi-status badge ${i.up || i.isup ? 'badge-success' : 'badge-danger'}">${i.up || i.isup ? 'UP' : 'DOWN'}</span>
          </div>
        `).join('') : '<div class="text-center text-muted" style="padding:20px">No interfaces found</div>'}
      </div>`;
    }).catch(() => {});
  }

  // ─── Location ───────────────────────────────────────
  function locationApp() {
    const id = launchWindow('Location', '\u{1F4CD}', '<div id="loc-'+id+'"><div class="text-center text-muted" style="padding:40px">Detecting...</div></div>', 500, 380);
    extFetch('/system/location').then(d => {
      const el = document.getElementById('loc-'+id);
      if (!el) return;
      el.innerHTML = `
      <style>
        .loc-card { text-align:center; padding:30px; }
        .loc-city { font-size:1.6em; font-weight:700; }
        .loc-region { color:var(--text2); margin-top:4px; }
        .loc-details { display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-top:24px; }
        .loc-detail { background:var(--bg2); border-radius:6px; padding:12px; }
        .loc-detail-label { font-size:0.75em; color:var(--text3); text-transform:uppercase; }
        .loc-detail-val { font-size:1.1em; font-weight:600; margin-top:2px; }
      </style>
      <div class="loc-card">
        <div style="font-size:3em;margin-bottom:8px">\u{1F30D}</div>
        <div class="loc-city">${d.city || 'Unknown'}</div>
        <div class="loc-region">${[d.region, d.country].filter(Boolean).join(', ')}</div>
        <div class="loc-details">
          <div class="loc-detail"><div class="loc-detail-label">ISP</div><div class="loc-detail-val">${d.isp || d.org || 'N/A'}</div></div>
          <div class="loc-detail"><div class="loc-detail-label">IP</div><div class="loc-detail-val">${d.ip || d.query || 'N/A'}</div></div>
          <div class="loc-detail"><div class="loc-detail-label">Latitude</div><div class="loc-detail-val">${d.lat || 'N/A'}</div></div>
          <div class="loc-detail"><div class="loc-detail-label">Longitude</div><div class="loc-detail-val">${d.lon || 'N/A'}</div></div>
        </div>
      </div>`;
    }).catch(() => {});
  }

  // ─── User Manager ───────────────────────────────────
  function userManager() {
    const id = launchWindow('User Manager', '\u{1F464}', `<div style="padding:20px;max-width:500px">
      <h3 style="margin-bottom:16px">User Accounts</h3>
      <div style="display:flex;flex-direction:column;gap:8px">
        ${['Admin (admin)', 'User (user)', 'Guest (guest)'].map(u => `
          <div style="display:flex;justify-content:space-between;align-items:center;padding:12px 16px;background:var(--bg2);border-radius:6px;border:1px solid var(--border)">
            <span><strong>${u}</strong></span>
            <span class="badge badge-success">Active</span>
          </div>
        `).join('')}
      </div>
      <p style="margin-top:16px;font-size:0.85em;color:var(--text2);padding:12px;background:var(--bg2);border-radius:6px">
        Default passwords: admin/admin, user/user, guest/(none)
      </p>
    </div>`, 500, 320);
  }

  // ─── Display Config ─────────────────────────────────
  function displayConfig() {
    const id = launchWindow('Display Config', '\u{1F5A5}\uFE0F', '<div id="disp-'+id+'"><div class="text-center text-muted" style="padding:40px">Loading...</div></div>', 550, 350);
    extFetch('/system/display').then(d => {
      const el = document.getElementById('disp-'+id);
      if (!el) return;
      el.innerHTML = `
      <style>
        .disp-card { padding:20px; }
        .disp-row { display:flex; justify-content:space-between; padding:8px 0; border-bottom:1px solid rgba(255,255,255,0.05); }
        .disp-row:last-child { border:none; }
      </style>
      <div class="disp-card">
        <h3 style="margin-bottom:12px">Display Information</h3>
        <div class="disp-row"><span style="color:var(--text3)">Resolution</span><span style="font-weight:600">${d.resolution || d.current || 'N/A'}</span></div>
        <div class="disp-row"><span style="color:var(--text3)">Output</span><span>${d.output || d.connected || 'N/A'}</span></div>
        <div class="disp-row"><span style="color:var(--text3)">Connected</span><span class="badge ${d.connected || d.active ? 'badge-success' : 'badge-danger'}">${d.connected || d.active ? 'Yes' : 'No'}</span></div>
      </div>`;
    }).catch(() => {});
  }

  // ─── Agent Company (50-Agent Enterprise) ────────────
  function agentCompany() {
    const id = launchWindow('AI Enterprise - 50 Agents', '\u{1F3E2}', '', 900, 620);
    const html = `
    <style>
      .ac-layout { display:flex; height:100%; gap:0; }
      .ac-sidebar { width:200px; background:var(--bg2); border-right:1px solid var(--border); padding:8px; overflow-y:auto; flex-shrink:0; }
      .ac-main { flex:1; display:flex; flex-direction:column; }
      .ac-header { padding:12px 16px; border-bottom:1px solid var(--border); font-weight:600; font-size:0.9em; display:flex; align-items:center; gap:8px; }
      .ac-badge { background:var(--primary); color:white; padding:2px 8px; border-radius:10px; font-size:0.72em; }
      .ac-dept { margin-bottom:8px; }
      .ac-dept-title { font-size:0.78em; color:var(--text3); text-transform:uppercase; letter-spacing:0.5px; padding:4px 8px; margin-bottom:2px; }
      .ac-agent { padding:5px 8px; border-radius:4px; font-size:0.78em; cursor:pointer; transition:0.15s; display:flex; align-items:center; gap:6px; }
      .ac-agent:hover { background:var(--bg3); }
      .ac-agent .dot { width:6px; height:6px; border-radius:50%; }
      .ac-agent .name { color:var(--text2); }
      .ac-chat { flex:1; overflow-y:auto; padding:16px; display:flex; flex-direction:column; gap:8px; }
      .ac-msg { padding:8px 12px; border-radius:6px; font-size:0.82em; max-width:90%; }
      .ac-msg.user { background:var(--primary); color:white; align-self:flex-end; }
      .ac-msg.agent { background:var(--bg2); border:1px solid var(--border); align-self:flex-start; }
      .ac-msg.system { background:rgba(255,165,2,0.1); border-left:3px solid var(--warning); align-self:center; font-size:0.75em; }
      .ac-input { display:flex; gap:8px; padding:12px; border-top:1px solid var(--border); }
      .ac-input input { flex:1; padding:8px 12px; border-radius:4px; background:var(--bg2); border:1px solid var(--border); color:var(--text); font-size:0.88em; }
      .ac-input input:focus { border-color:var(--primary); }
      .ac-input button { padding:8px 20px; border-radius:4px; background:var(--primary); color:white; border:none; cursor:pointer; font-weight:600; }
      .ac-modes { display:flex; gap:4px; padding:6px 12px; border-bottom:1px solid var(--border); }
      .ac-mode-btn { padding:3px 10px; border-radius:10px; border:1px solid var(--border); background:transparent; color:var(--text2); cursor:pointer; font-size:0.72em; }
      .ac-mode-btn.active { background:var(--primary); color:white; border-color:var(--primary); }
      .ac-org-btn { padding:6px 12px; border-radius:4px; background:var(--bg3); border:none; color:var(--text); cursor:pointer; font-size:0.78em; margin-left:auto; }
    </style>
    <div class="ac-layout">
      <div class="ac-sidebar" id="ac-sidebar-${id}"><div class="text-center text-muted" style="padding:20px;font-size:0.78em">Loading org chart...</div></div>
      <div class="ac-main">
        <div class="ac-header">
          <span>AI Enterprise</span>
          <span class="ac-badge" id="ac-count-${id}">50 agents</span>
          <div class="ac-modes" id="ac-modes-${id}"></div>
          <button class="ac-org-btn" onclick="showCompanyOrg('${id}')">Org Chart</button>
        </div>
        <div class="ac-chat" id="ac-chat-${id}">
          <div class="ac-msg system">50-Agent AI Enterprise ready. CEO + 7 departments + team leads + specialist workers.</div>
          <div class="ac-msg system">Modes: auto (smart route), org (all depts), pipeline (dev-qa-sec-ops-docs)</div>
        </div>
        <div class="ac-input">
          <input type="text" id="ac-input-${id}" placeholder="Ask the enterprise..." onkeydown="if(event.key==='Enter')sendCompanyMsg('${id}')">
          <button onclick="sendCompanyMsg('${id}')">Send to Enterprise</button>
        </div>
      </div>
    </div>`;
    const body = document.getElementById(id+'-body');
    if (body) body.innerHTML = html;

    // Mode buttons
    const modes = ['auto', 'org', 'pipeline'];
    let currentMode = 'auto';
    const mc = document.getElementById('ac-modes-'+id);
    modes.forEach(m => {
      const btn = document.createElement('button');
      btn.className = 'ac-mode-btn' + (m === currentMode ? ' active' : '');
      btn.textContent = m;
      btn.onclick = () => { currentMode = m; mc.querySelectorAll('.ac-mode-btn').forEach(b => b.className = 'ac-mode-btn'); btn.className = 'ac-mode-btn active'; };
      mc.appendChild(btn);
    });

    // Load org
    extFetch('/company/stats').then(d => {
      const sidebar = document.getElementById('ac-sidebar-'+id);
      const count = document.getElementById('ac-count-'+id);
      if (!sidebar) return;
      count.textContent = d.total_agents + ' agents';
      const depts = d.departments || {};
      const agents = d.agent_list || [];
      const byDept = {};
      agents.forEach(a => { if (!byDept[a.dept]) byDept[a.dept] = []; byDept[a.dept].push(a); });
      let html = '';
      Object.entries(byDept).slice(0, 8).forEach(([dept, members]) => {
        html += '<div class="ac-dept"><div class="ac-dept-title">' + dept + ' (' + members.length + ')</div>';
        members.slice(0, 6).forEach(m => {
          const colors = {Executive:'#7c6bff',Development:'#2ecc71',Quality:'#f39c12',Security:'#e74c3c',Operations:'#3498db',Creative:'#e91e63',Data:'#9b59b6',Support:'#1abc9c'};
          html += '<div class="ac-agent"><span class="dot" style="background:'+(colors[dept]||'#888')+'"></span><span class="name">' + m.role.split(' ').slice(0,2).join(' ') + '</span></div>';
        });
        html += '</div>';
      });
      sidebar.innerHTML = html;
    });

    window.sendCompanyMsg = function(wid) {
      const input = document.getElementById('ac-input-'+wid);
      const msg = input.value.trim();
      if (!msg) return;
      input.value = '';
      const chat = document.getElementById('ac-chat-'+wid);
      addMsg(chat, msg, 'user');
      extFetch('/company/process', {method:'POST', body:{message:msg, mode:currentMode}}).then(d => {
        if (d.results) {
          d.results.forEach(r => {
            const text = '[' + (r.role || r.agent) + '] ' + (r.result?.summary || r.result || JSON.stringify(r)).slice(0, 300);
            addMsg(chat, text, 'agent');
          });
        }
        if (d.mode) addMsg(chat, 'Mode: ' + d.mode + ' | ' + d.agents_involved + ' agents involved', 'system');
      }).catch(e => addMsg(chat, 'Error: ' + e.message, 'system'));
    };

    window.showCompanyOrg = function(wid) {
      extFetch('/company/org').then(d => {
        const chat = document.getElementById('ac-chat-'+wid);
        if (!chat) return;
        const agents = Object.entries(d).slice(0, 50);
        let text = '=== ORGANIZATION CHART ===\n';
        const byParent = {};
        agents.forEach(([id, info]) => { const p = info.parent || 'none'; if (!byParent[p]) byParent[p] = []; byParent[p].push(id); });
        function printTree(parent, indent) {
          (byParent[parent] || []).forEach(id => {
            const info = d[id];
            text += indent + id + ' (' + info.role + ')' + '\n';
            printTree(id, indent + '  ');
          });
        }
        printTree('none', '');
        addMsg(chat, text, 'system');
      });
    };
  }

  // ─── Document Viewer ────────────────────────────────
  function documentViewer() {
    const id = launchWindow('Document Viewer', '\u{1F4C4}', '', 850, 560);
    const html = `
    <style>
      .dv-layout { display:flex; height:100%; }
      .dv-sidebar { width:220px; background:var(--bg2); border-right:1px solid var(--border); display:flex; flex-direction:column; }
      .dv-search { padding:8px; border-bottom:1px solid var(--border); }
      .dv-search input { width:100%; padding:6px 10px; border-radius:4px; background:var(--bg); border:1px solid var(--border); color:var(--text); font-size:0.8em; }
      .dv-files { flex:1; overflow-y:auto; padding:4px; }
      .dv-file { padding:6px 8px; border-radius:4px; cursor:pointer; font-size:0.8em; transition:0.15s; display:flex; align-items:center; gap:6px; }
      .dv-file:hover { background:var(--bg3); }
      .dv-file.active { background:var(--primary); color:white; }
      .dv-file .ext { font-size:0.7em; opacity:0.7; }
      .dv-content { flex:1; display:flex; flex-direction:column; overflow:hidden; }
      .dv-toolbar { padding:8px 12px; border-bottom:1px solid var(--border); display:flex; gap:8px; align-items:center; font-size:0.82em; }
      .dv-toolbar button { padding:4px 12px; border-radius:4px; border:1px solid var(--border); background:transparent; color:var(--text2); cursor:pointer; font-size:0.8em; }
      .dv-toolbar button:hover { background:var(--bg3); color:var(--text); }
      .dv-body { flex:1; overflow:auto; padding:16px; font-size:0.88em; line-height:1.5; white-space:pre-wrap; font-family:monospace; }
    </style>
    <div class="dv-layout">
      <div class="dv-sidebar">
        <div class="dv-search"><input type="text" placeholder="Search files..." oninput="searchDocs('${id}',this.value)"></div>
        <div class="dv-files" id="dv-files-${id}"><div class="text-center text-muted" style="padding:20px;font-size:0.8em">Loading...</div></div>
      </div>
      <div class="dv-content">
        <div class="dv-toolbar">
          <span id="dv-file-name-${id}" style="font-weight:600">No file selected</span>
          <span id="dv-file-info-${id}" class="text-muted" style="font-size:0.8em;margin-left:8px"></span>
          <button onclick="loadDocDir('${id}')" style="margin-left:auto">Refresh</button>
        </div>
        <div class="dv-body" id="dv-body-${id}">
          <div class="text-center text-muted" style="padding:40px;font-size:0.9em">Select a file from the sidebar to preview</div>
        </div>
      </div>
    </div>`;
    const body = document.getElementById(id+'-body');
    if (body) body.innerHTML = html;
    loadDocDir(id);

    window.loadDocDir = function(wid) {
      extFetch('/documents/list', {method:'POST', body:{}}).then(d => {
        const list = document.getElementById('dv-files-'+wid);
        if (!list) return;
        if (d.error) { list.innerHTML = '<div class="text-center text-muted" style="padding:20px;font-size:0.8em">' + d.error + '</div>'; return; }
        const files = Array.isArray(d) ? d : [];
        list.innerHTML = files.map(f => {
          const icon = f.type === 'dir' ? '\u{1F4C1}' : '\u{1F4C4}';
          return '<div class="dv-file" onclick="openDoc(\''+wid+'\',\''+f.path.replace(/\\\\/g,'/')+'\')"><span>' + icon + '</span><span>' + f.name + '</span><span class="ext">' + (f.ext || '') + '</span></div>';
        }).join('') || '<div class="text-center text-muted" style="padding:20px;font-size:0.8em">Empty directory</div>';
      });
    };

    window.openDoc = function(wid, path) {
      document.getElementById('dv-file-name-'+wid).textContent = path.split('/').pop() || path;
      document.getElementById('dv-body-'+wid).innerHTML = '<div class="text-center text-muted" style="padding:40px">Loading...</div>';
      extFetch('/documents/preview', {method:'POST', body:{path}}).then(d => {
        const body = document.getElementById('dv-body-'+wid);
        if (!body) return;
        document.getElementById('dv-file-info-'+wid).textContent = d.size ? (d.size/1024).toFixed(1) + ' KB' : '';
        if (d.type === 'text' || d.content) {
          const content = d.content || d.paragraphs?.join('\n') || '';
          body.innerHTML = '<pre style="margin:0;white-space:pre-wrap;word-break:break-word;font-family:monospace;font-size:0.85em;color:var(--text2)">' + escapeHtml(content.slice(0, 50000)) + '</pre>';
        } else if (d.type === 'pdf') {
          let text = '';
          (d.content || []).forEach(p => { text += p.text + '\n'; });
          body.innerHTML = '<div style="font-size:0.85em;color:var(--text2)">' + escapeHtml(text.slice(0, 50000)) + '</div>';
        } else if (d.type === 'xlsx' && d.sheets) {
          let html = '';
          d.sheets.forEach(s => {
            html += '<h4 style="margin:12px 0 6px;color:var(--accent)">' + s.name + ' (' + (s.rows?.length||0) + ' rows)</h4>';
            html += '<table style="border-collapse:collapse;font-size:0.78em;width:100%">';
            (s.rows || []).slice(0, 50).forEach(row => {
              html += '<tr>' + row.map(c => '<td style="padding:2px 8px;border:1px solid var(--border);max-width:200px;overflow:hidden">' + escapeHtml(String(c).slice(0, 100)) + '</td>').join('') + '</tr>';
            });
            html += '</table>';
          });
          body.innerHTML = html;
        } else if (d.error) {
          body.innerHTML = '<div style="padding:20px;color:var(--danger)">Error: ' + d.error + '</div>';
        } else {
          body.innerHTML = '<div class="text-center text-muted" style="padding:40px">Preview not available for this file type</div>';
        }
      });
    };

    window.searchDocs = function(wid, q) {
      if (!q || q.length < 2) { loadDocDir(wid); return; }
      extFetch('/documents/search', {method:'POST', body:{query:q}}).then(d => {
        const list = document.getElementById('dv-files-'+wid);
        if (!list) return;
        const files = Array.isArray(d) ? d : [];
        list.innerHTML = files.slice(0, 30).map(f => {
          return '<div class="dv-file" onclick="openDoc(\''+wid+'\',\''+f.path.replace(/\\\\/g,'/')+'\')"><span>\u{1F4C4}</span><span>' + f.name + '</span><span class="ext">' + (f.size ? (f.size/1024).toFixed(0)+'KB' : '') + '</span></div>';
        }).join('') || '<div class="text-center text-muted" style="padding:20px;font-size:0.8em">No results</div>';
      });
    };

    function escapeHtml(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }
  }

  // ─── Video Player ───────────────────────────────────
  function videoPlayer() {
    const id = launchWindow('Video Player', '\u{1F4FA}', '', 800, 500);
    setWindowContent(id, `
    <style>
      .vp-body { padding:0; display:flex; flex-direction:column; height:100%; background:#000; }
      .vp-screen { flex:1; display:flex; align-items:center; justify-content:center; background:#000; position:relative; }
      .vp-screen video { max-width:100%; max-height:100%; }
      .vp-toolbar { padding:8px 12px; background:var(--bg2); display:flex; gap:8px; align-items:center; border-top:1px solid var(--border); }
      .vp-toolbar input { flex:1; padding:6px 10px; border-radius:4px; background:var(--bg); border:1px solid var(--border); color:var(--text); font-size:0.8em; }
      .vp-toolbar button { padding:6px 16px; border-radius:4px; border:none; background:var(--primary); color:white; cursor:pointer; font-size:0.8em; }
      .vp-placeholder { color:#444; font-size:1.5em; }
    </style>
    <div class="vp-body">
      <div class="vp-screen" id="vp-screen-${id}"><div class="vp-placeholder">Enter video URL to play</div></div>
      <div class="vp-toolbar">
        <input type="text" id="vp-url-${id}" placeholder="Video file path or URL..." value="/storage/sample.mp4">
        <button onclick="playVideo('${id}')">Play</button>
        <button onclick="document.getElementById('vp-video-${id}')?.pause()" style="background:var(--bg3)">Pause</button>
      </div>
    </div>`);

    window.playVideo = function(wid) {
      const url = document.getElementById('vp-url-'+wid).value.trim();
      if (!url) return;
      const screen = document.getElementById('vp-screen-'+wid);
      const existing = document.getElementById('vp-video-'+wid);
      if (existing) existing.remove();
      const video = document.createElement('video');
      video.id = 'vp-video-'+wid;
      video.controls = true;
      video.style.maxWidth = '100%';
      video.style.maxHeight = '100%';
      video.src = API + '/media/stream/' + url.replace(/^\/storage\//,'');
      video.load();
      screen.innerHTML = '';
      screen.appendChild(video);
    };
  }

  // ─── Audio Player ───────────────────────────────────
  function audioPlayer() {
    const id = launchWindow('Audio Player', '\u{1F3B5}', '', 500, 380);
    setWindowContent(id, `
    <style>
      .ap-body { display:flex; flex-direction:column; align-items:center; justify-content:center; height:100%; padding:30px; }
      .ap-icon { font-size:5em; margin-bottom:16px; animation:pulse 2s infinite; }
      @keyframes pulse { 0%,100% { transform:scale(1); opacity:0.6; } 50% { transform:scale(1.1); opacity:1; } }
      .ap-title { font-size:1.1em; font-weight:600; margin-bottom:8px; }
      .ap-controls { display:flex; gap:12px; margin:16px 0; }
      .ap-controls button { width:44px; height:44px; border-radius:50%; border:none; background:var(--primary); color:white; cursor:pointer; font-size:1.2em; display:flex; align-items:center; justify-content:center; transition:0.2s; }
      .ap-controls button:hover { transform:scale(1.1); }
      .ap-input { display:flex; gap:8px; width:100%; margin-top:12px; }
      .ap-input input { flex:1; padding:8px 12px; border-radius:4px; background:var(--bg2); border:1px solid var(--border); color:var(--text); font-size:0.85em; }
      .ap-input button { padding:8px 16px; border-radius:4px; border:none; background:var(--accent); color:white; cursor:pointer; }
      .ap-status { font-size:0.8em; color:var(--text3); margin-top:8px; }
    </style>
    <div class="ap-body">
      <div class="ap-icon">&#x1F3B5;</div>
      <div class="ap-title">Audio Player</div>
      <audio id="ap-audio-${id}" controls style="width:100%;margin:8px 0"></audio>
      <div class="ap-input">
        <input type="text" id="ap-url-${id}" placeholder="Audio file path..." value="/storage/sample.mp3">
        <button onclick="playAudio('${id}')">Play</button>
      </div>
      <div class="ap-status">Supported: mp3, wav, ogg, flac, m4a</div>
    </div>`);

    window.playAudio = function(wid) {
      const url = document.getElementById('ap-url-'+wid).value.trim();
      if (!url) return;
      const audio = document.getElementById('ap-audio-'+wid);
      audio.src = API + '/media/stream/' + url.replace(/^\/storage\//,'');
      audio.play();
    };
  }

  // ─── 3D Bike Race Game ──────────────────────────────
  function bikeRace() {
    const id = launchWindow('Bike Race 3D', '\u{1F3CE}\uFE0F', '', 900, 600);
    setWindowContent(id, '<iframe class="app-iframe" src="apps/games/bike-race.html" style="background:#000"></iframe>');
  }

  // ─── Register all extension apps ────────────────────
  const APPS = [
    { name: 'ai-chat', label: 'AI Chat', icon: '\u{1F4AC}', handler: aiChat, category: 'ai' },
    { name: 'agent-company', label: 'AI Enterprise', icon: '\u{1F3E2}', handler: agentCompany, category: 'ai' },
    { name: 'monitor-pro', label: 'Monitor Pro', icon: '\u{1F4CA}', handler: monitorPro, category: 'system' },
    { name: 'system-info', label: 'System Info', icon: '\u{1F4CB}', handler: systemInfo, category: 'system' },
    { name: 'document-viewer', label: 'Doc Viewer', icon: '\u{1F4C4}', handler: documentViewer, category: 'office' },
    { name: 'video-player', label: 'Video Player', icon: '\u{1F4FA}', handler: videoPlayer, category: 'media' },
    { name: 'audio-player', label: 'Audio Player', icon: '\u{1F3B5}', handler: audioPlayer, category: 'media' },
    { name: 'bike-race', label: 'Bike Race 3D', icon: '\u{1F3CE}\uFE0F', handler: bikeRace, category: 'games' },
    { name: 'package-manager', label: 'Packages', icon: '\u{1F4E6}', handler: packageManager, category: 'system' },
    { name: 'update-manager', label: 'Updates', icon: '\u{1F504}', handler: updateManager, category: 'system' },
    { name: 'disk-analyzer', label: 'Disk Analyzer', icon: '\u{1F50D}', handler: diskAnalyzer, category: 'system' },
    { name: 'speed-test', label: 'Speed Test', icon: '\u{1F4E1}', handler: speedTest, category: 'system' },
    { name: 'sensors', label: 'Sensors', icon: '\u{1F321}\uFE0F', handler: sensorsApp, category: 'system' },
    { name: 'system-logs', label: 'Logs', icon: '\u{1F4E2}', handler: systemLogs, category: 'system' },
    { name: 'wifi-scanner', label: 'WiFi', icon: '\u{1F4F6}', handler: wifiScanner, category: 'system' },
    { name: 'location', label: 'Location', icon: '\u{1F4CD}', handler: locationApp, category: 'system' },
    { name: 'user-manager', label: 'Users', icon: '\u{1F464}', handler: userManager, category: 'system' },
    { name: 'display-config', label: 'Display', icon: '\u{1F5A5}\uFE0F', handler: displayConfig, category: 'system' },
  ];

  if (typeof window !== 'undefined') {
    window.DESKTOP_APPS = APPS;
    // Register into app launcher
    APPS.forEach(a => {
      if (window.APP_REGISTRY) {
        window.APP_REGISTRY.push(a);
      }
    });
  }
})();
