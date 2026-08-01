/* ═══════════════════════════════════════════════════════
   Web OS v1.0 — Complete Desktop Environment
   Window Manager, Taskbar, Notifications, Login, Apps
   ═══════════════════════════════════════════════════════ */

let API = '/api';
let TOKEN = localStorage.getItem('token') || '';
let CURRENT_USER = { name: 'Admin', role: 'admin', avatar: 'A' };
let WINDOW_ID = 0;
let WINDOWS = {};
let Z_INDEX = 100;
let APP_REGISTRY = [];
let START_APPS = [];

// ═══════════════════════════════════════════════════════
// AUTH
// ═══════════════════════════════════════════════════════

const USERS = [
  { name: 'Admin', role: 'admin', password: 'admin', avatar: 'A', color: '#7c6bff' },
  { name: 'User', role: 'user', password: 'user', avatar: 'U', color: '#33c748' },
  { name: 'Guest', role: 'guest', password: '', avatar: 'G', color: '#3498db' },
];

function initLogin() {
  const container = document.getElementById('login-users');
  USERS.forEach((u, i) => {
    const el = document.createElement('div');
    el.className = 'login-user' + (i === 0 ? ' active' : '');
    el.innerHTML = `<div class="login-user-avatar" style="background:${u.color}">${u.avatar}</div><div class="login-user-name">${u.name}</div>`;
    el.onclick = () => selectUser(i);
    container.appendChild(el);
  });
}

let selectedUser = 0;
function selectUser(i) {
  selectedUser = i;
  document.querySelectorAll('.login-user').forEach((el, idx) => el.className = 'login-user' + (idx === i ? ' active' : ''));
  document.getElementById('login-password').value = '';
  document.getElementById('login-error').textContent = '';
  if (!USERS[i].password) doLogin();
}

async function doLogin() {
  const user = USERS[selectedUser];
  const pass = document.getElementById('login-password').value || user.password;
  if (user.password && pass !== user.password) {
    document.getElementById('login-error').textContent = 'Incorrect password';
    return;
  }
  if (user.role === 'guest') {
    TOKEN = 'guest-token';
    CURRENT_USER = user;
    showDesktop();
    return;
  }
  try {
    const r = await fetch(`${API}/auth/login`, {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({username: user.name.toLowerCase(), password: pass})
    });
    const d = await r.json();
    if (d.token) {
      TOKEN = d.token;
      localStorage.setItem('token', TOKEN);
      CURRENT_USER = user;
      showDesktop();
    } else {
      document.getElementById('login-error').textContent = 'Login failed';
    }
  } catch (e) {
    TOKEN = 'offline-token';
    CURRENT_USER = user;
    showDesktop();
  }
}

function lockScreen() {
  document.getElementById('desktop').style.display = 'none';
  document.getElementById('login-screen').style.display = 'flex';
  document.getElementById('login-password').value = '';
  document.getElementById('login-error').textContent = '';
  closeAllWindows();
  closeStartMenu();
}

// ═══════════════════════════════════════════════════════
// DESKTOP
// ═══════════════════════════════════════════════════════

function updateClock() {
  const now = new Date();
  const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  const dateStr = now.toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' });
  
  const clockTray = document.getElementById('tray-clock');
  if (clockTray) clockTray.textContent = timeStr;

  const widgetTime = document.getElementById('widget-time-display');
  if (widgetTime) widgetTime.textContent = timeStr;

  const widgetDate = document.getElementById('widget-date-display');
  if (widgetDate) widgetDate.textContent = dateStr;
}

function initDesktopWidgets() {
  updateClock();
  fetch('/api/system/network-details').then(r => r.json()).then(d => {
    const badge = document.getElementById('widget-ip-display');
    if (badge && d.primary_ip) {
      badge.innerHTML = `🌐 LAN: <strong>http://${d.primary_ip}:${d.http_port || 8080}</strong>`;
    }
  }).catch(() => {});
}

