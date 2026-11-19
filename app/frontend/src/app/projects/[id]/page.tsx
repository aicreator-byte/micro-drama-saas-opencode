'use client';

import { useEffect, useState, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { 
  ArrowLeft, Film, Users, MapPin, FileText, 
  Clapperboard, Settings, Plus, Edit, Trash2,
  ChevronRight, Loader2, Save, X, 
  Search, Filter, MoreVertical, Download,
  Eye, Copy, RefreshCw, AlertCircle,
  CheckCircle, XCircle, Clock, Play,
  Image, Zap, Layers, Type, Palette,
  BookOpen, Target, Sparkles
} from 'lucide-react';
import { api, exportApi, flowBridgeApi, storyEngineApi, sceneEngineApi, autoGenerateApi } from '@/lib/api';
import { useAuthStore } from '@/store';
import { formatDate } from '@/lib/utils';

interface Project {
  id: string;
  title: string;
  description: string | null;
  genre: string | null;
  themes: string | null;
  status: string;
  total_episodes: number;
  created_at: string;
  updated_at: string;
  google_account_id: string | null;
}

interface SeriesBible {
  id: string;
  project_id: string;
  premise: string | null;
  main_plot: string | null;
  subplots: string | null;
  character_relationships: string | null;
  world_settings: string | null;
  tone_and_visual_style: string | null;
  ending_direction: string | null;
  episode_structure: string | null;
  created_at: string;
  updated_at: string;
}

interface Character {
  id: string;
  project_id: string;
  name: string;
  role: string | null;
  order_index: number;
  age: string | null;
  gender: string | null;
  ethnicity: string | null;
  height: string | null;
  build: string | null;
  hair_color: string | null;
  hair_style: string | null;
  eye_color: string | null;
  skin_tone: string | null;
  distinguishing_features: string | null;
  personality_traits: string | null;
  background: string | null;
  motivations: string | null;
  fears: string | null;
  quirks: string | null;
  voice_pattern: string | null;
  physical_traits: string | null;
  skills: string | null;
  costume_style: string | null;
  signature_items: string | null;
  color_palette: string | null;
  reference_images: string | null;
  consistency_instructions: string | null;
  created_at: string;
  updated_at: string;
}

interface Location {
  id: string;
  project_id: string;
  name: string;
  type: string | null;
  order_index: number;
  description: string | null;
  environment_details: string | null;
  reference_images: string | null;
  visual_style_notes: string | null;
  lighting: string | null;
  atmosphere: string | null;
  time_of_day: string | null;
  weather: string | null;
  consistency_instructions: string | null;
  created_at: string;
  updated_at: string;
}

interface Episode {
  id: string;
  project_id: string;
  episode_number: number;
  title: string | null;
  summary: string | null;
  status: string;
  order_index: number;
  created_at: string;
  updated_at: string;
}

interface Scene {
  id: string;
  episode_id: string;
  scene_number: number;
  title: string | null;
  description: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

interface Prompt {
  id: string;
  project_id: string;
  name: string;
  category: string | null;
  template: string;
  variables: string | null;
  description: string | null;
  version: number;
  is_active: boolean;
  times_used: number;
  created_at: string;
  updated_at: string;
}

interface GoogleAccount {
  id: string;
  user_id: string;
  email: string;
  display_name: string | null;
  status: string;
  last_verified_at: string | null;
  error_message: string | null;
  profile_picture: string | null;
  projects_assigned: number;
  created_at: string;
  updated_at: string;
}

interface FlowBridgeTask {
  id: string;
  project_id: string;
  episode_id: string | null;
  scene_id: string | null;
  shot_id: string | null;
  google_account_id: string | null;
  title: string;
  description: string | null;
  task_type: string | null;
  status: string;
  input_prompts: string | null;
  input_references: string | null;
  input_parameters: string | null;
  output_assets: string | null;
  generation_log: string | null;
  error_message: string | null;
  priority: number;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  completed_at: string | null;
}

interface FlowBridgeAsset {
  id: string;
  task_id: string;
  project_id: string;
  asset_type: string;
  title: string | null;
  description: string | null;
  file_path: string | null;
  file_url: string | null;
  file_size: number | null;
  mime_type: string | null;
  checksum: string | null;
  source: string | null;
  source_metadata: string | null;
  episode_id: string | null;
  scene_id: string | null;
  shot_id: string | null;
  character_id: string | null;
  location_id: string | null;
  created_at: string;
  updated_at: string;
}

interface StoryEngineTask {
  id: string;
  project_id: string;
  series_bible_id: string;
  episode_id: string | null;
  task_type: string;
  status: string;
  input_parameters: string | null;
  context: string | null;
  output: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

interface AuditLog {
  id: string;
  user_id: string;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  ip_address: string | null;
  user_agent: string | null;
  request_id: string | null;
  old_values: string | null;
  new_values: string | null;
  success: boolean;
  error_message: string | null;
  created_at: string;
}

interface AutoGenerateStep {
  id: string;
  job_id: string;
  step: string;
  step_order: number;
  status: 'pending' | 'running' | 'completed' | 'failed';
  error_message: string | null;
  result?: Record<string, unknown> | null;
}

interface AutoGenerateJob {
  id: string;
  project_id: string;
  title: string;
  genre: string | null;
  total_episodes: number;
  premise: string | null;
  status: 'pending' | 'running' | 'completed' | 'failed';
  error_message: string | null;
  steps: AutoGenerateStep[];
}

type Tab = 'overview' | 'series-bible' | 'characters' | 'locations' | 'episodes' | 'prompts' | 'google-accounts' | 'flow-bridge' | 'settings' | 'export' | 'audit-logs';

const tabs: { id: Tab; label: string; icon: React.ReactNode }[] = [
  { id: 'overview', label: 'Overview', icon: <Film className="w-5 h-5" /> },
  { id: 'series-bible', label: 'Story Engine', icon: <BookOpen className="w-5 h-5" /> },
  { id: 'characters', label: 'Characters', icon: <Users className="w-5 h-5" /> },
  { id: 'locations', label: 'Locations', icon: <MapPin className="w-5 h-5" /> },
  { id: 'episodes', label: 'Episodes', icon: <Clapperboard className="w-5 h-5" /> },
  { id: 'prompts', label: 'Prompts', icon: <Type className="w-5 h-5" /> },
  { id: 'google-accounts', label: 'Google Accounts', icon: <Layers className="w-5 h-5" /> },
  { id: 'flow-bridge', label: 'Flow Bridge', icon: <Zap className="w-5 h-5" /> },
  { id: 'export', label: 'Export', icon: <Download className="w-5 h-5" /> },
  { id: 'audit-logs', label: 'Audit Logs', icon: <Target className="w-5 h-5" /> },
  { id: 'settings', label: 'Settings', icon: <Settings className="w-5 h-5" /> },
];

export default function ProjectPage() {
  const params = useParams();
  const router = useRouter();
  const { isAuthenticated } = useAuthStore();
  const projectId = params.id as string;
  
  const [project, setProject] = useState<Project | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<Tab>('overview');
  const [showEditModal, setShowEditModal] = useState(false);
  const [editTitle, setEditTitle] = useState('');
  const [editDescription, setEditDescription] = useState('');
  const [editGenre, setEditGenre] = useState('');
  const [isSaving, setIsSaving] = useState(false);

  // Auto-Generate (spec §6) — one job, 5 steps.
  // NOTE: Fase 1 backend runs create + retry synchronously in the request,
  // so there is no job id to poll while a run is in flight. The modal shows
  // an indeterminate "generating" state during the request, then the final
  // per-step status + Retry buttons. GET is used by Refresh for a past job.
  const AUTO_GENERATE_STEP_LABELS: Record<string, string> = {
    series_bible: 'Series Bible',
    characters: 'Characters',
    locations: 'Locations',
    episodes: 'Episodes',
    prompts: 'Prompts',
  };
  const AUTO_GENERATE_STEP_ORDER = ['series_bible', 'characters', 'locations', 'episodes', 'prompts'];
  const [showAutoGenerateModal, setShowAutoGenerateModal] = useState(false);
  const [autoGenForm, setAutoGenForm] = useState({
    title: '',
    genre: '',
    total_episodes: '30',
    premise: '',
  });
  const [autoGenJob, setAutoGenJob] = useState<AutoGenerateJob | null>(null);
  const [autoGenSubmitting, setAutoGenSubmitting] = useState(false);
  const [autoGenRetrying, setAutoGenRetrying] = useState<string | null>(null);
  const [autoGenError, setAutoGenError] = useState('');

  // Series Bible
  const [seriesBible, setSeriesBible] = useState<SeriesBible | null>(null);
  const [seriesBibleLoading, setSeriesBibleLoading] = useState(false);
  const [showSeriesBibleModal, setShowSeriesBibleModal] = useState(false);
  const [seriesBibleForm, setSeriesBibleForm] = useState({
    premise: '',
    main_plot: '',
    subplots: '',
    character_relationships: '',
    world_settings: '',
    tone_and_visual_style: '',
    ending_direction: '',
    episode_structure: '',
  });
  const [seriesBibleSaving, setSeriesBibleSaving] = useState(false);

  // Story Engine / Scene Engine tasks (audit F-13: previously API-only)
  interface EngineTask {
    id: string;
    task_type: string;
    status: string;
    input_parameters?: Record<string, unknown> | null;
    output?: Record<string, unknown> | null;
    error_message?: string | null;
    created_at: string;
    completed_at?: string | null;
  }
  const [storyTasks, setStoryTasks] = useState<EngineTask[]>([]);
  const [sceneTasks, setSceneTasks] = useState<EngineTask[]>([]);
  const [engineLoading, setEngineLoading] = useState(false);
  const [engineMessage, setEngineMessage] = useState('');
  const [storyType, setStoryType] = useState('generate_outline');
  const [storyContext, setStoryContext] = useState('');
  const [storyEpisodes, setStoryEpisodes] = useState('20');
  const [storyEpisodeNumber, setStoryEpisodeNumber] = useState('1');
  const [sceneType, setSceneType] = useState('breakdown_episode');
  const [sceneEpisodeId, setSceneEpisodeId] = useState('');
  const [sceneSceneId, setSceneSceneId] = useState('');
  const [sceneEpisodeScenes, setSceneEpisodeScenes] = useState<Scene[]>([]);
  const [sceneContext, setSceneContext] = useState('');
  const [expandedTask, setExpandedTask] = useState<string | null>(null);

  // Characters
  const [characters, setCharacters] = useState<Character[]>([]);
  const [charactersLoading, setCharactersLoading] = useState(false);
  const [showCharacterModal, setShowCharacterModal] = useState(false);
  const [editingCharacter, setEditingCharacter] = useState<Character | null>(null);
  const [characterForm, setCharacterForm] = useState<Partial<Character>>({
    name: '',
    role: 'supporting',
    age: '',
    gender: '',
    ethnicity: '',
    height: '',
    build: '',
    hair_color: '',
    hair_style: '',
    eye_color: '',
    skin_tone: '',
    distinguishing_features: '',
    personality_traits: '',
    background: '',
    motivations: '',
    fears: '',
    quirks: '',
    voice_pattern: '',
    physical_traits: '',
    skills: '',
    costume_style: '',
    signature_items: '',
    color_palette: '',
    reference_images: '',
    consistency_instructions: '',
  });
  const [characterSaving, setCharacterSaving] = useState(false);
  const [characterSearch, setCharacterSearch] = useState('');

  // Locations
  const [locations, setLocations] = useState<Location[]>([]);
  const [locationsLoading, setLocationsLoading] = useState(false);
  const [showLocationModal, setShowLocationModal] = useState(false);
  const [editingLocation, setEditingLocation] = useState<Location | null>(null);
  const [locationForm, setLocationForm] = useState<Partial<Location>>({
    name: '',
    type: 'interior',
    description: '',
    environment_details: '',
    reference_images: '',
    visual_style_notes: '',
    lighting: '',
    atmosphere: '',
    time_of_day: '',
    weather: '',
    consistency_instructions: '',
  });
  const [locationSaving, setLocationSaving] = useState(false);
  const [locationSearch, setLocationSearch] = useState('');

  // Episodes
  const [episodes, setEpisodes] = useState<Episode[]>([]);
  const [episodesLoading, setEpisodesLoading] = useState(false);
  const [showEpisodeModal, setShowEpisodeModal] = useState(false);
  const [editingEpisode, setEditingEpisode] = useState<Episode | null>(null);
  const [episodeForm, setEpisodeForm] = useState<Partial<Episode>>({
    episode_number: 1,
    title: '',
    summary: '',
    status: 'planned',
  });
  const [episodeSaving, setEpisodeSaving] = useState(false);

  // Prompts
  const [prompts, setPrompts] = useState<Prompt[]>([]);
  const [promptsLoading, setPromptsLoading] = useState(false);
  const [showPromptModal, setShowPromptModal] = useState(false);
  const [editingPrompt, setEditingPrompt] = useState<Prompt | null>(null);
  const [promptForm, setPromptForm] = useState<Partial<Prompt>>({
    name: '',
    category: 'scene',
    template: '',
    variables: '',
    description: '',
    is_active: true,
  });
  const [promptSaving, setPromptSaving] = useState(false);
  const [promptSearch, setPromptSearch] = useState('');
  const [promptCategoryFilter, setPromptCategoryFilter] = useState('all');

  // Google Accounts
  const [googleAccounts, setGoogleAccounts] = useState<GoogleAccount[]>([]);
  const [googleAccountsLoading, setGoogleAccountsLoading] = useState(false);
  const [oauthUrl, setOauthUrl] = useState<string | null>(null);
  const [showOauthModal, setShowOauthModal] = useState(false);

  // Flow Bridge
  const [flowTasks, setFlowTasks] = useState<FlowBridgeTask[]>([]);
  const [flowTasksLoading, setFlowTasksLoading] = useState(false);
  const [flowAssets, setFlowAssets] = useState<FlowBridgeAsset[]>([]);
  const [flowAssetsLoading, setFlowAssetsLoading] = useState(false);
  const [showFlowTaskModal, setShowFlowTaskModal] = useState(false);
  const [editingFlowTask, setEditingFlowTask] = useState<FlowBridgeTask | null>(null);
  const [flowTaskForm, setFlowTaskForm] = useState<Partial<FlowBridgeTask>>({
    title: '',
    description: '',
    task_type: 'image_gen',
    input_prompts: '',
    input_references: '',
    input_parameters: '',
    priority: 0,
  });
  const [flowTaskSaving, setFlowTaskSaving] = useState(false);
  const [flowTaskFilter, setFlowTaskFilter] = useState('all');

  // Export
  const [exports, setExports] = useState<any[]>([]);
  const [exportsLoading, setExportsLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [exportType, setExportType] = useState('project');
  const [exportEpisodeId, setExportEpisodeId] = useState('');

  // Audit Logs
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [auditLogsLoading, setAuditLogsLoading] = useState(false);
  const [auditLogFilter, setAuditLogFilter] = useState('');

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login');
      return;
    }
    fetchProject();
  }, [isAuthenticated, projectId]);

  const fetchProject = async () => {
    try {
      const response = await api.get(`/projects/${projectId}`);
      setProject(response.data);
      setEditTitle(response.data.title);
      setEditDescription(response.data.description || '');
      setEditGenre(response.data.genre || '');
    } catch (err) {
      console.error('Failed to fetch project:', err);
      router.push('/dashboard');
    } finally {
      setIsLoading(false);
    }
  };

  // Series Bible
  const fetchSeriesBible = useCallback(async () => {
    setSeriesBibleLoading(true);
    try {
      const response = await api.get(`/projects/${projectId}/series-bible`);
      setSeriesBible(response.data);
    } catch (err: any) {
      if (err.response?.status !== 404) {
        console.error('Failed to fetch series bible:', err);
      }
      setSeriesBible(null);
    } finally {
      setSeriesBibleLoading(false);
    }
  }, [projectId]);

  const handleCreateSeriesBible = async (e: React.FormEvent) => {
    e.preventDefault();
    setSeriesBibleSaving(true);
    try {
      const response = await api.post(`/projects/${projectId}/series-bible`, seriesBibleForm);
      setSeriesBible(response.data);
      setShowSeriesBibleModal(false);
    } catch (err) {
      console.error('Failed to create series bible:', err);
    } finally {
      setSeriesBibleSaving(false);
    }
  };

  const handleUpdateSeriesBible = async (e: React.FormEvent) => {
    e.preventDefault();
    setSeriesBibleSaving(true);
    try {
      const response = await api.patch(`/projects/${projectId}/series-bible`, seriesBibleForm);
      setSeriesBible(response.data);
      setShowSeriesBibleModal(false);
    } catch (err) {
      console.error('Failed to update series bible:', err);
    } finally {
      setSeriesBibleSaving(false);
    }
  };

  // Story Engine / Scene Engine
  const fetchStoryTasks = useCallback(async () => {
    try {
      const response = await storyEngineApi.list(projectId);
      setStoryTasks(response.data);
    } catch (err) {
      console.error('Failed to fetch story tasks:', err);
    }
  }, [projectId]);

  const fetchSceneTasks = useCallback(async () => {
    try {
      const response = await sceneEngineApi.list(projectId);
      setSceneTasks(response.data);
    } catch (err) {
      console.error('Failed to fetch scene tasks:', err);
    }
  }, [projectId]);

  const fetchEngineTasks = useCallback(async () => {
    setEngineLoading(true);
    try {
      await Promise.all([fetchStoryTasks(), fetchSceneTasks()]);
    } finally {
      setEngineLoading(false);
    }
  }, [fetchStoryTasks, fetchSceneTasks]);

  const handleCreateStoryTask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!seriesBible) return;
    setEngineMessage('');
    try {
      const parameters: Record<string, unknown> =
        storyType === 'generate_outline'
          ? { total_episodes: parseInt(storyEpisodes, 10) || 20 }
          : storyType === 'generate_episode'
            ? { episode_number: parseInt(storyEpisodeNumber, 10) || 1 }
            : {};
      const response = await storyEngineApi.create(projectId, {
        task_type: storyType,
        series_bible_id: seriesBible.id,
        parameters,
        context: storyContext || undefined,
      });
      setStoryTasks(prev => [response.data, ...prev]);
      setEngineMessage('Story task created — press Execute to run it.');
    } catch (err) {
      console.error('Failed to create story task:', err);
      setEngineMessage('Failed to create story task.');
    }
  };

  const handleCreateSceneTask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!sceneEpisodeId) {
      setEngineMessage('Pick an episode first.');
      return;
    }
    setEngineMessage('');
    try {
      const response = await sceneEngineApi.create(projectId, {
        task_type: sceneType,
        episode_id: sceneEpisodeId,
        scene_id: sceneSceneId || undefined,
        context: sceneContext || undefined,
      });
      setSceneTasks(prev => [response.data, ...prev]);
      setEngineMessage('Scene task created — press Execute to run it.');
    } catch (err) {
      console.error('Failed to create scene task:', err);
      setEngineMessage('Failed to create scene task.');
    }
  };

  const handleSceneEpisodeChange = async (episodeId: string) => {
    setSceneEpisodeId(episodeId);
    setSceneSceneId('');
    if (!episodeId) {
      setSceneEpisodeScenes([]);
      return;
    }
    try {
      const response = await api.get(`/projects/${projectId}/episodes/${episodeId}/scenes`);
      setSceneEpisodeScenes(response.data);
    } catch (err) {
      console.error('Failed to fetch scenes:', err);
      setSceneEpisodeScenes([]);
    }
  };

  const runEngineTask = async (
    kind: 'story' | 'scene', taskId: string,
    action: 'execute' | 'apply' | 'delete'
  ) => {
    const apiClient = kind === 'story' ? storyEngineApi : sceneEngineApi;
    const refresh = kind === 'story' ? fetchStoryTasks : fetchSceneTasks;
    setEngineMessage('');
    try {
      if (action === 'delete') {
        if (!confirm('Delete this task?')) return;
        await apiClient.delete(projectId, taskId);
        setEngineMessage('Task deleted.');
      } else if (action === 'execute') {
        await apiClient.execute(projectId, taskId);
        setEngineMessage('Task finished — check status and output below.');
      } else {
        const response = await apiClient.apply(projectId, taskId);
        const created = response.data?.created_episodes ?? response.data?.created ?? [];
        const count = Array.isArray(created) ? created.length : Object.values(created).flat().length;
        setEngineMessage(`Applied to project: ${count} row(s) created.`);
        fetchEpisodes();
      }
      await refresh();
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      setEngineMessage(
        typeof detail === 'string' ? detail : `Failed to ${action} task.`
      );
      console.error(`Failed to ${action} task:`, err);
      await refresh();
    }
  };

  // Characters
  const fetchCharacters = useCallback(async () => {
    setCharactersLoading(true);
    try {
      const response = await api.get(`/projects/${projectId}/characters`);
      setCharacters(response.data);
    } catch (err) {
      console.error('Failed to fetch characters:', err);
    } finally {
      setCharactersLoading(false);
    }
  }, [projectId]);

  const handleCreateCharacter = async (e: React.FormEvent) => {
    e.preventDefault();
    setCharacterSaving(true);
    try {
      const response = await api.post(`/projects/${projectId}/characters`, characterForm);
      setCharacters(prev => [...prev, response.data].sort((a, b) => a.order_index - b.order_index));
      setShowCharacterModal(false);
      setCharacterForm({
        name: '', role: 'supporting', age: '', gender: '', ethnicity: '',
        height: '', build: '', hair_color: '', hair_style: '', eye_color: '',
        skin_tone: '', distinguishing_features: '', personality_traits: '',
        background: '', motivations: '', fears: '', quirks: '',
        voice_pattern: '', physical_traits: '', skills: '',
        costume_style: '', signature_items: '', color_palette: '',
        reference_images: '', consistency_instructions: '',
      });
      setEditingCharacter(null);
    } catch (err) {
      console.error('Failed to create character:', err);
    } finally {
      setCharacterSaving(false);
    }
  };

  const handleUpdateCharacter = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingCharacter) return;
    setCharacterSaving(true);
    try {
      const response = await api.patch(`/projects/${projectId}/characters/${editingCharacter.id}`, characterForm);
      setCharacters(prev => prev.map(c => c.id === editingCharacter.id ? response.data : c));
      setShowCharacterModal(false);
      setEditingCharacter(null);
    } catch (err) {
      console.error('Failed to update character:', err);
    } finally {
      setCharacterSaving(false);
    }
  };

  const handleDeleteCharacter = async (id: string) => {
    if (!confirm('Delete this character?')) return;
    try {
      await api.delete(`/projects/${projectId}/characters/${id}`);
      setCharacters(prev => prev.filter(c => c.id !== id));
    } catch (err) {
      console.error('Failed to delete character:', err);
    }
  };

  const openEditCharacter = (character: Character) => {
    setEditingCharacter(character);
    setCharacterForm(character);
    setShowCharacterModal(true);
  };

  // Locations
  const fetchLocations = useCallback(async () => {
    setLocationsLoading(true);
    try {
      const response = await api.get(`/projects/${projectId}/locations`);
      setLocations(response.data);
    } catch (err) {
      console.error('Failed to fetch locations:', err);
    } finally {
      setLocationsLoading(false);
    }
  }, [projectId]);

  const handleCreateLocation = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocationSaving(true);
    try {
      const response = await api.post(`/projects/${projectId}/locations`, locationForm);
      setLocations(prev => [...prev, response.data].sort((a, b) => a.order_index - b.order_index));
      setShowLocationModal(false);
      setLocationForm({
        name: '', type: 'interior', description: '', environment_details: '',
        reference_images: '', visual_style_notes: '', lighting: '',
        atmosphere: '', time_of_day: '', weather: '', consistency_instructions: '',
      });
      setEditingLocation(null);
    } catch (err) {
      console.error('Failed to create location:', err);
    } finally {
      setLocationSaving(false);
    }
  };

  const handleUpdateLocation = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingLocation) return;
    setLocationSaving(true);
    try {
      const response = await api.patch(`/projects/${projectId}/locations/${editingLocation.id}`, locationForm);
      setLocations(prev => prev.map(l => l.id === editingLocation.id ? response.data : l));
      setShowLocationModal(false);
      setEditingLocation(null);
    } catch (err) {
      console.error('Failed to update location:', err);
    } finally {
      setLocationSaving(false);
    }
  };

  const handleDeleteLocation = async (id: string) => {
    if (!confirm('Delete this location?')) return;
    try {
      await api.delete(`/projects/${projectId}/locations/${id}`);
      setLocations(prev => prev.filter(l => l.id !== id));
    } catch (err) {
      console.error('Failed to delete location:', err);
    }
  };

  const openEditLocation = (location: Location) => {
    setEditingLocation(location);
    setLocationForm(location);
    setShowLocationModal(true);
  };

  // Episodes
  const fetchEpisodes = useCallback(async () => {
    setEpisodesLoading(true);
    try {
      const response = await api.get(`/projects/${projectId}/episodes`);
      setEpisodes(response.data.sort((a: Episode, b: Episode) => a.episode_number - b.episode_number));
    } catch (err) {
      console.error('Failed to fetch episodes:', err);
    } finally {
      setEpisodesLoading(false);
    }
  }, [projectId]);

  const handleCreateEpisode = async (e: React.FormEvent) => {
    e.preventDefault();
    setEpisodeSaving(true);
    try {
      const response = await api.post(`/projects/${projectId}/episodes`, episodeForm);
      setEpisodes(prev => [...prev, response.data].sort((a, b) => a.episode_number - b.episode_number));
      setShowEpisodeModal(false);
      setEpisodeForm({ episode_number: episodes.length + 1, title: '', summary: '', status: 'planned' });
      setEditingEpisode(null);
    } catch (err) {
      console.error('Failed to create episode:', err);
    } finally {
      setEpisodeSaving(false);
    }
  };

  const handleUpdateEpisode = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingEpisode) return;
    setEpisodeSaving(true);
    try {
      const response = await api.patch(`/projects/${projectId}/episodes/${editingEpisode.id}`, episodeForm);
      setEpisodes(prev => prev.map(ep => ep.id === editingEpisode.id ? response.data : ep));
      setShowEpisodeModal(false);
      setEditingEpisode(null);
    } catch (err) {
      console.error('Failed to update episode:', err);
    } finally {
      setEpisodeSaving(false);
    }
  };

  const handleDeleteEpisode = async (id: string) => {
    if (!confirm('Delete this episode and all its scenes?')) return;
    try {
      await api.delete(`/projects/${projectId}/episodes/${id}`);
      setEpisodes(prev => prev.filter(ep => ep.id !== id));
    } catch (err) {
      console.error('Failed to delete episode:', err);
    }
  };

  const openEditEpisode = (episode: Episode) => {
    setEditingEpisode(episode);
    setEpisodeForm(episode);
    setShowEpisodeModal(true);
  };

  // Prompts
  const fetchPrompts = useCallback(async () => {
    setPromptsLoading(true);
    try {
      const response = await api.get(`/projects/${projectId}/prompts`);
      setPrompts(response.data);
    } catch (err) {
      console.error('Failed to fetch prompts:', err);
    } finally {
      setPromptsLoading(false);
    }
  }, [projectId]);

  const handleCreatePrompt = async (e: React.FormEvent) => {
    e.preventDefault();
    setPromptSaving(true);
    try {
      const response = await api.post(`/projects/${projectId}/prompts`, promptForm);
      setPrompts(prev => [response.data, ...prev]);
      setShowPromptModal(false);
      setPromptForm({ name: '', category: 'scene', template: '', variables: '', description: '', is_active: true });
      setEditingPrompt(null);
    } catch (err) {
      console.error('Failed to create prompt:', err);
    } finally {
      setPromptSaving(false);
    }
  };

  const handleUpdatePrompt = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingPrompt) return;
    setPromptSaving(true);
    try {
      const response = await api.patch(`/projects/${projectId}/prompts/${editingPrompt.id}`, promptForm);
      setPrompts(prev => prev.map(p => p.id === editingPrompt.id ? response.data : p));
      setShowPromptModal(false);
      setEditingPrompt(null);
    } catch (err) {
      console.error('Failed to update prompt:', err);
    } finally {
      setPromptSaving(false);
    }
  };

  const handleDeletePrompt = async (id: string) => {
    if (!confirm('Delete this prompt?')) return;
    try {
      await api.delete(`/projects/${projectId}/prompts/${id}`);
      setPrompts(prev => prev.filter(p => p.id !== id));
    } catch (err) {
      console.error('Failed to delete prompt:', err);
    }
  };

  const openEditPrompt = (prompt: Prompt) => {
    setEditingPrompt(prompt);
    setPromptForm(prompt);
    setShowPromptModal(true);
  };

  // Google Accounts
  const fetchGoogleAccounts = useCallback(async () => {
    setGoogleAccountsLoading(true);
    try {
      const response = await api.get(`/google-accounts`);
      setGoogleAccounts(response.data);
    } catch (err) {
      console.error('Failed to fetch Google accounts:', err);
    } finally {
      setGoogleAccountsLoading(false);
    }
  }, []);

  const handleOAuthAuthorize = async () => {
    try {
      const response = await api.get(`/google-accounts/oauth/authorize`);
      setOauthUrl(response.data.authorize_url);
      setShowOauthModal(true);
    } catch (err) {
      console.error('Failed to get OAuth URL:', err);
      alert('Failed to start OAuth flow. Ensure Google OAuth credentials are configured in Settings.');
    }
  };

  const handleVerifyAccount = async (accountId: string) => {
    try {
      await api.post(`/google-accounts/${accountId}/verify`);
      fetchGoogleAccounts();
    } catch (err) {
      console.error('Failed to verify account:', err);
    }
  };

  const handleRefreshAccount = async (accountId: string) => {
    try {
      await api.post(`/google-accounts/${accountId}/refresh`);
      fetchGoogleAccounts();
    } catch (err) {
      console.error('Failed to refresh account:', err);
    }
  };

  const handleDeleteGoogleAccount = async (id: string) => {
    if (!confirm('Disconnect this Google account?')) return;
    try {
      await api.delete(`/google-accounts/${id}`);
      fetchGoogleAccounts();
    } catch (err) {
      console.error('Failed to delete Google account:', err);
    }
  };

  // Flow Bridge
  const fetchFlowTasks = useCallback(async () => {
    setFlowTasksLoading(true);
    try {
      const response = await flowBridgeApi.listTasks(projectId);
      setFlowTasks(response.data);
    } catch (err) {
      console.error('Failed to fetch flow tasks:', err);
    } finally {
      setFlowTasksLoading(false);
    }
  }, [projectId]);

  const fetchFlowAssets = useCallback(async () => {
    setFlowAssetsLoading(true);
    try {
      const response = await flowBridgeApi.listProjectAssets(projectId);
      setFlowAssets(response.data);
    } catch (err) {
      console.error('Failed to fetch flow assets:', err);
    } finally {
      setFlowAssetsLoading(false);
    }
  }, [projectId]);

  const handleCreateFlowTask = async (e: React.FormEvent) => {
    e.preventDefault();
    setFlowTaskSaving(true);
    try {
      const response = await flowBridgeApi.createTask(projectId, flowTaskForm);
      setFlowTasks(prev => [response.data, ...prev]);
      setShowFlowTaskModal(false);
      setFlowTaskForm({ title: '', description: '', task_type: 'image_gen', input_prompts: '', input_references: '', input_parameters: '', priority: 0 });
      setEditingFlowTask(null);
    } catch (err) {
      console.error('Failed to create flow task:', err);
    } finally {
      setFlowTaskSaving(false);
    }
  };

  const handleUpdateFlowTask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingFlowTask) return;
    setFlowTaskSaving(true);
    try {
      const response = await flowBridgeApi.updateTask(projectId, editingFlowTask.id, flowTaskForm);
      setFlowTasks(prev => prev.map(t => t.id === editingFlowTask.id ? response.data : t));
      setShowFlowTaskModal(false);
      setEditingFlowTask(null);
    } catch (err) {
      console.error('Failed to update flow task:', err);
    } finally {
      setFlowTaskSaving(false);
    }
  };

  const handleDeleteFlowTask = async (id: string) => {
    if (!confirm('Delete this flow task?')) return;
    try {
      await flowBridgeApi.deleteTask(projectId, id);
      setFlowTasks(prev => prev.filter(t => t.id !== id));
    } catch (err) {
      console.error('Failed to delete flow task:', err);
    }
  };

  const openEditFlowTask = (task: FlowBridgeTask) => {
    setEditingFlowTask(task);
    setFlowTaskForm(task);
    setShowFlowTaskModal(true);
  };

  // Export
  const fetchExports = useCallback(async () => {
    setExportsLoading(true);
    try {
      const response = await exportApi.list(projectId);
      setExports(response.data);
    } catch (err) {
      console.error('Failed to fetch exports:', err);
    } finally {
      setExportsLoading(false);
    }
  }, [projectId]);

  const handleExport = async (e: React.FormEvent) => {
    e.preventDefault();
    setExporting(true);
    try {
      if (exportType === 'project') {
        const response = await exportApi.create(projectId, { export_type: 'project' });
        setExports(prev => [response.data, ...prev]);
      } else if (exportType === 'episode' && exportEpisodeId) {
        const response = await exportApi.create(projectId, { export_type: 'episode', episode_id: exportEpisodeId });
        setExports(prev => [response.data, ...prev]);
      } else if (exportType === 'prompts') {
        const response = await exportApi.create(projectId, { export_type: 'prompts' });
        setExports(prev => [response.data, ...prev]);
      }
    } catch (err) {
      console.error('Failed to export:', err);
    } finally {
      setExporting(false);
    }
  };

  const handleDownloadExport = async (exportId: string) => {
    try {
      const response = await exportApi.download(projectId, exportId);
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `export-${exportId}.zip`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      console.error('Failed to download export:', err);
    }
  };

  // Audit Logs
  const fetchAuditLogs = useCallback(async () => {
    setAuditLogsLoading(true);
    try {
      const response = await api.get(`/audit-logs`, { params: { project_id: projectId } });
      setAuditLogs(response.data);
    } catch (err) {
      console.error('Failed to fetch audit logs:', err);
    } finally {
      setAuditLogsLoading(false);
    }
  }, [projectId]);

  // Load data when tab changes
  useEffect(() => {
    switch (activeTab) {
      case 'series-bible':
        fetchSeriesBible();
        fetchEpisodes();
        fetchEngineTasks();
        break;
      case 'characters':
        fetchCharacters();
        break;
      case 'locations':
        fetchLocations();
        break;
      case 'episodes':
        fetchEpisodes();
        break;
      case 'prompts':
        fetchPrompts();
        break;
      case 'google-accounts':
        fetchGoogleAccounts();
        break;
      case 'flow-bridge':
        fetchFlowTasks();
        fetchFlowAssets();
        break;
      case 'export':
        fetchExports();
        break;
      case 'audit-logs':
        fetchAuditLogs();
        break;
    }
  }, [activeTab, fetchSeriesBible, fetchCharacters, fetchLocations, fetchEpisodes, fetchPrompts, fetchGoogleAccounts, fetchFlowTasks, fetchFlowAssets, fetchExports, fetchAuditLogs, fetchEngineTasks]);

  const handleUpdateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    try {
      await api.patch(`/projects/${projectId}`, {
        title: editTitle,
        description: editDescription,
        genre: editGenre,
      });
      setProject(prev => prev ? { ...prev, title: editTitle, description: editDescription, genre: editGenre } : null);
      setShowEditModal(false);
    } catch (err) {
      console.error('Failed to update project:', err);
    } finally {
      setIsSaving(false);
    }
  };

  const handleDeleteProject = async () => {
    if (!confirm('Are you sure you want to delete this project? This action cannot be undone.')) return;
    try {
      await api.delete(`/projects/${projectId}`);
      router.push('/dashboard');
    } catch (err) {
      console.error('Failed to delete project:', err);
    }
  };

  // Auto-Generate (spec §6)
  const openAutoGenerateModal = () => {
    if (!autoGenJob) {
      setAutoGenForm({
        title: project?.title || '',
        genre: project?.genre || '',
        total_episodes: String(project?.total_episodes || 30),
        premise: '',
      });
    }
    setAutoGenError('');
    setShowAutoGenerateModal(true);
  };

  // Plain function (not useCallback): only called from event handlers,
  // no memoization needed — avoids exhaustive-deps churn on fetchProject.
  const refreshAutoGenData = () => {
    fetchProject();
    fetchSeriesBible();
    fetchCharacters();
    fetchLocations();
    fetchEpisodes();
    fetchPrompts();
  };

  const handleAutoGenerateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!autoGenForm.title.trim()) return;
    setAutoGenSubmitting(true);
    setAutoGenError('');
    setAutoGenJob(null);
    try {
      const response = await autoGenerateApi.create(projectId, {
        title: autoGenForm.title.trim(),
        genre: autoGenForm.genre.trim() || undefined,
        total_episodes: Math.min(60, Math.max(1, parseInt(autoGenForm.total_episodes, 10) || 30)),
        premise: autoGenForm.premise.trim() || undefined,
      });
      setAutoGenJob(response.data);
      if (response.data.status === 'completed') refreshAutoGenData();
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      setAutoGenError(typeof detail === 'string' ? detail : 'Failed to start auto-generate.');
      console.error('Failed to start auto-generate:', err);
    } finally {
      setAutoGenSubmitting(false);
    }
  };

  const handleAutoGenRetry = async (step: string) => {
    if (!autoGenJob) return;
    setAutoGenRetrying(step);
    setAutoGenError('');
    try {
      const response = await autoGenerateApi.retry(projectId, autoGenJob.id, step);
      setAutoGenJob(response.data);
      if (response.data.status === 'completed') refreshAutoGenData();
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      setAutoGenError(typeof detail === 'string' ? detail : `Failed to retry step ${step}.`);
      console.error('Failed to retry auto-generate step:', err);
    } finally {
      setAutoGenRetrying(null);
    }
  };

  const handleAutoGenRefresh = async () => {
    if (!autoGenJob) return;
    try {
      const response = await autoGenerateApi.get(projectId, autoGenJob.id);
      setAutoGenJob(response.data);
      if (response.data.status === 'completed') refreshAutoGenData();
    } catch (err) {
      console.error('Failed to refresh auto-generate job:', err);
    }
  };

  const openAutoGenResults = (tab: Tab) => {
    setShowAutoGenerateModal(false);
    setActiveTab(tab);
  };

  if (!isAuthenticated || isLoading) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-slate-900 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
      </div>
    );
  }

  if (!project) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-slate-900 flex items-center justify-center">
        <p className="text-slate-500">Project not found</p>
      </div>
    );
  }

  const renderTabContent = () => {
    switch (activeTab) {
      case 'overview':
        return (
          <div className="space-y-6">
            <div className="card">
              <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">Project Details</h2>
              <dl className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <dt className="text-sm text-slate-500 dark:text-slate-400">Title</dt>
                  <dd className="text-slate-900 dark:text-white font-medium">{project.title}</dd>
                </div>
                <div>
                  <dt className="text-sm text-slate-500 dark:text-slate-400">Status</dt>
                  <dd className="text-slate-900 dark:text-white capitalize">{project.status.replace('_', ' ')}</dd>
                </div>
                <div>
                  <dt className="text-sm text-slate-500 dark:text-slate-400">Genre</dt>
                  <dd className="text-slate-900 dark:text-white">{project.genre || 'Not set'}</dd>
                </div>
                <div>
                  <dt className="text-sm text-slate-500 dark:text-slate-400">Total Episodes</dt>
                  <dd className="text-slate-900 dark:text-white">{project.total_episodes}</dd>
                </div>
                <div>
                  <dt className="text-sm text-slate-500 dark:text-slate-400">Created</dt>
                  <dd className="text-slate-900 dark:text-white">{formatDate(project.created_at)}</dd>
                </div>
                <div>
                  <dt className="text-sm text-slate-500 dark:text-slate-400">Updated</dt>
                  <dd className="text-slate-900 dark:text-white">{formatDate(project.updated_at)}</dd>
                </div>
              </dl>
            </div>
            
            {project.description && (
              <div className="card">
                <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">Description</h2>
                <p className="text-slate-600 dark:text-slate-300 whitespace-pre-wrap">{project.description}</p>
              </div>
            )}
          </div>
        );

      case 'series-bible':
        return (
          <div className="space-y-6">
            {!seriesBible ? (
              <div className="card">
                <div className="text-center py-12">
                  <BookOpen className="w-12 h-12 text-slate-300 dark:text-slate-600 mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-slate-900 dark:text-white mb-2">No Series Bible yet</h3>
                  <p className="text-slate-500 dark:text-slate-400 mb-6">Create a Series Bible to define your story foundation</p>
                  <button 
                    onClick={() => setShowSeriesBibleModal(true)}
                    className="btn-primary"
                    disabled={seriesBibleSaving}
                  >
                    <Plus className="w-4 h-4 mr-2" />
                    Create Series Bible
                  </button>
                </div>
              </div>
            ) : (
              <>
                <div className="card">
                  <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">Series Bible Overview</h3>
                  <div className="space-y-4">
                    {seriesBible.premise && (
                      <div>
                        <h4 className="text-sm font-medium text-slate-500 dark:text-slate-400 mb-1">Premise</h4>
                        <p className="text-slate-900 dark:text-white">{seriesBible.premise}</p>
                      </div>
                    )}
                    {seriesBible.main_plot && (
                      <div>
                        <h4 className="text-sm font-medium text-slate-500 dark:text-slate-400 mb-1">Main Plot</h4>
                        <p className="text-slate-900 dark:text-white">{seriesBible.main_plot}</p>
                      </div>
                    )}
                    {seriesBible.tone_and_visual_style && (
                      <div>
                        <h4 className="text-sm font-medium text-slate-500 dark:text-slate-400 mb-1">Tone & Visual Style</h4>
                        <p className="text-slate-900 dark:text-white">{seriesBible.tone_and_visual_style}</p>
                      </div>
                    )}
                    {seriesBible.ending_direction && (
                      <div>
                        <h4 className="text-sm font-medium text-slate-500 dark:text-slate-400 mb-1">Ending Direction</h4>
                        <p className="text-slate-900 dark:text-white">{seriesBible.ending_direction}</p>
                      </div>
                    )}
                    {seriesBible.world_settings && (
                      <div>
                        <h4 className="text-sm font-medium text-slate-500 dark:text-slate-400 mb-1">World Settings</h4>
                        <p className="text-slate-900 dark:text-white">{seriesBible.world_settings}</p>
                      </div>
                    )}
                    {seriesBible.character_relationships && (
                      <div>
                        <h4 className="text-sm font-medium text-slate-500 dark:text-slate-400 mb-1">Character Relationships</h4>
                        <p className="text-slate-900 dark:text-white">{seriesBible.character_relationships}</p>
                      </div>
                    )}
                    {seriesBible.subplots && Array.isArray(seriesBible.subplots) && seriesBible.subplots.length > 0 && (
                      <div>
                        <h4 className="text-sm font-medium text-slate-500 dark:text-slate-400 mb-1">Subplots</h4>
                        <ul className="list-disc list-inside text-slate-900 dark:text-white space-y-1">
                          {seriesBible.subplots.map((subplot, i) => <li key={i}>{subplot}</li>)}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>

                <div className="card">
                  <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">Story Engine Tasks</h3>
                  {engineMessage && (
                    <p className="text-sm text-slate-600 dark:text-slate-300 mb-4">{engineMessage}</p>
                  )}
                  <form onSubmit={handleCreateStoryTask} className="space-y-3 mb-6">
                    <div className="flex flex-wrap gap-2">
                      <select value={storyType} onChange={(e) => setStoryType(e.target.value)} className="input w-auto">
                        <option value="generate_outline">Generate outline</option>
                        <option value="generate_episode">Generate one episode</option>
                        <option value="generate_character_arcs">Character arcs</option>
                        <option value="generate_world_building">World building</option>
                      </select>
                      {storyType === 'generate_outline' && (
                        <input type="number" min={1} max={100} value={storyEpisodes} onChange={(e) => setStoryEpisodes(e.target.value)} className="input w-28" placeholder="Episodes" title="Total episodes" />
                      )}
                      {storyType === 'generate_episode' && (
                        <input type="number" min={1} max={100} value={storyEpisodeNumber} onChange={(e) => setStoryEpisodeNumber(e.target.value)} className="input w-28" placeholder="Episode #" title="Episode number" />
                      )}
                      <button type="submit" className="btn-primary" disabled={!seriesBible}>
                        <Plus className="w-4 h-4 mr-2" />
                        New Task
                      </button>
                    </div>
                    <textarea value={storyContext} onChange={(e) => setStoryContext(e.target.value)} className="input" rows={2} placeholder="Your instructions for the LLM (optional) — e.g. make episode 3 a flashback" />
                  </form>
                  {engineLoading ? (
                    <div className="flex justify-center py-8"><Loader2 className="w-8 h-8 animate-spin text-primary-600" /></div>
                  ) : storyTasks.length === 0 ? (
                    <div className="text-center py-8 text-slate-500 dark:text-slate-400">
                      <Sparkles className="w-10 h-10 text-slate-300 dark:text-slate-600 mx-auto mb-3" />
                      <p>No story engine tasks yet</p>
                      <p className="text-sm mt-1">Create a task to generate outline, character arcs, or world building</p>
                    </div>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full">
                        <thead>
                          <tr className="border-b border-slate-200 dark:border-slate-700">
                            <th className="text-left py-3 px-4 text-sm font-medium text-slate-500 dark:text-slate-400">Task Type</th>
                            <th className="text-left py-3 px-4 text-sm font-medium text-slate-500 dark:text-slate-400">Status</th>
                            <th className="text-left py-3 px-4 text-sm font-medium text-slate-500 dark:text-slate-400">Created</th>
                            <th className="text-left py-3 px-4 text-sm font-medium text-slate-500 dark:text-slate-400">Actions</th>
                          </tr>
                        </thead>
                        <tbody>
                          {storyTasks.map((task) => (
                            <tr key={task.id} className="border-b border-slate-100 dark:border-slate-800">
                              <td className="py-3 px-4 text-sm text-slate-900 dark:text-white">{task.task_type}</td>
                              <td className="py-3 px-4">
                                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                                  task.status === 'completed' ? 'bg-green-100 text-green-800' :
                                  task.status === 'failed' ? 'bg-red-100 text-red-800' :
                                  task.status === 'processing' ? 'bg-blue-100 text-blue-800' :
                                  'bg-slate-100 text-slate-800'
                                }`}>{task.status}</span>
                                {task.status === 'failed' && task.error_message && (
                                  <div className="text-xs text-red-600 mt-1 max-w-xs truncate" title={task.error_message}>{task.error_message}</div>
                                )}
                              </td>
                              <td className="py-3 px-4 text-sm text-slate-600 dark:text-slate-300">{formatDate(task.created_at)}</td>
                              <td className="py-3 px-4">
                                <div className="flex items-center gap-2 flex-wrap">
                                  {task.status !== 'processing' && (
                                    <button onClick={() => runEngineTask('story', task.id, 'execute')} className="btn-ghost p-1.5 text-primary-600" title={task.status === 'failed' ? 'Retry' : 'Execute'}>
                                      <Play className="w-4 h-4" />
                                    </button>
                                  )}
                                  {task.status === 'completed' && (task.task_type === 'generate_outline' || task.task_type === 'generate_episode') && (
                                    <button onClick={() => runEngineTask('story', task.id, 'apply')} className="btn-ghost p-1.5 text-green-600" title="Apply to project (create episodes)">
                                      <CheckCircle className="w-4 h-4" />
                                    </button>
                                  )}
                                  {task.output && (
                                    <button onClick={() => setExpandedTask(expandedTask === task.id ? null : task.id)} className="btn-ghost p-1.5" title="Show output">
                                      <Eye className="w-4 h-4" />
                                    </button>
                                  )}
                                  <button onClick={() => runEngineTask('story', task.id, 'delete')} className="btn-ghost p-1.5 text-red-600" title="Delete">
                                    <Trash2 className="w-4 h-4" />
                                  </button>
                                </div>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                      {expandedTask && storyTasks.find(t => t.id === expandedTask)?.output && (
                        <pre className="mt-4 p-4 bg-slate-100 dark:bg-slate-800 rounded text-xs overflow-auto max-h-96">{JSON.stringify(storyTasks.find(t => t.id === expandedTask)?.output, null, 2)}</pre>
                      )}
                    </div>
                  )}
                </div>

                <div className="card">
                  <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">Scene Engine Tasks</h3>
                  <form onSubmit={handleCreateSceneTask} className="space-y-3 mb-6">
                    <div className="flex flex-wrap gap-2">
                      <select value={sceneType} onChange={(e) => setSceneType(e.target.value)} className="input w-auto">
                        <option value="breakdown_episode">Breakdown episode</option>
                        <option value="generate_scenes">Generate scenes</option>
                        <option value="generate_shots">Generate shots</option>
                        <option value="generate_dialogue">Generate dialogue</option>
                        <option value="generate_action">Generate action</option>
                      </select>
                      <select value={sceneEpisodeId} onChange={(e) => handleSceneEpisodeChange(e.target.value)} className="input w-auto">
                        <option value="">Select episode</option>
                        {episodes.map((ep) => (
                          <option key={ep.id} value={ep.id}>Ep {ep.episode_number}: {ep.title || 'Untitled'}</option>
                        ))}
                      </select>
                      {(sceneType === 'generate_shots' || sceneType === 'generate_dialogue' || sceneType === 'generate_action') && (
                        <select value={sceneSceneId} onChange={(e) => setSceneSceneId(e.target.value)} className="input w-auto">
                          <option value="">Select scene</option>
                          {sceneEpisodeScenes.map((s) => (
                            <option key={s.id} value={s.id}>Scene {s.scene_number}: {s.title || 'Untitled'}</option>
                          ))}
                        </select>
                      )}
                      <button type="submit" className="btn-primary">
                        <Plus className="w-4 h-4 mr-2" />
                        New Task
                      </button>
                    </div>
                    <textarea value={sceneContext} onChange={(e) => setSceneContext(e.target.value)} className="input" rows={2} placeholder="Notes for this task (optional)" />
                  </form>
                  {sceneTasks.length === 0 ? (
                    <div className="text-center py-8 text-slate-500 dark:text-slate-400">
                      <Clapperboard className="w-10 h-10 text-slate-300 dark:text-slate-600 mx-auto mb-3" />
                      <p>No scene engine tasks yet</p>
                      <p className="text-sm mt-1">Break an episode into scenes, shots, dialogue, or action beats</p>
                    </div>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full">
                        <thead>
                          <tr className="border-b border-slate-200 dark:border-slate-700">
                            <th className="text-left py-3 px-4 text-sm font-medium text-slate-500 dark:text-slate-400">Task Type</th>
                            <th className="text-left py-3 px-4 text-sm font-medium text-slate-500 dark:text-slate-400">Status</th>
                            <th className="text-left py-3 px-4 text-sm font-medium text-slate-500 dark:text-slate-400">Created</th>
                            <th className="text-left py-3 px-4 text-sm font-medium text-slate-500 dark:text-slate-400">Actions</th>
                          </tr>
                        </thead>
                        <tbody>
                          {sceneTasks.map((task) => (
                            <tr key={task.id} className="border-b border-slate-100 dark:border-slate-800">
                              <td className="py-3 px-4 text-sm text-slate-900 dark:text-white">{task.task_type}</td>
                              <td className="py-3 px-4">
                                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                                  task.status === 'completed' ? 'bg-green-100 text-green-800' :
                                  task.status === 'failed' ? 'bg-red-100 text-red-800' :
                                  task.status === 'processing' ? 'bg-blue-100 text-blue-800' :
                                  'bg-slate-100 text-slate-800'
                                }`}>{task.status}</span>
                                {task.status === 'failed' && task.error_message && (
                                  <div className="text-xs text-red-600 mt-1 max-w-xs truncate" title={task.error_message}>{task.error_message}</div>
                                )}
                              </td>
                              <td className="py-3 px-4 text-sm text-slate-600 dark:text-slate-300">{formatDate(task.created_at)}</td>
                              <td className="py-3 px-4">
                                <div className="flex items-center gap-2 flex-wrap">
                                  {task.status !== 'processing' && (
                                    <button onClick={() => runEngineTask('scene', task.id, 'execute')} className="btn-ghost p-1.5 text-primary-600" title={task.status === 'failed' ? 'Retry' : 'Execute'}>
                                      <Play className="w-4 h-4" />
                                    </button>
                                  )}
                                  {task.status === 'completed' && task.task_type !== 'refine_scenes' && (
                                    <button onClick={() => runEngineTask('scene', task.id, 'apply')} className="btn-ghost p-1.5 text-green-600" title="Apply to project (create scenes/shots/dialogue)">
                                      <CheckCircle className="w-4 h-4" />
                                    </button>
                                  )}
                                  {task.output && (
                                    <button onClick={() => setExpandedTask(expandedTask === task.id ? null : task.id)} className="btn-ghost p-1.5" title="Show output">
                                      <Eye className="w-4 h-4" />
                                    </button>
                                  )}
                                  <button onClick={() => runEngineTask('scene', task.id, 'delete')} className="btn-ghost p-1.5 text-red-600" title="Delete">
                                    <Trash2 className="w-4 h-4" />
                                  </button>
                                </div>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                      {expandedTask && sceneTasks.find(t => t.id === expandedTask)?.output && (
                        <pre className="mt-4 p-4 bg-slate-100 dark:bg-slate-800 rounded text-xs overflow-auto max-h-96">{JSON.stringify(sceneTasks.find(t => t.id === expandedTask)?.output, null, 2)}</pre>
                      )}
                    </div>
                  )}
                </div>
              </>
            )}
          </div>
        );

      case 'characters':
        return (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Characters</h2>
              <button 
                onClick={() => { setEditingCharacter(null); setCharacterForm({ name: '', role: 'supporting', age: '', gender: '', ethnicity: '', height: '', build: '', hair_color: '', hair_style: '', eye_color: '', skin_tone: '', distinguishing_features: '', personality_traits: '', background: '', motivations: '', fears: '', quirks: '', voice_pattern: '', physical_traits: '', skills: '', costume_style: '', signature_items: '', color_palette: '', reference_images: '', consistency_instructions: '' }); setShowCharacterModal(true); }}
                className="btn-primary"
              >
                <Plus className="w-4 h-4 mr-2" />
                Add Character
              </button>
            </div>
            
            {charactersLoading ? (
              <div className="card"><div className="flex justify-center py-12"><Loader2 className="w-8 h-8 animate-spin text-primary-600" /></div></div>
            ) : characters.length === 0 ? (
              <div className="card">
                <div className="text-center py-12">
                  <Users className="w-12 h-12 text-slate-300 dark:text-slate-600 mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-slate-900 dark:text-white mb-2">No characters yet</h3>
                  <p className="text-slate-500 dark:text-slate-400 mb-6">Create characters for your project</p>
                  <button 
                    onClick={() => { setEditingCharacter(null); setCharacterForm({ name: '', role: 'supporting', age: '', gender: '', ethnicity: '', height: '', build: '', hair_color: '', hair_style: '', eye_color: '', skin_tone: '', distinguishing_features: '', personality_traits: '', background: '', motivations: '', fears: '', quirks: '', voice_pattern: '', physical_traits: '', skills: '', costume_style: '', signature_items: '', color_palette: '', reference_images: '', consistency_instructions: '' }); setShowCharacterModal(true); }}
                    className="btn-primary"
                  >
                    <Plus className="w-4 h-4 mr-2" />
                    Create First Character
                  </button>
                </div>
              </div>
            ) : (
              <div className="card">
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-slate-200 dark:border-slate-700">
                        <th className="text-left py-3 px-4 text-sm font-medium text-slate-500 dark:text-slate-400">#</th>
                        <th className="text-left py-3 px-4 text-sm font-medium text-slate-500 dark:text-slate-400">Name</th>
                        <th className="text-left py-3 px-4 text-sm font-medium text-slate-500 dark:text-slate-400">Role</th>
                        <th className="text-left py-3 px-4 text-sm font-medium text-slate-500 dark:text-slate-400">Age</th>
                        <th className="text-left py-3 px-4 text-sm font-medium text-slate-500 dark:text-slate-400">Gender</th>
                        <th className="text-left py-3 px-4 text-sm font-medium text-slate-500 dark:text-slate-400">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {characters
                        .filter(c => characterSearch === '' || c.name.toLowerCase().includes(characterSearch.toLowerCase()))
                        .sort((a, b) => a.order_index - b.order_index)
                        .map((character, index) => (
                          <tr key={character.id} className="border-b border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/50">
                            <td className="py-3 px-4 text-sm text-slate-900 dark:text-white">{index + 1}</td>
                            <td className="py-3 px-4">
                              <div className="font-medium text-slate-900 dark:text-white">{character.name}</div>
                              {character.background && <div className="text-sm text-slate-500 dark:text-slate-400 truncate max-w-xs">{character.background}</div>}
                            </td>
                            <td className="py-3 px-4 text-sm text-slate-600 dark:text-slate-300">{character.role || '—'}</td>
                            <td className="py-3 px-4 text-sm text-slate-600 dark:text-slate-300">{character.age || '—'}</td>
                            <td className="py-3 px-4 text-sm text-slate-600 dark:text-slate-300">{character.gender || '—'}</td>
                            <td className="py-3 px-4">
                              <div className="flex items-center gap-2">
                                <button onClick={() => openEditCharacter(character)} className="btn-ghost p-1.5" title="Edit">
                                  <Edit className="w-4 h-4" />
                                </button>
                                <button onClick={() => handleDeleteCharacter(character.id)} className="btn-ghost p-1.5 text-red-600 hover:text-red-700" title="Delete">
                                  <Trash2 className="w-4 h-4" />
                                </button>
                              </div>
                            </td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        );

      case 'locations':
        return (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Locations</h2>
              <button 
                onClick={() => { setEditingLocation(null); setLocationForm({ name: '', type: 'interior', description: '', environment_details: '', reference_images: '', visual_style_notes: '', lighting: '', atmosphere: '', time_of_day: '', weather: '', consistency_instructions: '' }); setShowLocationModal(true); }}
                className="btn-primary"
              >
                <Plus className="w-4 h-4 mr-2" />
                Add Location
              </button>
            </div>
            
            {locationsLoading ? (
              <div className="card"><div className="flex justify-center py-12"><Loader2 className="w-8 h-8 animate-spin text-primary-600" /></div></div>
            ) : locations.length === 0 ? (
              <div className="card">
                <div className="text-center py-12">
                  <MapPin className="w-12 h-12 text-slate-300 dark:text-slate-600 mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-slate-900 dark:text-white mb-2">No locations yet</h3>
                  <p className="text-slate-500 dark:text-slate-400 mb-6">Create locations for your scenes</p>
                  <button 
                    onClick={() => { setEditingLocation(null); setLocationForm({ name: '', type: 'interior', description: '', environment_details: '', reference_images: '', visual_style_notes: '', lighting: '', atmosphere: '', time_of_day: '', weather: '', consistency_instructions: '' }); setShowLocationModal(true); }}
                    className="btn-primary"
                  >
                    <Plus className="w-4 h-4 mr-2" />
                    Create First Location
                  </button>
                </div>
              </div>
            ) : (
              <div className="card">
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-slate-200 dark:border-slate-700">
                        <th className="text-left py-3 px-4 text-sm font-medium text-slate-500 dark:text-slate-400">#</th>
                        <th className="text-left py-3 px-4 text-sm font-medium text-slate-500 dark:text-slate-400">Name</th>
                        <th className="text-left py-3 px-4 text-sm font-medium text-slate-500 dark:text-slate-400">Type</th>
                        <th className="text-left py-3 px-4 text-sm font-medium text-slate-500 dark:text-slate-400">Time of Day</th>
                        <th className="text-left py-3 px-4 text-sm font-medium text-slate-500 dark:text-slate-400">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {locations
                        .filter(l => locationSearch === '' || l.name.toLowerCase().includes(locationSearch.toLowerCase()))
                        .sort((a, b) => a.order_index - b.order_index)
                        .map((location, index) => (
                          <tr key={location.id} className="border-b border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/50">
                            <td className="py-3 px-4 text-sm text-slate-900 dark:text-white">{index + 1}</td>
                            <td className="py-3 px-4">
                              <div className="font-medium text-slate-900 dark:text-white">{location.name}</div>
                              {location.description && <div className="text-sm text-slate-500 dark:text-slate-400 truncate max-w-xs">{location.description}</div>}
                            </td>
                            <td className="py-3 px-4 text-sm text-slate-600 dark:text-slate-300 capitalize">{location.type || '—'}</td>
                            <td className="py-3 px-4 text-sm text-slate-600 dark:text-slate-300">{location.time_of_day || '—'}</td>
                            <td className="py-3 px-4">
                              <div className="flex items-center gap-2">
                                <button onClick={() => openEditLocation(location)} className="btn-ghost p-1.5" title="Edit">
                                  <Edit className="w-4 h-4" />
                                </button>
                                <button onClick={() => handleDeleteLocation(location.id)} className="btn-ghost p-1.5 text-red-600 hover:text-red-700" title="Delete">
                                  <Trash2 className="w-4 h-4" />
                                </button>
                              </div>
                            </td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        );

      case 'episodes':
        return (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Episodes</h2>
              <button 
                onClick={() => { setEditingEpisode(null); setEpisodeForm({ episode_number: episodes.length + 1, title: '', summary: '', status: 'planned' }); setShowEpisodeModal(true); }}
                className="btn-primary"
              >
                <Plus className="w-4 h-4 mr-2" />
                Add Episode
              </button>
            </div>
            
            {episodesLoading ? (
              <div className="card"><div className="flex justify-center py-12"><Loader2 className="w-8 h-8 animate-spin text-primary-600" /></div></div>
            ) : episodes.length === 0 ? (
              <div className="card">
                <div className="text-center py-12">
                  <Clapperboard className="w-12 h-12 text-slate-300 dark:text-slate-600 mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-slate-900 dark:text-white mb-2">No episodes yet</h3>
                  <p className="text-slate-500 dark:text-slate-400 mb-6">Create episodes for your series (up to 20)</p>
                  <button 
                    onClick={() => { setEditingEpisode(null); setEpisodeForm({ episode_number: episodes.length + 1, title: '', summary: '', status: 'planned' }); setShowEpisodeModal(true); }}
                    className="btn-primary"
                  >
                    <Plus className="w-4 h-4 mr-2" />
                    Create First Episode
                  </button>
                </div>
              </div>
            ) : (
              <div className="card">
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-slate-200 dark:border-slate-700">
                        <th className="text-left py-3 px-4 text-sm font-medium text-slate-500 dark:text-slate-400">#</th>
                        <th className="text-left py-3 px-4 text-sm font-medium text-slate-500 dark:text-slate-400">Title</th>
                        <th className="text-left py-3 px-4 text-sm font-medium text-slate-500 dark:text-slate-400">Summary</th>
                        <th className="text-left py-3 px-4 text-sm font-medium text-slate-500 dark:text-slate-400">Status</th>
                        <th className="text-left py-3 px-4 text-sm font-medium text-slate-500 dark:text-slate-400">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {episodes
                        .sort((a, b) => a.episode_number - b.episode_number)
                        .map((episode) => (
                          <tr key={episode.id} className="border-b border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/50">
                            <td className="py-3 px-4 text-sm font-mono text-slate-900 dark:text-white">Ep {episode.episode_number}</td>
                            <td className="py-3 px-4 font-medium text-slate-900 dark:text-white">{episode.title || 'Untitled'}</td>
                            <td className="py-3 px-4 text-sm text-slate-600 dark:text-slate-300 truncate max-w-md">{episode.summary || '—'}</td>
                            <td className="py-3 px-4">
                              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                                episode.status === 'completed' ? 'bg-green-100 text-green-800' :
                                episode.status === 'in_production' ? 'bg-blue-100 text-blue-800' :
                                episode.status === 'scenes_written' ? 'bg-purple-100 text-purple-800' :
                                episode.status === 'outlined' ? 'bg-yellow-100 text-yellow-800' :
                                'bg-slate-100 text-slate-800'
                              }`}>
                                {episode.status.replace('_', ' ')}
                              </span>
                            </td>
                            <td className="py-3 px-4">
                              <div className="flex items-center gap-2">
                                <button onClick={() => openEditEpisode(episode)} className="btn-ghost p-1.5" title="Edit">
                                  <Edit className="w-4 h-4" />
                                </button>
                                <button onClick={() => handleDeleteEpisode(episode.id)} className="btn-ghost p-1.5 text-red-600 hover:text-red-700" title="Delete">
                                  <Trash2 className="w-4 h-4" />
                                </button>
                              </div>
                            </td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        );

      case 'prompts':
        return (
          <div className="space-y-6">
            <div className="flex items-center justify-between flex-wrap gap-4">
              <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Prompt Studio</h2>
              <div className="flex items-center gap-2">
                <select value={promptCategoryFilter} onChange={(e) => setPromptCategoryFilter(e.target.value)} className="input w-auto">
                  <option value="all">All Categories</option>
                  <option value="character_image">Character Image</option>
                  <option value="location_image">Location Image</option>
                  <option value="scene_image">Scene Image</option>
                  <option value="video_generation">Video Generation</option>
                  <option value="camera_movement">Camera Movement</option>
                  <option value="character_action">Character Action</option>
                  <option value="dialogue_audio">Dialogue Audio</option>
                  <option value="sound_effect">Sound Effect</option>
                  <option value="music">Music</option>
                </select>
                <input
                  type="text"
                  placeholder="Search prompts..."
                  value={promptSearch}
                  onChange={(e) => setPromptSearch(e.target.value)}
                  className="input w-64"
                />
                <button 
                  onClick={() => { setEditingPrompt(null); setPromptForm({ name: '', category: 'scene', template: '', variables: '', description: '', is_active: true }); setShowPromptModal(true); }}
                  className="btn-primary"
                >
                  <Plus className="w-4 h-4 mr-2" />
                  Add Prompt
                </button>
              </div>
            </div>
            
            {promptsLoading ? (
              <div className="card"><div className="flex justify-center py-12"><Loader2 className="w-8 h-8 animate-spin text-primary-600" /></div></div>
            ) : prompts.length === 0 ? (
              <div className="card">
                <div className="text-center py-12">
                  <Type className="w-12 h-12 text-slate-300 dark:text-slate-600 mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-slate-900 dark:text-white mb-2">No prompts yet</h3>
                  <p className="text-slate-500 dark:text-slate-400 mb-6">Create reusable prompt templates</p>
                  <button 
                    onClick={() => { setEditingPrompt(null); setPromptForm({ name: '', category: 'scene', template: '', variables: '', description: '', is_active: true }); setShowPromptModal(true); }}
                    className="btn-primary"
                  >
                    <Plus className="w-4 h-4 mr-2" />
                    Create First Prompt
                  </button>
                </div>
              </div>
            ) : (
              <div className="card">
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-slate-200 dark:border-slate-700">
                        <th className="text-left py-3 px-4 text-sm font-medium text-slate-500 dark:text-slate-400">Name</th>
                        <th className="text-left py-3 px-4 text-sm font-medium text-slate-500 dark:text-slate-400">Category</th>
                        <th className="text-left py-3 px-4 text-sm font-medium text-slate-500 dark:text-slate-400">Status</th>
                        <th className="text-left py-3 px-4 text-sm font-medium text-slate-500 dark:text-slate-400">Version</th>
                        <th className="text-left py-3 px-4 text-sm font-medium text-slate-500 dark:text-slate-400">Used</th>
                        <th className="text-left py-3 px-4 text-sm font-medium text-slate-500 dark:text-slate-400">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {prompts
                        .filter(p => 
                          (promptCategoryFilter === 'all' || p.category === promptCategoryFilter) &&
                          (promptSearch === '' || p.name.toLowerCase().includes(promptSearch.toLowerCase()))
                        )
                        .map((prompt) => (
                          <tr key={prompt.id} className="border-b border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/50">
                            <td className="py-3 px-4">
                              <div className="font-medium text-slate-900 dark:text-white">{prompt.name}</div>
                              {prompt.description && <div className="text-sm text-slate-500 dark:text-slate-400 truncate max-w-xs">{prompt.description}</div>}
                            </td>
                            <td className="py-3 px-4 text-sm text-slate-600 dark:text-slate-300 capitalize">{prompt.category?.replace('_', ' ') || '—'}</td>
                            <td className="py-3 px-4">
                              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                                prompt.is_active ? 'bg-green-100 text-green-800' : 'bg-slate-100 text-slate-800'
                              }`}>
                                {prompt.is_active ? 'Active' : 'Archived'}
                              </span>
                            </td>
                            <td className="py-3 px-4 text-sm text-slate-600 dark:text-slate-300">v{prompt.version}</td>
                            <td className="py-3 px-4 text-sm text-slate-600 dark:text-slate-300">{prompt.times_used}</td>
                            <td className="py-3 px-4">
                              <div className="flex items-center gap-2">
                                <button onClick={() => openEditPrompt(prompt)} className="btn-ghost p-1.5" title="Edit">
                                  <Edit className="w-4 h-4" />
                                </button>
                                <button onClick={() => handleDeletePrompt(prompt.id)} className="btn-ghost p-1.5 text-red-600 hover:text-red-700" title="Delete">
                                  <Trash2 className="w-4 h-4" />
                                </button>
                              </div>
                            </td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        );

      case 'google-accounts':
        return (
          <div className="space-y-6">
            <div className="flex items-center justify-between flex-wrap gap-4">
              <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Google Accounts</h2>
              <button 
                onClick={handleOAuthAuthorize}
                className="btn-primary"
                disabled={googleAccountsLoading}
              >
                <Layers className="w-4 h-4 mr-2" />
                Connect Google Account
              </button>
            </div>
            
            {googleAccountsLoading ? (
              <div className="card"><div className="flex justify-center py-12"><Loader2 className="w-8 h-8 animate-spin text-primary-600" /></div></div>
            ) : googleAccounts.length === 0 ? (
              <div className="card">
                <div className="text-center py-12">
                  <Layers className="w-12 h-12 text-slate-300 dark:text-slate-600 mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-slate-900 dark:text-white mb-2">No Google accounts connected</h3>
                  <p className="text-slate-500 dark:text-slate-400 mb-6">Connect up to 20 Google accounts for Flow Bridge integration</p>
                  <button 
                    onClick={handleOAuthAuthorize}
                    className="btn-primary"
                  >
                    <Layers className="w-4 h-4 mr-2" />
                    Connect First Account
                  </button>
                </div>
              </div>
            ) : (
              <div className="card">
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-slate-200 dark:border-slate-700">
                        <th className="text-left py-3 px-4 text-sm font-medium text-slate-500 dark:text-slate-400">Account</th>
                        <th className="text-left py-3 px-4 text-sm font-medium text-slate-500 dark:text-slate-400">Email</th>
                        <th className="text-left py-3 px-4 text-sm font-medium text-slate-500 dark:text-slate-400">Status</th>
                        <th className="text-left py-3 px-4 text-sm font-medium text-slate-500 dark:text-slate-400">Projects</th>
                        <th className="text-left py-3 px-4 text-sm font-medium text-slate-500 dark:text-slate-400">Last Verified</th>
                        <th className="text-left py-3 px-4 text-sm font-medium text-slate-500 dark:text-slate-400">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {googleAccounts.map((account) => (
                        <tr key={account.id} className="border-b border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/50">
                          <td className="py-3 px-4">
                            <div className="flex items-center gap-3">
                              {account.profile_picture ? (
                                <img src={account.profile_picture} alt="" className="w-8 h-8 rounded-full" />
                              ) : (
                                <div className="w-8 h-8 rounded-full bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center">
                                  <span className="text-sm font-medium text-primary-600 dark:text-primary-400">
                                    {account.display_name?.[0] || account.email[0].toUpperCase()}
                                  </span>
                                </div>
                              )}
                              <div>
                                <div className="font-medium text-slate-900 dark:text-white">{account.display_name || 'Unnamed'}</div>
                                <div className="text-xs text-slate-500 dark:text-slate-400">ID: {account.id.slice(0, 8)}...</div>
                              </div>
                            </div>
                          </td>
                          <td className="py-3 px-4 text-sm text-slate-600 dark:text-slate-300">{account.email}</td>
                          <td className="py-3 px-4">
                            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                              account.status === 'connected' ? 'bg-green-100 text-green-800' :
                              account.status === 'expired' ? 'bg-yellow-100 text-yellow-800' :
                              account.status === 'error' ? 'bg-red-100 text-red-800' :
                              'bg-slate-100 text-slate-800'
                            }`}>
                              {account.status}
                            </span>
                          </td>
                          <td className="py-3 px-4 text-sm text-slate-600 dark:text-slate-300">{account.projects_assigned}</td>
                          <td className="py-3 px-4 text-sm text-slate-600 dark:text-slate-300">
                            {account.last_verified_at ? formatDate(account.last_verified_at) : 'Never'}
                          </td>
                          <td className="py-3 px-4">
                            <div className="flex items-center gap-2">
                              {account.status !== 'connected' && (
                                <button 
                                  onClick={() => handleVerifyAccount(account.id)}
                                  className="btn-ghost p-1.5 text-sm" 
                                  title="Verify"
                                >
                                  <RefreshCw className="w-4 h-4" />
                                </button>
                              )}
                              <button 
                                onClick={() => handleRefreshAccount(account.id)}
                                className="btn-ghost p-1.5" 
                                title="Refresh Token"
                              >
                                <RefreshCw className="w-4 h-4" />
                              </button>
                              <button 
                                onClick={() => handleDeleteGoogleAccount(account.id)}
                                className="btn-ghost p-1.5 text-red-600 hover:text-red-700" 
                                title="Disconnect"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        );

      case 'flow-bridge':
        return (
          <div className="space-y-6">
            <div className="flex items-center justify-between flex-wrap gap-4">
              <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Flow Bridge</h2>
              <div className="flex items-center gap-2">
                <select value={flowTaskFilter} onChange={(e) => setFlowTaskFilter(e.target.value)} className="input w-auto">
                  <option value="all">All Tasks</option>
                  <option value="pending">Pending</option>
                  <option value="preparing">Preparing</option>
                  <option value="ready_for_generation">Ready for Generation</option>
                  <option value="generating">Generating</option>
                  <option value="waiting_for_import">Waiting for Import</option>
                  <option value="completed">Completed</option>
                  <option value="failed">Failed</option>
                </select>
                <button 
                  onClick={() => { setEditingFlowTask(null); setFlowTaskForm({ title: '', description: '', task_type: 'image_gen', input_prompts: '', input_references: '', input_parameters: '', priority: 0 }); setShowFlowTaskModal(true); }}
                  className="btn-primary"
                >
                  <Plus className="w-4 h-4 mr-2" />
                  Create Task
                </button>
              </div>
            </div>
            
            {(flowTasksLoading || flowAssetsLoading) ? (
              <div className="card"><div className="flex justify-center py-12"><Loader2 className="w-8 h-8 animate-spin text-primary-600" /></div></div>
            ) : (
              <>
                <p className="text-sm text-slate-500 dark:text-slate-400">Tugas di sini hanya pelacakan manual — eksekusi dilakukan langsung di Google Flow (tidak ada otomasi browser; mode mock dimatikan).</p>
                <div className="card">
                  <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">Tasks</h3>
                  {flowTasks.length === 0 ? (
                    <div className="text-center py-12">
                      <Zap className="w-12 h-12 text-slate-300 dark:text-slate-600 mx-auto mb-4" />
                      <h4 className="text-lg font-medium text-slate-900 dark:text-white mb-2">No tasks yet</h4>
                      <p className="text-slate-500 dark:text-slate-400 mb-6">Create tasks for asset generation</p>
                    </div>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full">
                        <thead>
                          <tr className="border-b border-slate-200 dark:border-slate-700">
                            <th className="text-left py-3 px-4 text-sm font-medium text-slate-500 dark:text-slate-400">Title</th>
                            <th className="text-left py-3 px-4 text-sm font-medium text-slate-500 dark:text-slate-400">Type</th>
                            <th className="text-left py-3 px-4 text-sm font-medium text-slate-500 dark:text-slate-400">Status</th>
                            <th className="text-left py-3 px-4 text-sm font-medium text-slate-500 dark:text-slate-400">Priority</th>
                            <th className="text-left py-3 px-4 text-sm font-medium text-slate-500 dark:text-slate-400">Created</th>
                            <th className="text-left py-3 px-4 text-sm font-medium text-slate-500 dark:text-slate-400">Actions</th>
                          </tr>
                        </thead>
                        <tbody>
                          {flowTasks
                            .filter(t => flowTaskFilter === 'all' || t.status === flowTaskFilter)
                            .map((task) => (
                              <tr key={task.id} className="border-b border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/50">
                                <td className="py-3 px-4">
                                  <div className="font-medium text-slate-900 dark:text-white">{task.title}</div>
                                  {task.description && <div className="text-sm text-slate-500 dark:text-slate-400 truncate max-w-xs">{task.description}</div>}
                                </td>
                                <td className="py-3 px-4 text-sm text-slate-600 dark:text-slate-300">{task.task_type || '—'}</td>
                                <td className="py-3 px-4">
                                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                                    task.status === 'completed' ? 'bg-green-100 text-green-800' :
                                    task.status === 'generating' ? 'bg-blue-100 text-blue-800' :
                                    task.status === 'failed' ? 'bg-red-100 text-red-800' :
                                    task.status === 'ready_for_generation' ? 'bg-yellow-100 text-yellow-800' :
                                    'bg-slate-100 text-slate-800'
                                  }`}>
                                    {task.status?.replace('_', ' ')}
                                  </span>
                                </td>
                                <td className="py-3 px-4 text-sm text-slate-600 dark:text-slate-300">{task.priority}</td>
                                <td className="py-3 px-4 text-sm text-slate-600 dark:text-slate-300">{formatDate(task.created_at)}</td>
                                <td className="py-3 px-4">
                                  <div className="flex items-center gap-2">
                                    <button onClick={() => openEditFlowTask(task)} className="btn-ghost p-1.5" title="Edit">
                                      <Edit className="w-4 h-4" />
                                    </button>
                                    <button onClick={() => handleDeleteFlowTask(task.id)} className="btn-ghost p-1.5 text-red-600 hover:text-red-700" title="Delete">
                                      <Trash2 className="w-4 h-4" />
                                    </button>
                                  </div>
                                </td>
                              </tr>
                            ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>

                <div className="card">
                  <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">Assets</h3>
                  {flowAssets.length === 0 ? (
                    <div className="text-center py-12">
                      <Image className="w-12 h-12 text-slate-300 dark:text-slate-600 mx-auto mb-4" />
                      <h4 className="text-lg font-medium text-slate-900 dark:text-white mb-2">No assets yet</h4>
                      <p className="text-slate-500 dark:text-slate-400">Generated assets will appear here</p>
                    </div>
                  ) : (
                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                      {flowAssets.map((asset) => (
                        <div key={asset.id} className="border border-slate-200 dark:border-slate-700 rounded-lg p-4 hover:border-primary-300 dark:hover:border-primary-700 transition-colors">
                          <div className="text-sm font-medium text-slate-900 dark:text-white truncate">{asset.title || 'Untitled'}</div>
                          <div className="text-xs text-slate-500 dark:text-slate-400 mb-2">{asset.asset_type?.replace('_', ' ')}</div>
                          {asset.file_url && (
                            <a href={asset.file_url} target="_blank" rel="noopener noreferrer" className="text-sm text-primary-600 hover:underline">
                              View Asset
                            </a>
                          )}
                          {asset.file_size && (
                            <div className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                              {(asset.file_size / 1024).toFixed(1)} KB
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </>
            )}
          </div>
        );

      case 'export':
        return (
          <div className="space-y-6">
            <div className="card">
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-6">Create Export</h3>
              <form onSubmit={handleExport} className="space-y-4 max-w-2xl">
                <div>
                  <label className="label">Export Type</label>
                  <select value={exportType} onChange={(e) => setExportType(e.target.value)} className="input">
                    <option value="project">Full Project</option>
                    <option value="episode">Episode</option>
                    <option value="prompts">Prompts</option>
                    <option value="series_bible">Series Bible</option>
                    <option value="characters">Characters</option>
                    <option value="locations">Locations</option>
                    <option value="scenes">Scenes</option>
                    <option value="full_project">Full Project (All Data)</option>
                  </select>
                </div>
                {exportType === 'episode' && (
                  <div>
                    <label className="label">Episode</label>
                    <select value={exportEpisodeId} onChange={(e) => setExportEpisodeId(e.target.value)} className="input">
                      <option value="">Select Episode</option>
                      {episodes.map((ep) => (
                        <option key={ep.id} value={ep.id}>Ep {ep.episode_number}: {ep.title || 'Untitled'}</option>
                      ))}
                    </select>
                  </div>
                )}
                <button type="submit" disabled={exporting} className="btn-primary">
                  {exporting ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Download className="w-4 h-4 mr-2" />} Create Export
                </button>
              </form>
            </div>

            <div className="card">
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-6">Export History</h3>
              {exportsLoading ? (
                <div className="flex justify-center py-12"><Loader2 className="w-8 h-8 animate-spin text-primary-600" /></div>
              ) : exports.length === 0 ? (
                <div className="text-center py-12">
                  <Download className="w-12 h-12 text-slate-300 dark:text-slate-600 mx-auto mb-4" />
                  <h4 className="text-lg font-medium text-slate-900 dark:text-white mb-2">No exports yet</h4>
                  <p className="text-slate-500 dark:text-slate-400">Create an export to see history here</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-slate-200 dark:border-slate-700">
                        <th className="text-left py-3 px-4 text-sm font-medium text-slate-500 dark:text-slate-400">Type</th>
                        <th className="text-left py-3 px-4 text-sm font-medium text-slate-500 dark:text-slate-400">Format</th>
                        <th className="text-left py-3 px-4 text-sm font-medium text-slate-500 dark:text-slate-400">Status</th>
                        <th className="text-left py-3 px-4 text-sm font-medium text-slate-500 dark:text-slate-400">Size</th>
                        <th className="text-left py-3 px-4 text-sm font-medium text-slate-500 dark:text-slate-400">Created</th>
                        <th className="text-left py-3 px-4 text-sm font-medium text-slate-500 dark:text-slate-400">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {exports.map((exp) => (
                        <tr key={exp.export_id} className="border-b border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/50">
                          <td className="py-3 px-4">
                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-primary-100 text-primary-800 dark:bg-primary-900/30 dark:text-primary-400">
                              {exp.export_type?.replace('_', ' ')}
                            </span>
                          </td>
                          <td className="py-3 px-4 text-sm text-slate-600 dark:text-slate-300">{exp.format?.toUpperCase()}</td>
                          <td className="py-3 px-4">
                            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                              exp.status === 'completed' ? 'bg-green-100 text-green-800' :
                              exp.status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
                              exp.status === 'processing' ? 'bg-blue-100 text-blue-800' :
                              'bg-red-100 text-red-800'
                            }`}>
                              {exp.status}
                            </span>
                          </td>
                          <td className="py-3 px-4 text-sm text-slate-600 dark:text-slate-300">
                            {exp.file_size ? `${(exp.file_size / 1024).toFixed(1)} KB` : '—'}
                          </td>
                          <td className="py-3 px-4 text-sm text-slate-600 dark:text-slate-300">{formatDate(exp.created_at)}</td>
                          <td className="py-3 px-4">
                            {exp.status === 'completed' && exp.file_url && (
                              <button 
                                onClick={() => handleDownloadExport(exp.export_id)}
                                className="btn-ghost p-1.5 text-primary-600 hover:text-primary-700" 
                                title="Download"
                              >
                                <Download className="w-4 h-4" />
                              </button>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        );

      case 'audit-logs':
        return (
          <div className="space-y-6">
            <div className="card">
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-6">Audit Logs</h3>
              <div className="flex items-center gap-4 mb-6">
                <input
                  type="text"
                  placeholder="Filter by action, resource, or error..."
                  value={auditLogFilter}
                  onChange={(e) => setAuditLogFilter(e.target.value)}
                  className="input w-96"
                />
              </div>
              {auditLogsLoading ? (
                <div className="flex justify-center py-12"><Loader2 className="w-8 h-8 animate-spin text-primary-600" /></div>
              ) : auditLogs.length === 0 ? (
                <div className="text-center py-12">
                  <Target className="w-12 h-12 text-slate-300 dark:text-slate-600 mx-auto mb-4" />
                  <h4 className="text-lg font-medium text-slate-900 dark:text-white mb-2">No audit logs</h4>
                  <p className="text-slate-500 dark:text-slate-400">Audit logs will appear here</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-slate-200 dark:border-slate-700">
                        <th className="text-left py-3 px-4 text-sm font-medium text-slate-500 dark:text-slate-400">Action</th>
                        <th className="text-left py-3 px-4 text-sm font-medium text-slate-500 dark:text-slate-400">Resource</th>
                        <th className="text-left py-3 px-4 text-sm font-medium text-slate-500 dark:text-slate-400">Status</th>
                        <th className="text-left py-3 px-4 text-sm font-medium text-slate-500 dark:text-slate-400">IP Address</th>
                        <th className="text-left py-3 px-4 text-sm font-medium text-slate-500 dark:text-slate-400">Time</th>
                      </tr>
                    </thead>
                    <tbody>
                      {auditLogs
                        .filter(log => 
                          auditLogFilter === '' || 
                          log.action.toLowerCase().includes(auditLogFilter.toLowerCase()) ||
                          log.resource_type?.toLowerCase().includes(auditLogFilter.toLowerCase()) ||
                          log.error_message?.toLowerCase().includes(auditLogFilter.toLowerCase())
                        )
                        .map((log) => (
                          <tr key={log.id} className="border-b border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/50">
                            <td className="py-3 px-4">
                              <span className="font-mono text-sm text-slate-900 dark:text-white">{log.action}</span>
                            </td>
                            <td className="py-3 px-4 text-sm text-slate-600 dark:text-slate-300">
                              {log.resource_type} {log.resource_id ? `(${log.resource_id.slice(0, 8)}...)` : ''}
                            </td>
                            <td className="py-3 px-4">
                              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${log.success ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                                {log.success ? 'Success' : 'Failed'}
                              </span>
                            </td>
                            <td className="py-3 px-4 text-sm text-slate-600 dark:text-slate-300">{log.ip_address || '—'}</td>
                            <td className="py-3 px-4 text-sm text-slate-600 dark:text-slate-300">{formatDate(log.created_at)}</td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        );

      case 'settings':
        return (
          <div className="card">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-6">Project Settings</h2>
            <form onSubmit={handleUpdateProject} className="space-y-4 max-w-2xl">
              <div>
                <label htmlFor="title" className="label">Title</label>
                <input
                  id="title"
                  type="text"
                  value={editTitle}
                  onChange={(e) => setEditTitle(e.target.value)}
                  className="input"
                  required
                />
              </div>
              <div>
                <label htmlFor="description" className="label">Description</label>
                <textarea
                  id="description"
                  value={editDescription}
                  onChange={(e) => setEditDescription(e.target.value)}
                  className="input"
                  rows={4}
                />
              </div>
              <div>
                <label htmlFor="genre" className="label">Genre</label>
                <input
                  id="genre"
                  type="text"
                  value={editGenre}
                  onChange={(e) => setEditGenre(e.target.value)}
                  className="input"
                  placeholder="Drama, Thriller, Romance, etc."
                />
              </div>
              <div className="flex justify-end gap-3 pt-4">
                <button type="button" onClick={() => setShowEditModal(false)} className="btn-secondary">Cancel</button>
                <button type="submit" disabled={isSaving} className="btn-primary">
                  {isSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4 mr-2" />} Save Changes
                </button>
              </div>
            </form>
            
            <div className="mt-8 pt-8 border-t border-slate-200 dark:border-slate-700">
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">Danger Zone</h3>
              <p className="text-slate-500 dark:text-slate-400 mb-4">Once deleted, this project and all its data cannot be recovered.</p>
              <button
                onClick={handleDeleteProject}
                className="btn-danger"
              >
                <Trash2 className="w-4 h-4 mr-2" />
                Delete Project
              </button>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900">
      <nav className="bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-4">
              <Link href="/dashboard" className="btn-ghost p-2">
                <ArrowLeft className="w-5 h-5" />
              </Link>
              <div>
                <h1 className="text-xl font-bold text-slate-900 dark:text-white">{project.title}</h1>
                <span className={`text-xs px-2 py-1 rounded-full ${
                  project.status === 'completed' ? 'bg-green-100 text-green-800' :
                  project.status === 'in_progress' ? 'bg-blue-100 text-blue-800' :
                  'bg-slate-100 text-slate-800'
                }`}>
                  {project.status.replace('_', ' ')}
                </span>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button onClick={openAutoGenerateModal} className="btn-primary" title="Generate the whole project with AI: bible, characters, locations, episodes and prompts">
                <Sparkles className="w-4 h-4 mr-2" />
                Auto-Generate
              </button>
            </div>
          </div>
          
          <div className="border-t border-slate-200 dark:border-slate-700">
            <nav className="flex overflow-x-auto" aria-label="Project tabs">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                    activeTab === tab.id
                      ? 'border-primary-600 text-primary-600'
                      : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300 dark:text-slate-400 dark:hover:text-slate-200'
                  }`}
                >
                  {tab.icon}
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {renderTabContent()}
      </main>

      {/* Auto-Generate modal (spec §6) */}
      {showAutoGenerateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-white dark:bg-slate-800 rounded-xl shadow-xl max-w-lg w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between">
              <h2 className="text-xl font-semibold text-slate-900 dark:text-white flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-primary-600" />
                Auto-Generate
              </h2>
              <button onClick={() => setShowAutoGenerateModal(false)} className="btn-ghost p-2" title="Close">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-4">
              {!autoGenJob && !autoGenSubmitting && (
                <form onSubmit={handleAutoGenerateSubmit} className="space-y-4">
                  <p className="text-sm text-slate-500 dark:text-slate-400">
                    AI fills the whole project for you: Series Bible, Characters, Locations,
                    Episodes and Prompts — in order, one job. Just give it a title.
                  </p>
                  <div>
                    <label htmlFor="autogen-title" className="label">Title *</label>
                    <input
                      id="autogen-title"
                      type="text"
                      value={autoGenForm.title}
                      onChange={(e) => setAutoGenForm({ ...autoGenForm, title: e.target.value })}
                      className="input"
                      placeholder="THE BILLIONAIRE CEO"
                      required
                    />
                  </div>
                  <div>
                    <label htmlFor="autogen-genre" className="label">Genre</label>
                    <input
                      id="autogen-genre"
                      type="text"
                      value={autoGenForm.genre}
                      onChange={(e) => setAutoGenForm({ ...autoGenForm, genre: e.target.value })}
                      className="input"
                      placeholder="Romance, Drama, Revenge…"
                    />
                  </div>
                  <div>
                    <label htmlFor="autogen-episodes" className="label">Total episodes</label>
                    <input
                      id="autogen-episodes"
                      type="number"
                      min={1}
                      max={60}
                      value={autoGenForm.total_episodes}
                      onChange={(e) => setAutoGenForm({ ...autoGenForm, total_episodes: e.target.value })}
                      className="input"
                    />
                  </div>
                  <div>
                    <label htmlFor="autogen-premise" className="label">Premise (optional)</label>
                    <textarea
                      id="autogen-premise"
                      value={autoGenForm.premise}
                      onChange={(e) => setAutoGenForm({ ...autoGenForm, premise: e.target.value })}
                      className="input"
                      rows={3}
                      placeholder="One or two sentences about the story…"
                    />
                  </div>
                  {autoGenError && (
                    <p className="text-sm text-red-600 flex items-start gap-2">
                      <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                      {autoGenError}
                    </p>
                  )}
                  <div className="flex justify-end gap-3">
                    <button type="button" onClick={() => setShowAutoGenerateModal(false)} className="btn-secondary">Cancel</button>
                    <button type="submit" className="btn-primary" disabled={!autoGenForm.title.trim()}>
                      <Sparkles className="w-4 h-4 mr-2" />
                      Start Auto-Generate
                    </button>
                  </div>
                </form>
              )}

              {autoGenSubmitting && (
                <div className="space-y-4">
                  <div className="flex items-center gap-3 text-slate-900 dark:text-white">
                    <Loader2 className="w-5 h-5 animate-spin text-primary-600" />
                    <p className="font-medium">Generating all 5 steps — this can take a few minutes.</p>
                  </div>
                  <p className="text-sm text-slate-500 dark:text-slate-400">
                    The AI is writing the bible, characters, locations, episodes and prompts.
                    Please keep this tab open.
                  </p>
                  <ul className="space-y-2">
                    {AUTO_GENERATE_STEP_ORDER.map((step) => (
                      <li key={step} className="flex items-center gap-3 text-sm text-slate-500 dark:text-slate-400">
                        <Clock className="w-4 h-4" />
                        {AUTO_GENERATE_STEP_LABELS[step]}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {autoGenJob && !autoGenSubmitting && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <p className="text-sm text-slate-500 dark:text-slate-400">
                      Job: <span className="font-medium text-slate-900 dark:text-white">{autoGenJob.title}</span>
                      {' '}· {autoGenJob.total_episodes} episodes
                    </p>
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      autoGenJob.status === 'completed' ? 'bg-green-100 text-green-800' :
                      autoGenJob.status === 'failed' ? 'bg-red-100 text-red-800' :
                      'bg-blue-100 text-blue-800'
                    }`}>{autoGenJob.status}</span>
                  </div>

                  {autoGenError && (
                    <p className="text-sm text-red-600 flex items-start gap-2">
                      <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                      {autoGenError}
                    </p>
                  )}
                  {autoGenJob.error_message && (
                    <p className="text-sm text-red-600">{autoGenJob.error_message}</p>
                  )}

                  <ul className="space-y-2">
                    {[...autoGenJob.steps].sort((a, b) => a.step_order - b.step_order).map((step) => (
                      <li key={step.id} className="border border-slate-200 dark:border-slate-700 rounded-lg p-3">
                        <div className="flex items-center justify-between gap-2">
                          <div className="flex items-center gap-3 text-sm">
                            {step.status === 'completed' && <CheckCircle className="w-4 h-4 text-green-600" />}
                            {step.status === 'failed' && <XCircle className="w-4 h-4 text-red-600" />}
                            {step.status === 'running' && <Loader2 className="w-4 h-4 animate-spin text-blue-600" />}
                            {step.status === 'pending' && <Clock className="w-4 h-4 text-slate-400" />}
                            <span className="font-medium text-slate-900 dark:text-white">
                              {AUTO_GENERATE_STEP_LABELS[step.step] || step.step}
                            </span>
                            <span className="text-slate-500 dark:text-slate-400 capitalize">{step.status}</span>
                          </div>
                          {step.status === 'failed' && (
                            <button
                              onClick={() => handleAutoGenRetry(step.step)}
                              disabled={autoGenRetrying !== null}
                              className="btn-secondary text-xs"
                            >
                              {autoGenRetrying === step.step
                                ? <Loader2 className="w-3 h-3 animate-spin mr-1" />
                                : <RefreshCw className="w-3 h-3 mr-1" />}
                              Retry
                            </button>
                          )}
                        </div>
                        {step.status === 'failed' && step.error_message && (
                          <p className="text-xs text-red-600 mt-2">{step.error_message}</p>
                        )}
                      </li>
                    ))}
                  </ul>

                  {autoGenJob.status === 'completed' && (
                    <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4">
                      <p className="text-sm font-medium text-green-800 dark:text-green-300 mb-3">
                        Done — everything is filled in. Open a tab to see the results:
                      </p>
                      <div className="flex flex-wrap gap-2">
                        <button onClick={() => openAutoGenResults('series-bible')} className="btn-secondary text-xs">Series Bible</button>
                        <button onClick={() => openAutoGenResults('characters')} className="btn-secondary text-xs">Characters</button>
                        <button onClick={() => openAutoGenResults('locations')} className="btn-secondary text-xs">Locations</button>
                        <button onClick={() => openAutoGenResults('episodes')} className="btn-secondary text-xs">Episodes</button>
                        <button onClick={() => openAutoGenResults('prompts')} className="btn-secondary text-xs">Prompts</button>
                      </div>
                    </div>
                  )}

                  <div className="flex justify-between gap-3 pt-2">
                    <button
                      onClick={handleAutoGenRefresh}
                      className="btn-ghost text-sm"
                      title="Re-fetch the latest job status from the server"
                    >
                      <RefreshCw className="w-4 h-4 mr-2" />
                      Refresh status
                    </button>
                    <div className="flex gap-3">
                      <button
                        onClick={() => { setAutoGenJob(null); setAutoGenError(''); }}
                        className="btn-secondary"
                      >
                        Start a new job
                      </button>
                      <button onClick={() => setShowAutoGenerateModal(false)} className="btn-primary">Close</button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}