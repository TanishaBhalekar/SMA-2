import axios from 'axios';

let currentBaseUrl = 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: currentBaseUrl,
  timeout: 30000,
});

// Probe for live backend instance across localhost:8000, 127.0.0.1:8000, and relative proxy
export async function detectActiveBackend() {
  const candidates = [
    'http://localhost:8000',
    'http://127.0.0.1:8000',
    'http://localhost:8001',
    'http://127.0.0.1:8001',
    '',
  ];
  for (const base of candidates) {
    try {
      const url = base ? `${base}/api/health` : '/api/health';
      const res = await axios.get(url, { timeout: 1500 });
      if (res.data && (res.data.status === 'ok' || res.data.project)) {
        currentBaseUrl = base;
        apiClient.defaults.baseURL = currentBaseUrl;
        return currentBaseUrl;
      }
    } catch {
      // Continue checking next candidate
    }
  }
  return currentBaseUrl;
}

// Interceptor to auto-fallback between localhost, 127.0.0.1, and Vite proxy if connection fails
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const config = error.config;
    if (config && !config._retried) {
      config._retried = true;
      if (config.baseURL && config.baseURL.includes('localhost:8000')) {
        config.baseURL = 'http://127.0.0.1:8000';
        apiClient.defaults.baseURL = 'http://127.0.0.1:8000';
        return apiClient(config);
      } else if (config.baseURL && config.baseURL.includes('127.0.0.1:8000')) {
        config.baseURL = '';
        apiClient.defaults.baseURL = '';
        return apiClient(config);
      }
    }
    return Promise.reject(error);
  }
);

export const api = {
  // Stats
  getStats: () => apiClient.get('/api/stats'),
  getHealth: () => apiClient.get('/api/health'),

  // Sources
  listSources: () => apiClient.get('/api/sources'),
  uploadSource: (formData) =>
    apiClient.post('/api/sources/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  confirmMapping: (sourceId, mappings) =>
    apiClient.post(`/api/sources/${sourceId}/confirm-mapping`, { mappings }),
  getSourceStatus: (sourceId) => apiClient.get(`/api/sources/${sourceId}/status`),

  // Entities & Progressive Discovery
  searchEntity: (field, value) =>
    apiClient.get('/api/entities/search', { params: { field, value } }),
  getEntityDetails: (entityId) => apiClient.get(`/api/entities/${entityId}`),
};