function showDesktop() {
  const loginScreen = document.getElementById('login-screen');
  if (loginScreen) loginScreen.style.display = 'none';
  const desktop = document.getElementById('desktop');
  if (desktop) desktop.style.display = 'flex';
  
  const nameEl = document.getElementById('start-user-name');
  if (nameEl) nameEl.textContent = CURRENT_USER.name || 'Admin';
  const avatarEl = document.getElementById('start-user-avatar');
  if (avatarEl) avatarEl.textContent = CURRENT_USER.avatar || 'A';

  initDesktopIcons();
  initStartMenu();
  initDesktopWidgets();
  setInterval(updateClock, 1000);

  document.addEventListener('click', (e) => {
    if (!e.target.closest('#start-menu') && !e.target.closest('#start-btn')) closeStartMenu();
    if (!e.target.closest('.context-menu')) {
      const menu = document.getElementById('desktop-context-menu');
      if (menu) menu.style.display = 'none';
    }
  });
  document.addEventListener('keydown', handleKeyboardShortcuts);
}

function initDesktopIcons() {
  const container = document.getElementById('desktop-icons');
  container.innerHTML = '';
  const icons = [
    { icon: '\u{1F4F6}', label: 'Network & IP', app: 'network-info' },
    { icon: '\u{1F4C1}', label: 'File Manager', app: 'file-manager' },
    { icon: '\u{1F4BB}', label: 'Terminal', app: 'terminal' },
    { icon: '\u{1F4DD}', label: 'Text Editor', app: 'text-editor' },
    { icon: '\u{1F3AC}', label: 'App Store', app: 'app-store' },
    { icon: '\u{2699}\uFE0F', label: 'Settings', app: 'settings' },
    { icon: '\u{1F4F7}', label: 'Camera', app: 'camera' },
    { icon: '\u{1F3B5}', label: 'Music', app: 'music-player' },
    { icon: '\u{1F4FA}', label: 'Video', app: 'video-player' },
  ];
  icons.forEach(ic => {
    const el = document.createElement('div');
    el.className = 'desktop-icon';
    el.innerHTML = `<div class="desktop-icon-img">${ic.icon}</div><div class="desktop-icon-label">${ic.label}</div>`;
    el.ondblclick = () => launchApp(ic.app);
    el.oncontextmenu = (e) => { e.preventDefault(); showContextMenu(e, [{label: 'Open', action: () => launchApp(ic.app)}]); };
    container.appendChild(el);
  });
}

// ═══════════════════════════════════════════════════════
// START MENU
// ═══════════════════════════════════════════════════════

function initStartMenu() {
  const apps = [
    { icon: '\u{1F4F6}', label: 'Network & IP Info', app: 'network-info', color: '#00b894' },
    { icon: '\u{1F4C1}', label: 'File Manager', app: 'file-manager', color: '#3498db' },
    { icon: '\u{1F4BB}', label: 'Terminal', app: 'terminal', color: '#2ecc71' },
    { icon: '\u{1F4DD}', label: 'Text Editor', app: 'text-editor', color: '#f39c12' },
    { icon: '\u{1F4AC}', label: 'AI Chat', app: 'ai-chat', color: '#7c6bff' },
    { icon: '\u{1F4CA}', label: 'Monitor Pro', app: 'monitor-pro', color: '#e74c3c' },
    { icon: '\u{2699}\uFE0F', label: 'Settings', app: 'settings', color: '#95a5a6' },
    { icon: '\u{1F4E6}', label: 'Packages', app: 'package-manager', color: '#1abc9c' },
    { icon: '\u{1F504}', label: 'Updates', app: 'update-manager', color: '#9b59b6' },
    { icon: '\u{1F50D}', label: 'Disk Analyzer', app: 'disk-analyzer', color: '#e67e22' },
    { icon: '\u{1F4E1}', label: 'Speed Test', app: 'speed-test', color: '#2ecc71' },
    { icon: '\u{1F321}\uFE0F', label: 'Sensors', app: 'sensors', color: '#e74c3c' },
    { icon: '\u{1F4CB}', label: 'System Info', app: 'system-info', color: '#3498db' },
    { icon: '\u{1F4BB}', label: 'WebApps', app: 'web-apps', color: '#1abc9c' },
    { icon: '\u{1F4F7}', label: 'Camera', app: 'camera', color: '#f1c40f' },
    { icon: '\u{1F3B5}', label: 'Music', app: 'music-player', color: '#e91e63' },
    { icon: '\u{1F4FA}', label: 'Video', app: 'video-player', color: '#9b59b6' },
    { icon: '\u{1F5A8}\uFE0F', label: 'Paint', app: 'paint', color: '#ff6b6b' },
    { icon: '\u{1F9E9}', label: 'Games', app: 'games', color: '#ffa502' },
    { icon: '\u{1F5C3}\uFE0F', label: 'Files', app: 'files', color: '#2ed573' },
    { icon: '\u{1F579}\uFE0F', label: 'Whiteboard', app: 'whiteboard', color: '#3742fa' },
    { icon: '\u{1F4CB}', label: 'Notes', app: 'notes', color: '#ff6348' },
    { icon: '\u{1F4C5}', label: 'Calendar', app: 'calendar', color: '#a29bfe' },
    { icon: '\u{1F4CE}', label: 'Todos', app: 'todos', color: '#fd79a8' },
    { icon: '\u{1F3E0}', label: 'Weather', app: 'weather', color: '#74b9ff' },
    { icon: '\u{1F4F6}', label: 'WiFi', app: 'wifi-scanner', color: '#00b894' },
    { icon: '\u{1F4CD}', label: 'Location', app: 'location', color: '#6c5ce7' },
    { icon: '\u{1F4E2}', label: 'System Logs', app: 'system-logs', color: '#636e72' },
    { icon: '\u{1F464}', label: 'Users', app: 'user-manager', color: '#dfe6e9' },
    { icon: '\u{1F4F1}', label: 'Remote', app: 'remote-desktop', color: '#00cec9' },
  ];
  START_APPS = apps;
  renderStartApps(apps);
}

