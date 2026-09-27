import axios from 'axios';
import { supabase } from '../lib/supabase';

// Default to relative URL ('') to use Vite's dev proxy, or fallback to VITE_API_URL / direct backend
let currentBaseUrl = import.meta.env.VITE_API_URL ?? '';

export const apiClient = axios.create({
  baseURL: currentBaseUrl,
  timeout: 30000,
});

// Request interceptor to automatically attach Supabase JWT Bearer token
apiClient.interceptors.request.use(
  async (config) => {
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (session?.access_token) {
        config.headers.Authorization = `Bearer ${session.access_token}`;
      }
    } catch (err) {
      console.warn('Failed to retrieve Supabase session for Authorization header:', err);
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Probe for live backend instance across relative proxy, 127.0.0.1:8000, and localhost:8000
export async function detectActiveBackend() {
  const candidates = [
    import.meta.env.VITE_API_URL,
    '',
    'http://127.0.0.1:8000',
    'http://localhost:8000',
  ].filter((c) => c !== undefined && c !== null);

  for (const base of candidates) {
    try {
      const url = base ? `${base}/api/health` : '/api/health';
      const res = await axios.get(url, { timeout: 2000 });
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

// Interceptor to auto-fallback between Vite proxy (''), 127.0.0.1:8000, and localhost:8000 if connection fails
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const config = error.config;
    if (config && !config._retried) {
      config._retried = true;
      if (config.baseURL === '' || !config.baseURL) {
        config.baseURL = 'http://127.0.0.1:8000';
        apiClient.defaults.baseURL = 'http://127.0.0.1:8000';
        return apiClient(config);
      } else if (config.baseURL.includes('127.0.0.1:8000')) {
        config.baseURL = 'http://localhost:8000';
        apiClient.defaults.baseURL = 'http://localhost:8000';
        return apiClient(config);
      } else if (config.baseURL.includes('localhost:8000')) {
        config.baseURL = '';
        apiClient.defaults.baseURL = '';
        return apiClient(config);
      }
    }
    return Promise.reject(error);
  }
);

export const api = {
  // Stats (supports optional workspaceId)
  getStats: (workspaceId = null) =>
    apiClient.get('/api/stats', { params: workspaceId ? { workspace_id: workspaceId } : {} }),
  getHealth: () => apiClient.get('/api/health'),

  // Workspaces / Ingestion Sessions
  listWorkspaces: () => apiClient.get('/api/workspaces'),
  getWorkspace: (id) => apiClient.get(`/api/workspaces/${id}`),
  getWorkspaceStats: (id) => apiClient.get(`/api/workspaces/${id}/stats`),
  resolveWorkspace: (id) => apiClient.post(`/api/workspaces/${id}/resolve`),
  createWorkspace: (data = {}) => apiClient.post('/api/workspaces', data),
  updateWorkspace: (id, data) => apiClient.patch(`/api/workspaces/${id}`, data),
  deleteWorkspace: (id) => apiClient.delete(`/api/workspaces/${id}`),
  purgeEmptyWorkspaces: () => apiClient.post('/api/workspaces/purge-empty'),

  // Sources (scoped by workspaceId)
  listSources: (workspaceId = null) =>
    apiClient.get('/api/sources', { params: workspaceId ? { workspace_id: workspaceId } : {} }),
  uploadSource: (formData, workspaceId = null) => {
    const headers = { 'Content-Type': 'multipart/form-data' };
    if (workspaceId) {
      headers['X-Workspace-Id'] = workspaceId;
    }
    return apiClient.post('/api/sources/upload', formData, { headers });
  },
  confirmMapping: (sourceId, mappings) =>
    apiClient.post(`/api/sources/${sourceId}/confirm-mapping`, { mappings }),
  getSourceStatus: (sourceId) => apiClient.get(`/api/sources/${sourceId}/status`),
  deleteSource: (sourceId) => apiClient.delete(`/api/sources/${sourceId}`),

  // Entities & Progressive Discovery (scoped by workspaceId)
  searchEntity: (field, value, workspaceId = null) =>
    apiClient.get('/api/entities/search', {
      params: {
        field,
        value,
        ...(workspaceId ? { workspace_id: workspaceId } : {}),
      },
    }),
  getEntityDetails: (entityId) => apiClient.get(`/api/entities/${entityId}`),
};

