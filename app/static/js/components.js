/* UI component helpers */
const UI = (() => {
  const ICONS = {
    dashboard: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="4" rx="1"/><rect x="14" y="10" width="7" height="11" rx="1"/><rect x="3" y="13" width="7" height="8" rx="1"/></svg>',
    robot: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="5" y="8" width="14" height="12" rx="2"/><circle cx="9" cy="14" r="1.5"/><circle cx="15" cy="14" r="1.5"/><path d="M12 2v4M8 8V6a4 4 0 018 0v2"/></svg>',
    task: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11"/></svg>',
    settings: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 01-2.83 2.83l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"/></svg>',
    plus: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>',
    refresh: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 11-2.12-9.36L23 10"/></svg>',
    close: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>',
    check: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>',
    alert: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>',
    bell: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 01-3.46 0"/></svg>',
    webhook: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71"/></svg>',
    map: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"/><line x1="8" y1="2" x2="8" y2="18"/><line x1="16" y1="6" x2="16" y2="22"/></svg>',
    logout: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>',
    lock: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0110 0v4"/></svg>',
    user: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>',
    menu: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>',
  };

  function icon(name) { return ICONS[name] || ''; }

  function badge(status) {
    const s = (status || 'unknown').toLowerCase();
    return `<span class="badge ${s}"><span class="badge-dot"></span>${s}</span>`;
  }

  function severityBadge(severity) {
    const map = { error: 'failed', warning: 'pending', info: 'running' };
    const cls = map[severity] || 'running';
    return `<span class="badge ${cls}"><span class="badge-dot"></span>${severity}</span>`;
  }

  function toast(msg, type = 'info') {
    let c = document.getElementById('toast-container');
    if (!c) { c = document.createElement('div'); c.id = 'toast-container'; c.className = 'toast-container'; document.body.appendChild(c); }
    const t = document.createElement('div');
    t.className = `toast ${type}`;
    t.innerHTML = `${type === 'success' ? icon('check') : icon('alert')} <span>${msg}</span>`;
    c.appendChild(t);
    setTimeout(() => t.remove(), 4000);
  }

  function skeleton(rows = 4) {
    return Array.from({ length: rows }, () => '<div class="skeleton skeleton-line" style="width:' + (60 + Math.random() * 30) + '%"></div>').join('');
  }

  function emptyState(msg = 'Veri bulunamadı') {
    return `<div class="empty-state">${icon('alert')}<p>${msg}</p></div>`;
  }

  function pagination(page, totalPages, onClick) {
    if (totalPages <= 1) return '';
    let html = '<div class="pagination">';
    html += `<button class="page-btn" ${page <= 1 ? 'disabled' : ''} onclick="${onClick}(${page - 1})">‹</button>`;
    const start = Math.max(1, page - 2);
    const end = Math.min(totalPages, page + 2);
    for (let i = start; i <= end; i++) {
      html += `<button class="page-btn ${i === page ? 'active' : ''}" onclick="${onClick}(${i})">${i}</button>`;
    }
    html += `<span class="page-info">${page} / ${totalPages}</span>`;
    html += `<button class="page-btn" ${page >= totalPages ? 'disabled' : ''} onclick="${onClick}(${page + 1})">›</button>`;
    html += '</div>';
    return html;
  }

  function timeAgo(isoStr) {
    if (!isoStr) return '—';
    const d = new Date(isoStr);
    const now = new Date();
    const s = Math.floor((now - d) / 1000);
    if (s < 60) return `${s}s önce`;
    if (s < 3600) return `${Math.floor(s / 60)}dk önce`;
    if (s < 86400) return `${Math.floor(s / 3600)}sa önce`;
    return d.toLocaleDateString('tr-TR');
  }

  return { icon, badge, severityBadge, toast, skeleton, emptyState, pagination, timeAgo };
})();
