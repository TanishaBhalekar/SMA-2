import axios from 'axios';

let currentBaseUrl = 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: currentBaseUrl,
  timeout: 30000,
});

// Probe for live backend instance across 8000 and 8001
export async function detectActiveBackend() {
  for (const port of [8000, 8001]) {
    try {
      const res = await axios.get(`http://localhost:${port}/api/health`, { timeout: 1500 });
      if (res.data && (res.data.status === 'ok' || res.data.project)) {
        currentBaseUrl = `http://localhost:${port}`;
        apiClient.defaults.baseURL = currentBaseUrl;
        return currentBaseUrl;
      }
    } catch {
      // Continue checking next candidate port
    }
  }
  return currentBaseUrl;
}

// Interceptor to auto-fallback between port 8000 and 8001 if port 8000 encounters conflict
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const config = error.config;
    if (config && !config._retried && config.baseURL && config.baseURL.includes(':8000')) {
      config._retried = true;
      config.baseURL = 'http://localhost:8001';
      apiClient.defaults.baseURL = 'http://localhost:8001';
      return apiClient(config);
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