function renderStartApps(apps) {
  const container = document.getElementById('start-apps');
  container.innerHTML = '';
  apps.forEach(a => {
    const el = document.createElement('div');
    el.className = 'start-app-item';
    el.innerHTML = `<div class="sai-icon" style="background:${a.color}20;color:${a.color}">${a.icon}</div><div>${a.label}</div>`;
    el.onclick = () => { launchApp(a.app); closeStartMenu(); };
    container.appendChild(el);
  });
}

function filterStartApps(q) {
  if (!q) { renderStartApps(START_APPS); return; }
  const filtered = START_APPS.filter(a => a.label.toLowerCase().includes(q.toLowerCase()) || a.app.toLowerCase().includes(q.toLowerCase()));
  renderStartApps(filtered);
}

function toggleStartMenu() {
  const m = document.getElementById('start-menu');
  m.style.display = m.style.display === 'none' ? 'flex' : 'none';
  if (m.style.display === 'flex') document.getElementById('start-search').focus();
}

function closeStartMenu() {
  document.getElementById('start-menu').style.display = 'none';
}

// ═══════════════════════════════════════════════════════
// WINDOW MANAGER
// ═══════════════════════════════════════════════════════

function createWindow(opts) {
  const id = 'win-' + (++WINDOW_ID);
  const title = opts.title || 'Window';
  const icon = opts.icon || '\u{1F4C4}';
  const width = opts.width || 800;
  const height = opts.height || 520;

  const container = document.getElementById('windows-container');
  const win = document.createElement('div');
  win.className = 'window';
  win.id = id;
  win.style.width = width + 'px';
  win.style.height = height + 'px';
  win.style.left = (80 + (WINDOW_ID % 8) * 30) + 'px';
  win.style.top = (40 + (WINDOW_ID % 8) * 24) + 'px';
  win.style.zIndex = ++Z_INDEX;

  win.innerHTML = `
    <div class="window-header">
      <span class="window-icon">${icon}</span>
      <span class="window-title">${title}</span>
      <div class="window-controls">
        <button class="window-btn-min" onclick="minimizeWindow('${id}')" title="Minimize">\u{2014}</button>
        <button class="window-btn-max" onclick="toggleMaximize('${id}')" title="Maximize">\u{25A1}</button>
        <button class="window-btn-close" onclick="closeWindow('${id}')" title="Close">\u{2715}</button>
      </div>
    </div>
    <div class="window-body" id="${id}-body"></div>
  `;

  win.addEventListener('mousedown', () => { win.style.zIndex = ++Z_INDEX; });
  container.appendChild(win);

  WINDOWS[id] = { el: win, title, icon, opts, state: 'normal' };
  updateTaskbar();

  makeDraggable(win, win.querySelector('.window-header'));
  makeResizable(win);

  return id;
}

