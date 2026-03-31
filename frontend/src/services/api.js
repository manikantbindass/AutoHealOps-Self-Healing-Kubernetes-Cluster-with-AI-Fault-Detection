import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_URL,
  timeout: 10000,
  headers: { 'Content-Type': 'application/json' },
});

// Attach JWT token if available
api.interceptors.request.use(config => {
  const token = localStorage.getItem('token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export const apiService = {
  // Metrics
  getMetrics: () => api.get('/metrics').then(r => r.data),
  getHealthScore: () => api.get('/metrics/health-score').then(r => r.data),
  getMetricHistory: (metric, limit = 100) =>
    api.get(`/metrics/history?metric=${metric}&limit=${limit}`).then(r => r.data),

  // Alerts
  getAlerts: (status) =>
    api.get(`/alerts${status ? `?status=${status}` : ''}`).then(r => r.data),
  acknowledgeAlert: (id) => api.post(`/alerts/acknowledge/${id}`).then(r => r.data),

  // Healing
  triggerHeal: (body) => api.post('/heal', body).then(r => r.data),
  getHealingLogs: () => api.get('/heal/logs').then(r => r.data),

  // Auth
  login: (username, password) =>
    api.post('/auth/login', { username, password }).then(r => r.data),
};
