/* API client module for RCS-2000 Middleware dashboard */

const API = (() => {
  let apiKey = localStorage.getItem('rcs_api_key') || '';
  const BASE = '/api/v1';

  function setApiKey(key) {
    apiKey = key;
    localStorage.setItem('rcs_api_key', key);
  }
  function getApiKey() { return apiKey; }
  function clearApiKey() { apiKey = ''; localStorage.removeItem('rcs_api_key'); }

  async function request(method, path, body = null) {
    const opts = {
      method,
      headers: { 'Content-Type': 'application/json', 'X-API-Key': apiKey },
    };
    if (body) opts.body = JSON.stringify(body);
    const res = await fetch(`${BASE}${path}`, opts);
    const data = await res.json();
    if (!res.ok && !data.success) {
      const msg = data.error?.message || data.detail || `HTTP ${res.status}`;
      throw new Error(msg);
    }
    return data;
  }

  return {
    setApiKey,
    getApiKey,
    clearApiKey,
    getStats: () => request('GET', '/system/stats'),
    getRobots: () => request('GET', '/robots/status'),
    getTaskHistory: (page = 1, pageSize = 15, status = '') => {
      let url = `/tasks/history?page=${page}&pageSize=${pageSize}`;
      if (status) url += `&status=${status}`;
      return request('GET', url);
    },
    createTask: (payload) => request('POST', '/tasks/create', payload),
    getWebhookLogs: (page = 1, pageSize = 30, taskCode = '') => {
      let url = `/webhook/logs?page=${page}&pageSize=${pageSize}`;
      if (taskCode) url += `&taskCode=${taskCode}`;
      return request('GET', url);
    },
    getAlerts: (limit = 30) => request('GET', `/alerts/recent?limit=${limit}`),
    healthReady: async () => {
      try {
        const res = await fetch('/health/ready');
        return await res.json();
      } catch { return { db: 'error', redis: 'error' }; }
    },
    healthLive: async () => {
      try {
        const res = await fetch('/health/live');
        return res.ok;
      } catch { return false; }
    },
    validateApiKey: async (key) => {
      try {
        const res = await fetch(`${BASE}/system/stats`, {
          headers: { 'X-API-Key': key, 'Content-Type': 'application/json' },
        });
        return res.ok;
      } catch { return false; }
    },
    getSystemConfig: () => request('GET', '/system/config'),
    updateSystemConfig: (payload) => request('PUT', '/system/config', payload),
  };
})();