function setWindowContent(id, html) {
  const body = document.getElementById(id + '-body');
  if (body) body.innerHTML = html;
}

function closeWindow(id) {
  const w = WINDOWS[id];
  if (w) {
    if (w.onclose) w.onclose();
    w.el.remove();
    delete WINDOWS[id];
    updateTaskbar();
  }
}

function closeAllWindows() {
  Object.keys(WINDOWS).forEach(id => closeWindow(id));
}

function minimizeWindow(id) {
  const w = WINDOWS[id];
  if (!w) return;
  if (w.state === 'minimized') {
    w.el.classList.remove('minimized');
    w.state = 'normal';
    w.el.style.zIndex = ++Z_INDEX;
  } else {
    w.el.classList.add('minimized');
    w.state = 'minimized';
  }
  updateTaskbar();
}

function toggleMaximize(id) {
  const w = WINDOWS[id];
  if (!w) return;
  if (w.el.classList.contains('maximized')) {
    w.el.classList.remove('maximized');
    if (w._savedRect) {
      w.el.style.left = w._savedRect.left + 'px';
      w.el.style.top = w._savedRect.top + 'px';
      w.el.style.width = w._savedRect.width + 'px';
      w.el.style.height = w._savedRect.height + 'px';
    }
  } else {
    w._savedRect = w.el.getBoundingClientRect();
    w.el.classList.add('maximized');
  }
}

function focusWindow(id) {
  const w = WINDOWS[id];
  if (!w) return;
  w.el.style.zIndex = ++Z_INDEX;
  if (w.state === 'minimized') minimizeWindow(id);
}

function updateTaskbar() {
  const container = document.getElementById('taskbar-apps');
  container.innerHTML = '';
  Object.keys(WINDOWS).forEach(id => {
    const w = WINDOWS[id];
    const el = document.createElement('div');
    el.className = 'taskbar-app' + (w.state === 'minimized' ? ' minimized' : '');
    el.innerHTML = `<span>${w.icon}</span><span>${w.title}</span>`;
    el.onclick = () => {
      if (w.state === 'minimized') minimizeWindow(id);
      else { focusWindow(id); minimizeWindow(id); }
    };
    container.appendChild(el);
  });
}

// ─── Drag ──────────────────────────────
function makeDraggable(el, handle) {
  let x, y, l, t, dragging = false;
  handle.addEventListener('mousedown', (e) => {
    if (e.target.closest('.window-controls')) return;
    if (el.classList.contains('maximized')) return;
    dragging = true;
    const rect = el.getBoundingClientRect();
    x = e.clientX - rect.left;
    y = e.clientY - rect.top;
    el.style.cursor = 'grabbing';
  });
  document.addEventListener('mousemove', (e) => {
    if (!dragging) return;
    l = e.clientX - x;
    t = e.clientY - y;
    l = Math.max(0, Math.min(l, window.innerWidth - 100));
    t = Math.max(0, Math.min(t, window.innerHeight - document.getElementById('taskbar').offsetHeight - 40));
    el.style.left = l + 'px';
    el.style.top = t + 'px';
  });
  document.addEventListener('mouseup', () => { dragging = false; el.style.cursor = ''; });
}

