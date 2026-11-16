'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { 
  ArrowLeft, Film, Users, MapPin, FileText, 
  Clapperboard, Settings, Plus, Edit, Trash2,
  ChevronRight, Loader2, Save, X
} from 'lucide-react';
import { api } from '@/lib/api';
import { useAuthStore } from '@/lib/auth-store';
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

type Tab = 'overview' | 'series-bible' | 'characters' | 'locations' | 'episodes' | 'prompts' | 'google-accounts' | 'flow-bridge' | 'settings';

const tabs: { id: Tab; label: string; icon: React.ReactNode }[] = [
  { id: 'overview', label: 'Overview', icon: <Film className="w-5 h-5" /> },
  { id: 'series-bible', label: 'Series Bible', icon: <FileText className="w-5 h-5" /> },
  { id: 'characters', label: 'Characters', icon: <Users className="w-5 h-5" /> },
  { id: 'locations', label: 'Locations', icon: <MapPin className="w-5 h-5" /> },
  { id: 'episodes', label: 'Episodes', icon: <Clapperboard className="w-5 h-5" /> },
  { id: 'prompts', label: 'Prompts', icon: <Settings className="w-5 h-5" /> },
  { id: 'google-accounts', label: 'Google Accounts', icon: <Settings className="w-5 h-5" /> },
  { id: 'flow-bridge', label: 'Flow Bridge', icon: <Settings className="w-5 h-5" /> },
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

  useEffect(() => {
    if (!isAuthenticated()) {
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

  const handleUpdateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    try {
      await api.put(`/projects/${projectId}`, {
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

  if (!isAuthenticated() || isLoading) {
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
          <div className="card">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Series Bible</h2>
              <button className="btn-primary" disabled>
                <Plus className="w-4 h-4 mr-2" />
                Create Series Bible
              </button>
            </div>
            <p className="text-slate-500 dark:text-slate-400 text-center py-12">
              Series Bible functionality coming soon...
            </p>
          </div>
        );

      case 'characters':
        return (
          <div className="card">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Characters</h2>
              <button className="btn-primary" disabled>
                <Plus className="w-4 h-4 mr-2" />
                Add Character
              </button>
            </div>
            <p className="text-slate-500 dark:text-slate-400 text-center py-12">
              Character Studio coming soon... (Max 6 characters per project)
            </p>
          </div>
        );

      case 'locations':
        return (
          <div className="card">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Locations</h2>
              <button className="btn-primary" disabled>
                <Plus className="w-4 h-4 mr-2" />
                Add Location
              </button>
            </div>
            <p className="text-slate-500 dark:text-slate-400 text-center py-12">
              Location Studio coming soon...
            </p>
          </div>
        );

      case 'episodes':
        return (
          <div className="card">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Episodes</h2>
              <button className="btn-primary" disabled>
                <Plus className="w-4 h-4 mr-2" />
                Add Episode
              </button>
            </div>
            <p className="text-slate-500 dark:text-slate-400 text-center py-12">
              Episode Manager coming soon... (20 episodes planned)
            </p>
          </div>
        );

      case 'prompts':
        return (
          <div className="card">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-6">Prompt Studio</h2>
            <p className="text-slate-500 dark:text-slate-400 text-center py-12">
              Prompt Studio coming soon...
            </p>
          </div>
        );

      case 'google-accounts':
        return (
          <div className="card">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-6">Google Accounts</h2>
            <p className="text-slate-500 dark:text-slate-400 text-center py-12">
              Google Account Manager coming soon... (Max 20 accounts)
            </p>
          </div>
        );

      case 'flow-bridge':
        return (
          <div className="card">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-6">Flow Bridge</h2>
            <p className="text-slate-500 dark:text-slate-400 text-center py-12">
              Flow Bridge integration coming soon...
            </p>
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
    </div>
  );
}