// MicroDrama mobile API client.
// Base URL comes from EXPO_PUBLIC_API_URL (set in .env or in the shell
// before `npx expo start`). Default points at the local backend.
// Auth: JWT from POST /auth/login, stored via expo-secure-store, with
// AsyncStorage as fallback when SecureStore is unavailable (e.g. web).
import * as SecureStore from 'expo-secure-store';
import AsyncStorage from '@react-native-async-storage/async-storage';

export const API_BASE_URL =
  process.env.EXPO_PUBLIC_API_URL || 'http://localhost:8002/api/v1';

const TOKEN_KEY = 'microdrama_access_token';

async function secureAvailable(): Promise<boolean> {
  try {
    return await SecureStore.isAvailableAsync();
  } catch {
    return false;
  }
}

export async function saveToken(token: string): Promise<void> {
  if (await secureAvailable()) {
    await SecureStore.setItemAsync(TOKEN_KEY, token);
  } else {
    await AsyncStorage.setItem(TOKEN_KEY, token);
  }
}

export async function getToken(): Promise<string | null> {
  if (await secureAvailable()) {
    return SecureStore.getItemAsync(TOKEN_KEY);
  }
  return AsyncStorage.getItem(TOKEN_KEY);
}

export async function clearToken(): Promise<void> {
  if (await secureAvailable()) {
    await SecureStore.deleteItemAsync(TOKEN_KEY);
  } else {
    await AsyncStorage.removeItem(TOKEN_KEY);
  }
}

export interface ApiError extends Error {
  status?: number;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = await getToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(init.headers as Record<string, string> | undefined),
  };
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(`${API_BASE_URL}${path}`, { ...init, headers });
  if (!res.ok) {
    const err = new Error(`API ${res.status}: ${res.statusText}`) as ApiError;
    err.status = res.status;
    let detail = '';
    try {
      const body = await res.json();
      detail = typeof body?.detail === 'string' ? body.detail : '';
    } catch {
      // ignore non-JSON error bodies
    }
    if (detail) err.message = detail;
    throw err;
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const get = <T,>(path: string) => request<T>(path);
export const post = <T,>(path: string, body?: unknown) =>
  request<T>(path, { method: 'POST', body: body === undefined ? undefined : JSON.stringify(body) });

// --- Types (mirror backend shapes used by the web frontend) ---

export interface Project {
  id: string;
  title: string;
  description?: string | null;
  genre?: string | null;
  status: string;
  total_episodes: number;
  created_at?: string;
  updated_at?: string;
}

export interface SeriesBible {
  id: string;
  premise?: string | null;
  main_plot?: string | null;
}

export interface Character {
  id: string;
  name: string;
  role?: string | null;
}

export interface Episode {
  id: string;
  episode_number: number;
  title?: string | null;
  status?: string | null;
}

export interface AutoGenerateStep {
  id: string;
  job_id: string;
  step: string;
  step_order: number;
  status: 'pending' | 'running' | 'completed' | 'failed';
  error_message: string | null;
}

export interface AutoGenerateJob {
  id: string;
  project_id: string;
  title: string;
  genre: string | null;
  total_episodes: number;
  status: 'pending' | 'running' | 'completed' | 'failed';
  error_message: string | null;
  steps: AutoGenerateStep[];
}

// --- Auth ---

export async function login(email: string, password: string): Promise<string> {
  // Same contract as the web frontend: form-urlencoded username/password.
  const form = new URLSearchParams();
  form.append('username', email);
  form.append('password', password);
  const res = await fetch(`${API_BASE_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: form.toString(),
  });
  if (!res.ok) {
    const err = new Error('Login failed') as ApiError;
    err.status = res.status;
    try {
      const body = await res.json();
      if (typeof body?.detail === 'string') err.message = body.detail;
    } catch {
      // ignore
    }
    throw err;
  }
  const data = await res.json();
  const token = data.access_token as string | undefined;
  if (!token) throw new Error('Login succeeded but no access_token was returned');
  await saveToken(token);
  return token;
}

// --- Projects / Auto-Generate ---

export const listProjects = () =>
  get<{ projects: Project[] }>('/projects?page_size=100');

export const getProject = (id: string) => get<Project>(`/projects/${id}`);

export const getSeriesBible = (projectId: string) =>
  get<SeriesBible>(`/projects/${projectId}/series-bible`);

export const listCharacters = (projectId: string) =>
  get<Character[]>(`/projects/${projectId}/characters`);

export const listEpisodes = (projectId: string) =>
  get<Episode[]>(`/projects/${projectId}/episodes`);

export const createAutoGenerate = (
  projectId: string,
  data: { title: string; genre?: string; total_episodes?: number; premise?: string },
) => post<AutoGenerateJob>(`/projects/${projectId}/auto-generate`, data);

export const getAutoGenerateJob = (projectId: string, jobId: string) =>
  get<AutoGenerateJob>(`/projects/${projectId}/auto-generate/${jobId}`);