// ─── Resize ─────────────────────────────
function makeResizable(el) {
  const handles = ['n', 's', 'e', 'w', 'ne', 'nw', 'se', 'sw'];
  handles.forEach(dir => {
    const h = document.createElement('div');
    h.style.cssText = `position:absolute;z-index:100;`;
    if (dir.includes('n')) { h.style.top = '0'; h.style.height = '6px'; h.style.cursor = 'n-resize'; }
    if (dir.includes('s')) { h.style.bottom = '0'; h.style.height = '6px'; h.style.cursor = 's-resize'; }
    if (dir.includes('w')) { h.style.left = '0'; h.style.width = '6px'; h.style.cursor = 'w-resize'; }
    if (dir.includes('e')) { h.style.right = '0'; h.style.width = '6px'; h.style.cursor = 'e-resize'; }
    if (!dir.includes('n') && !dir.includes('s')) h.style.top = '6px'; h.style.bottom = '6px';
    if (!dir.includes('w') && !dir.includes('e')) h.style.left = '6px'; h.style.right = '6px';
    el.appendChild(h);
    let dragging = false, startX, startY, startW, startH, startL, startT;
    h.addEventListener('mousedown', (e) => {
      e.preventDefault(); e.stopPropagation();
      if (el.classList.contains('maximized')) return;
      dragging = true;
      const rect = el.getBoundingClientRect();
      startX = e.clientX; startY = e.clientY;
      startW = rect.width; startH = rect.height;
      startL = rect.left; startT = rect.top;
    });
    document.addEventListener('mousemove', (e) => {
      if (!dragging) return;
      const dx = e.clientX - startX, dy = e.clientY - startY;
      let nw = startW, nh = startH, nl = startL, nt = startT;
      if (dir.includes('e')) nw = Math.max(300, startW + dx);
      if (dir.includes('w')) { nw = Math.max(300, startW - dx); nl = startL + startW - nw; }
      if (dir.includes('s')) nh = Math.max(200, startH + dy);
      if (dir.includes('n')) { nh = Math.max(200, startH - dy); nt = startT + startH - nh; }
      el.style.width = nw + 'px'; el.style.height = nh + 'px';
      el.style.left = nl + 'px'; el.style.top = nt + 'px';
    });
    document.addEventListener('mouseup', () => { dragging = false; });
  });
}

// ═══════════════════════════════════════════════════════
// APP LAUNCHER
// ═══════════════════════════════════════════════════════

function launchApp(name) {
  const app = APP_REGISTRY.find(a => a.name === name);
  if (app && app.handler) {
    app.handler();
    return;
  }
  const exts = window.DESKTOP_APPS || [];
  const ext = exts.find(a => a.name === name);
  if (ext && ext.handler) { ext.handler(); return; }
  if (name === 'settings') { showSettings(); return; }
  showAppWindow(name);
}

function showAppWindow(name) {
  const apps = {
    'file-manager': { title: 'File Manager', icon: '\u{1F4C1}', url: 'apps/file-manager.html' },
    'terminal': { title: 'Terminal', icon: '\u{1F4BB}', url: 'apps/terminal.html' },
    'text-editor': { title: 'Text Editor', icon: '\u{1F4DD}', url: 'apps/editor.html' },
    'camera': { title: 'Camera', icon: '\u{1F4F7}', url: 'apps/camera.html' },
    'music-player': { title: 'Music Player', icon: '\u{1F3B5}', url: 'apps/music.html' },
    'video-player': { title: 'Video Player', icon: '\u{1F4FA}', url: 'apps/video.html' },
    'paint': { title: 'Paint', icon: '\u{1F5A8}\uFE0F', url: 'apps/paint.html' },
    'games': { title: 'Games', icon: '\u{1F9E9}', url: 'apps/games.html' },
    'files': { title: 'Files', icon: '\u{1F5C3}\uFE0F', url: 'apps/files.html' },
    'whiteboard': { title: 'Whiteboard', icon: '\u{1F579}\uFE0F', url: 'apps/whiteboard.html' },
    'notes': { title: 'Notes', icon: '\u{1F4CB}', url: 'apps/notes.html' },
    'calendar': { title: 'Calendar', icon: '\u{1F4C5}', url: 'apps/calendar.html' },
    'todos': { title: 'Todos', icon: '\u{1F4CE}', url: 'apps/todos.html' },
    'weather': { title: 'Weather', icon: '\u{1F3E0}', url: 'apps/weather.html' },
    'web-apps': { title: 'Web Apps', icon: '\u{1F4BB}', url: 'apps/webapps.html' },
    'remote-desktop': { title: 'Remote Desktop', icon: '\u{1F4F1}', url: 'apps/remote.html' },
  };
  const info = apps[name];
  if (!info) { notify('App not found: ' + name, 'error'); return; }
  const id = createWindow({ title: info.title, icon: info.icon, width: 900, height: 580 });
  setWindowContent(id, `<iframe class="app-iframe" src="${info.url}" sandbox="allow-scripts allow-forms allow-same-origin"></iframe>`);
}

// ═══════════════════════════════════════════════════════
// SETTINGS
// ═══════════════════════════════════════════════════════

