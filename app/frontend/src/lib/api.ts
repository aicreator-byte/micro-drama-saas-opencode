import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: false,
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('access_token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor to handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      if (typeof window !== 'undefined') {
        localStorage.removeItem('access_token');
        localStorage.removeItem('user');
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authApi = {
  register: (data: { email: string; password: string; full_name?: string }) =>
    api.post('/auth/register', data),
  
  login: (email: string, password: string) => {
    const formData = new URLSearchParams();
    formData.append('username', email);
    formData.append('password', password);
    return api.post('/auth/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    });
  },
  
  logout: () =>
    api.post('/auth/logout'),

  changePassword: (data: { current_password: string; new_password: string }) =>
    api.post('/auth/change-password', data),

  getMe: () =>
    api.get('/auth/me'),
};

// Projects API
export const projectsApi = {
  list: (params?: { page?: number; page_size?: number; status?: string; search?: string }) =>
    api.get('/projects', { params }),
  
  create: (data: { title: string; description?: string; genre?: string; themes?: string[]; total_episodes?: number }) =>
    api.post('/projects', data),
  
  get: (id: string) =>
    api.get(`/projects/${id}`),
  
  update: (id: string, data: Partial<{ title: string; description?: string; genre?: string; themes?: string[]; status?: string; total_episodes?: number; google_account_id?: string | null }>) =>
    api.patch(`/projects/${id}`, data),
  
  delete: (id: string) =>
    api.delete(`/projects/${id}`),
};

// Series Bible API
export const seriesBibleApi = {
  create: (projectId: string, data: { premise?: string; main_plot?: string; subplots?: string[]; character_relationships?: string; world_settings?: string; tone_and_visual_style?: string; ending_direction?: string; episode_structure?: string }) =>
    api.post(`/projects/${projectId}/series-bible`, data),
  
  get: (projectId: string) =>
    api.get(`/projects/${projectId}/series-bible`),
  
  update: (projectId: string, data: Partial<{ premise?: string; main_plot?: string; subplots?: string[]; character_relationships?: string; world_settings?: string; tone_and_visual_style?: string; ending_direction?: string; episode_structure?: string }>) =>
    api.patch(`/projects/${projectId}/series-bible`, data),
  
  delete: (projectId: string) =>
    api.delete(`/projects/${projectId}/series-bible`),
};

// Characters API
export const charactersApi = {
  list: (projectId: string) =>
    api.get(`/projects/${projectId}/characters`),
  
  create: (projectId: string, data: any) =>
    api.post(`/projects/${projectId}/characters`, data),
  
  get: (projectId: string, id: string) =>
    api.get(`/projects/${projectId}/characters/${id}`),
  
  update: (projectId: string, id: string, data: any) =>
    api.patch(`/projects/${projectId}/characters/${id}`, data),
  
  delete: (projectId: string, id: string) =>
    api.delete(`/projects/${projectId}/characters/${id}`),
};

// Locations API
export const locationsApi = {
  list: (projectId: string) =>
    api.get(`/projects/${projectId}/locations`),
  
  create: (projectId: string, data: any) =>
    api.post(`/projects/${projectId}/locations`, data),
  
  get: (projectId: string, id: string) =>
    api.get(`/projects/${projectId}/locations/${id}`),
  
  update: (projectId: string, id: string, data: any) =>
    api.patch(`/projects/${projectId}/locations/${id}`, data),
  
  delete: (projectId: string, id: string) =>
    api.delete(`/projects/${projectId}/locations/${id}`),
};

// Episodes API
export const episodesApi = {
  list: (projectId: string) =>
    api.get(`/projects/${projectId}/episodes`),
  
  create: (projectId: string, data: { episode_number: number; title?: string; summary?: string }) =>
    api.post(`/projects/${projectId}/episodes`, data),
  
  get: (projectId: string, id: string) =>
    api.get(`/projects/${projectId}/episodes/${id}`),
  
  update: (projectId: string, id: string, data: any) =>
    api.patch(`/projects/${projectId}/episodes/${id}`, data),
  
  delete: (projectId: string, id: string) =>
    api.delete(`/projects/${projectId}/episodes/${id}`),
  
  // Scenes
  listScenes: (projectId: string, episodeId: string) =>
    api.get(`/projects/${projectId}/episodes/${episodeId}/scenes`),
  
  createScene: (projectId: string, episodeId: string, data: any) =>
    api.post(`/projects/${projectId}/episodes/${episodeId}/scenes`, data),
  
  getScene: (projectId: string, episodeId: string, sceneId: string) =>
    api.get(`/projects/${projectId}/episodes/${episodeId}/scenes/${sceneId}`),
  
  updateScene: (projectId: string, episodeId: string, sceneId: string, data: any) =>
    api.patch(`/projects/${projectId}/episodes/${episodeId}/scenes/${sceneId}`, data),
  
  deleteScene: (projectId: string, episodeId: string, sceneId: string) =>
    api.delete(`/projects/${projectId}/episodes/${episodeId}/scenes/${sceneId}`),
  
  // Shots
  listShots: (projectId: string, episodeId: string, sceneId: string) =>
    api.get(`/projects/${projectId}/episodes/${episodeId}/scenes/${sceneId}/shots`),
  
  createShot: (projectId: string, episodeId: string, sceneId: string, data: any) =>
    api.post(`/projects/${projectId}/episodes/${episodeId}/scenes/${sceneId}/shots`, data),
  
  getShot: (projectId: string, episodeId: string, sceneId: string, shotId: string) =>
    api.get(`/projects/${projectId}/episodes/${episodeId}/scenes/${sceneId}/shots/${shotId}`),
  
  updateShot: (projectId: string, episodeId: string, sceneId: string, shotId: string, data: any) =>
    api.patch(`/projects/${projectId}/episodes/${episodeId}/scenes/${sceneId}/shots/${shotId}`, data),
  
  deleteShot: (projectId: string, episodeId: string, sceneId: string, shotId: string) =>
    api.delete(`/projects/${projectId}/episodes/${episodeId}/scenes/${sceneId}/shots/${shotId}`),
};

// Prompts API
export const promptsApi = {
  list: (projectId: string, params?: { prompt_type?: string; episode_id?: string; scene_id?: string; shot_id?: string; character_id?: string; location_id?: string; status?: string }) =>
    api.get(`/projects/${projectId}/prompts`, { params }),
  
  create: (projectId: string, data: any) =>
    api.post(`/projects/${projectId}/prompts`, data),
  
  get: (projectId: string, id: string) =>
    api.get(`/projects/${projectId}/prompts/${id}`),
  
  update: (projectId: string, id: string, data: any) =>
    api.patch(`/projects/${projectId}/prompts/${id}`, data),
  
  delete: (projectId: string, id: string) =>
    api.delete(`/projects/${projectId}/prompts/${id}`),
  
  use: (projectId: string, id: string) =>
    api.post(`/projects/${projectId}/prompts/${id}/use`),
};

// Google Accounts API
export const googleAccountsApi = {
  list: () =>
    api.get('/google-accounts'),
  
  connect: (data: { email: string; session_data: string; expires_at?: string }) =>
    api.post('/google-accounts', data),
  
  get: (id: string) =>
    api.get(`/google-accounts/${id}`),
  
  update: (id: string, data: any) =>
    api.patch(`/google-accounts/${id}`, data),
  
  disconnect: (id: string) =>
    api.delete(`/google-accounts/${id}`),
  
  verify: (id: string) =>
    api.post(`/google-accounts/${id}/verify`),
  
  // OAuth endpoints
  authorize: () =>
    api.get('/google-accounts/oauth/authorize'),
  
  refresh: (id: string) =>
    api.post(`/google-accounts/${id}/refresh`),
};

// Flow Bridge API
export const flowBridgeApi = {
  listTasks: (projectId: string, params?: { status?: string; episode_id?: string }) =>
    api.get(`/projects/${projectId}/tasks`, { params }),
  
  createTask: (projectId: string, data: any) =>
    api.post(`/projects/${projectId}/tasks`, data),
  
  getTask: (projectId: string, id: string) =>
    api.get(`/projects/${projectId}/tasks/${id}`),
  
  updateTask: (projectId: string, id: string, data: any) =>
    api.patch(`/projects/${projectId}/tasks/${id}`, data),
  
  deleteTask: (projectId: string, id: string) =>
    api.delete(`/projects/${projectId}/tasks/${id}`),
  
  listAssets: (projectId: string, taskId: string) =>
    api.get(`/projects/${projectId}/tasks/${taskId}/assets`),
  
  createAsset: (projectId: string, taskId: string, data: any) =>
    api.post(`/projects/${projectId}/tasks/${taskId}/assets`, data),
  
  listProjectAssets: (projectId: string, params?: { asset_type?: string; episode_id?: string }) =>
    api.get(`/projects/${projectId}/assets`, { params }),
};

// Audit Logs API
export const auditLogsApi = {
  list: (params?: { action?: string; resource_type?: string; resource_id?: string; start_date?: string; end_date?: string; page?: number; page_size?: number }) =>
    api.get('/audit-logs', { params }),
  
  get: (id: string) =>
    api.get(`/audit-logs/${id}`),
};

// Export API
export const exportApi = {
  create: (projectId: string, data: { export_type: string; format?: string; project_id?: string; episode_id?: string; include_related?: boolean }) =>
    api.post(`/projects/${projectId}/export`, data),
  
  list: (projectId: string) =>
    api.get(`/projects/${projectId}/export/history`),
  
  quickExportProject: (projectId: string, format?: string) =>
    api.get(`/projects/${projectId}/export/project`, { params: { format } }),
  
  quickExportEpisode: (projectId: string, episodeId: string, format?: string) =>
    api.get(`/projects/${projectId}/export/episode/${episodeId}`, { params: { format } }),
  
  quickExportPrompts: (projectId: string, format?: string) =>
    api.get(`/projects/${projectId}/export/prompts`, { params: { format } }),
  
  download: (projectId: string, exportId: string) =>
    api.get(`/projects/${projectId}/export/${exportId}/download`, { responseType: 'blob' }),
};

// Story Engine API
export const storyEngineApi = {
  list: (projectId: string) =>
    api.get(`/projects/${projectId}/story-engine/tasks`),

  create: (projectId: string, data: { task_type: string; series_bible_id: string; parameters?: Record<string, unknown>; context?: string }) =>
    api.post(`/projects/${projectId}/story-engine/tasks`, data),

  get: (projectId: string, taskId: string) =>
    api.get(`/projects/${projectId}/story-engine/tasks/${taskId}`),

  execute: (projectId: string, taskId: string) =>
    api.post(`/projects/${projectId}/story-engine/tasks/${taskId}/execute`),

  apply: (projectId: string, taskId: string) =>
    api.post(`/projects/${projectId}/story-engine/tasks/${taskId}/apply`),

  delete: (projectId: string, taskId: string) =>
    api.delete(`/projects/${projectId}/story-engine/tasks/${taskId}`),
};

// Scene Engine API
export const sceneEngineApi = {
  list: (projectId: string) =>
    api.get(`/projects/${projectId}/scene-engine/tasks`),

  create: (projectId: string, data: { task_type: string; episode_id: string; scene_id?: string; parameters?: Record<string, unknown>; context?: string }) =>
    api.post(`/projects/${projectId}/scene-engine/tasks`, data),

  get: (projectId: string, taskId: string) =>
    api.get(`/projects/${projectId}/scene-engine/tasks/${taskId}`),

  execute: (projectId: string, taskId: string) =>
    api.post(`/projects/${projectId}/scene-engine/tasks/${taskId}/execute`),

  apply: (projectId: string, taskId: string) =>
    api.post(`/projects/${projectId}/scene-engine/tasks/${taskId}/apply`),

  delete: (projectId: string, taskId: string) =>
    api.delete(`/projects/${projectId}/scene-engine/tasks/${taskId}`),
};

// Dialogues API (per scene)
export const dialoguesApi = {
  list: (projectId: string, episodeId: string, sceneId: string) =>
    api.get(`/projects/${projectId}/episodes/${episodeId}/scenes/${sceneId}/dialogues`),
};

// Episode revisions API
export const episodeRevisionsApi = {
  list: (projectId: string, episodeId: string) =>
    api.get(`/projects/${projectId}/episodes/${episodeId}/revisions`),

  create: (projectId: string, episodeId: string, data: { change_notes?: string }) =>
    api.post(`/projects/${projectId}/episodes/${episodeId}/revisions`, data),
};

// Settings API
export const settingsApi = {
  get: () =>
    api.get('/settings'),
  
  update: (data: {
    ai_providers?: Array<{ id: string; provider: string; model: string; key_env: string; enabled: boolean; priority: number }>;
    google_oauth_client_id?: string;
    google_oauth_client_secret?: string;
  }) =>
    api.patch('/settings', data),
};

export default api;