function showSettings() {
  const id = createWindow({ title: 'Settings', icon: '\u{2699}\uFE0F', width: 700, height: 500 });
  setWindowContent(id, `
    <div style="padding:20px;max-width:600px">
      <h2 style="margin-bottom:20px;font-size:1.2em">Settings</h2>
      <div class="settings-group">
        <div class="settings-item">
          <div><strong>Wallpaper</strong><br><span class="text-muted text-sm">Change desktop background</span></div>
          <select id="set-wallpaper" onchange="changeWallpaper(this.value)" style="padding:6px 10px;border-radius:4px;background:var(--bg2);border:1px solid var(--border);color:var(--text)">
            <option value="default">Default</option>
            <option value="dark">Dark</option>
            <option value="gradient">Gradient</option>
            <option value="light">Light</option>
          </select>
        </div>
        <div class="settings-item">
          <div><strong>Theme</strong><br><span class="text-muted text-sm">UI color scheme</span></div>
          <select onchange="document.documentElement.style.setProperty('--primary', this.value)" style="padding:6px 10px;border-radius:4px;background:var(--bg2);border:1px solid var(--border);color:var(--text)">
            <option value="#7c6bff">Purple (Default)</option>
            <option value="#3498db">Blue</option>
            <option value="#2ecc71">Green</option>
            <option value="#e74c3c">Red</option>
            <option value="#f39c12">Orange</option>
          </select>
        </div>
        <div class="settings-item">
          <div><strong>User</strong><br><span class="text-muted text-sm">Signed in as ${CURRENT_USER.name}</span></div>
          <button onclick="lockScreen()" style="padding:6px 16px;border-radius:4px;background:var(--danger);color:white;border:none;cursor:pointer">Lock</button>
        </div>
        <div class="settings-item">
          <div><strong>About Web OS</strong><br><span class="text-muted text-sm">v1.0 Complete Edition</span></div>
          <div class="text-sm text-muted">12 AI Agents | 55+ Apps</div>
        </div>
      </div>
    </div>
  `);
}

function changeWallpaper(val) {
  const wp = document.getElementById('desktop-wallpaper');
  const gradients = {
    default: 'linear-gradient(135deg, #0a0a2a 0%, #1a0a3a 25%, #0a1a2a 50%, #0a0a30 75%, #1a0a20 100%)',
    dark: '#0a0a1a',
    gradient: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    light: 'linear-gradient(135deg, #e0e0f0 0%, #c0c0d0 100%)',
  };
  wp.style.background = gradients[val] || gradients.default;
  if (val === 'light') document.body.style.color = '#222';
  else document.body.style.color = '';
}

// ═══════════════════════════════════════════════════════
// CONTEXT MENU
// ═══════════════════════════════════════════════════════

function showContextMenu(e, items) {
  const menu = document.getElementById('desktop-context-menu');
  menu.innerHTML = '';
  menu.style.display = 'block';
  items.forEach((item, i) => {
    if (item.sep) {
      const sep = document.createElement('div');
      sep.className = 'context-menu-sep';
      menu.appendChild(sep);
    } else {
      const el = document.createElement('div');
      el.className = 'context-menu-item';
      el.innerHTML = `<span>${item.icon || ''} ${item.label}</span>${item.shortcut ? '<span class="shortcut">'+item.shortcut+'</span>' : ''}`;
      el.onclick = () => { item.action(); menu.style.display = 'none'; };
      menu.appendChild(el);
    }
  });
  const x = Math.min(e.clientX, window.innerWidth - 220);
  const y = Math.min(e.clientY, window.innerHeight - 250);
  menu.style.left = x + 'px';
  menu.style.top = y + 'px';
}

document.addEventListener('contextmenu', (e) => {
  if (!e.target.closest('#desktop-icons') && !e.target.closest('#desktop-wallpaper')) return;
  e.preventDefault();
  showContextMenu(e, [
    { label: 'Open Terminal', icon: '\u{1F4BB}', action: () => launchApp('terminal') },
    { label: 'File Manager', icon: '\u{1F4C1}', action: () => launchApp('file-manager') },
    { sep: true },
    { label: 'Change Wallpaper', icon: '\u{1F5BC}\uFE0F', action: () => showSettings() },
    { label: 'Refresh', icon: '\u{1F504}', action: () => {} },
    { sep: true },
    { label: 'Lock Screen', icon: '\u{1F512}', shortcut: 'Win+L', action: () => lockScreen() },
    { sep: true },
    { label: 'AI Assistant', icon: '\u{1F4AC}', action: () => launchApp('ai-chat') },
  ]);
});

// ═══════════════════════════════════════════════════════
// KEYBOARD SHORTCUTS
// ═══════════════════════════════════════════════════════

function handleKeyboardShortcuts(e) {
  if (e.ctrlKey && e.key === 't') { e.preventDefault(); launchApp('terminal'); }
  if (e.ctrlKey && e.key === 'n') { e.preventDefault(); launchApp('text-editor'); }
  if (e.ctrlKey && e.key === 'f') { e.preventDefault(); launchApp('file-manager'); }
  if (e.key === 'Escape') { closeStartMenu(); }
}

// ═══════════════════════════════════════════════════════
// SYSTEM TRAY
// ═══════════════════════════════════════════════════════

function updateClock() {
  const now = new Date();
  document.getElementById('tray-clock').textContent = now.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
}

function showShutdownMenu() {
  const overlay = document.createElement('div');
  overlay.className = 'power-overlay';
  overlay.id = 'power-overlay';
  overlay.innerHTML = `
    <div class="power-menu">
      <div class="power-btn" onclick="powerAction('shutdown')">
        <div class="pb-icon">\u{23FB}</div>
        <div class="pb-label">Shutdown</div>
      </div>
      <div class="power-btn" onclick="powerAction('restart')">
        <div class="pb-icon">\u{1F504}</div>
        <div class="pb-label">Restart</div>
      </div>
      <div class="power-btn" onclick="powerAction('sleep')">
        <div class="pb-icon">\u{1F31C}</div>
        <div class="pb-label">Sleep</div>
      </div>
      <div class="power-btn" onclick="powerAction('logout')">
        <div class="pb-icon">\u{1F6AA}</div>
        <div class="pb-label">Log Out</div>
      </div>
    </div>
  `;
  overlay.onclick = (e) => { if (e.target === overlay) overlay.remove(); };
  document.body.appendChild(overlay);
}

function powerAction(action) {
  document.getElementById('power-overlay').remove();
  if (action === 'logout') { lockScreen(); return; }
  notify(action.charAt(0).toUpperCase() + action.slice(1) + ' initiated', 'info');
}

// ═══════════════════════════════════════════════════════
// NOTIFICATIONS
// ═══════════════════════════════════════════════════════

function notify(message, type, title) {
  type = type || 'info';
  const container = document.getElementById('notification-container');
  const el = document.createElement('div');
  el.className = 'notification ' + type;
  const icons = { info: '\u{2139}\uFE0F', success: '\u{2705}', warning: '\u{26A0}\uFE0F', error: '\u{274C}' };
  el.innerHTML = `
    <div class="notification-title">${icons[type] || ''} ${title || type.charAt(0).toUpperCase() + type.slice(1)}</div>
    <div class="notification-msg">${message}</div>
    <div class="notification-time">${new Date().toLocaleTimeString()}</div>
  `;
  el.onclick = () => el.remove();
  container.appendChild(el);
  setTimeout(() => { if (el.parentNode) el.remove(); }, 5000);
}

// ═══════════════════════════════════════════════════════
// NETWORK HELPERS
// ═══════════════════════════════════════════════════════

function apiFetch(path, opts) {
  opts = opts || {};
  opts.headers = opts.headers || {};
  opts.headers['Authorization'] = 'Bearer ' + TOKEN;
  if (opts.body && typeof opts.body === 'object' && !(opts.body instanceof FormData)) {
    if (!opts.headers['Content-Type']) opts.headers['Content-Type'] = 'application/json';
    opts.body = JSON.stringify(opts.body);
  }
  return fetch(API + path, opts).then(r => r.json());
}

// ═══════════════════════════════════════════════════════
// BOOT: Always load Graphical Desktop Environment immediately
// ═══════════════════════════════════════════════════════

function bootOS() {
  try {
    initLogin();
  } catch(e) {}
  if (!TOKEN) {
    TOKEN = 'admin-token';
    localStorage.setItem('token', TOKEN);
  }
  showDesktop();
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', bootOS);
} else {
  bootOS();
}
