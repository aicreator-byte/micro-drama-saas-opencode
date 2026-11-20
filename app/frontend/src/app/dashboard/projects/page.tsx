'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useProjectStore } from '@/store';
import { projectsApi, templatesApi } from '@/lib/api';
import { Plus, Search, Filter, MoreVertical, Edit, Trash2, FolderOpen, Eye, X, FolderKanban } from 'lucide-react';
import { ProjectStatus } from '@/types';
import { cn, formatDate } from '@/lib/utils';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

const projectSchema = z.object({
  title: z.string().min(1, 'Title is required').max(255),
  description: z.string().optional(),
  genre: z.string().optional(),
  themes: z.string().optional(),
  total_episodes: z.number().min(1).max(100).default(20),
});

type ProjectForm = z.infer<typeof projectSchema>;

interface ProjectTemplate {
  id: string;
  name: string;
  genre?: string | null;
  description?: string | null;
  total_episodes?: number | null;
}

export default function ProjectsPage() {
  const router = useRouter();
  const { projects, setProjects, currentProject, setCurrentProject, addProject, updateProject, removeProject } = useProjectStore();
  const [isLoading, setIsLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<ProjectStatus | 'all'>('all');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingProject, setEditingProject] = useState<typeof projects[0] | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  // Genre templates (GET /templates). Endpoint may not exist yet — on
  // 404/503 the picker hides itself and manual creation keeps working.
  const [templates, setTemplates] = useState<ProjectTemplate[]>([]);
  const [templatesState, setTemplatesState] = useState<'idle' | 'loading' | 'ready' | 'unavailable'>('idle');
  const [selectedTemplateId, setSelectedTemplateId] = useState('');
  const [templateError, setTemplateError] = useState('');
  const [templateCreating, setTemplateCreating] = useState(false);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
    setValue,
  } = useForm<ProjectForm>({
    resolver: zodResolver(projectSchema),
    defaultValues: {
      total_episodes: 20,
    },
  });

  useEffect(() => {
    const loadProjects = async () => {
      setIsLoading(true);
      try {
        const response = await projectsApi.list({ page_size: 100 });
        setProjects(response.data.projects);
      } catch (err) {
        console.error('Failed to load projects:', err);
      } finally {
        setIsLoading(false);
      }
    };
    loadProjects();
  }, [setProjects]);

  // Load genre templates when the create modal opens (create only).
  useEffect(() => {
    if (!showCreateModal || editingProject) return;
    let cancelled = false;
    setTemplatesState('loading');
    setTemplateError('');
    (async () => {
      try {
        const res = await templatesApi.list();
        if (!cancelled) {
          const list = Array.isArray(res.data) ? res.data : res.data?.templates ?? [];
          setTemplates(list);
          setTemplatesState('ready');
        }
      } catch {
        if (!cancelled) setTemplatesState('unavailable');
      }
    })();
    return () => { cancelled = true; };
  }, [showCreateModal, editingProject]);

  const handleCreateFromTemplate = async () => {
    if (!selectedTemplateId) return;
    setTemplateCreating(true);
    setTemplateError('');
    try {
      const res = await templatesApi.createFromTemplate({ template_id: selectedTemplateId });
      const created = res.data;
      if (created?.id) {
        addProject(created);
        reset();
        setShowCreateModal(false);
        router.push(`/projects/${created.id}`);
      } else {
        setTemplateError('Template created a project but returned no id.');
      }
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      setTemplateError(typeof detail === 'string' ? detail : 'Failed to create project from template.');
      console.error('Failed to create project from template:', err);
    } finally {
      setTemplateCreating(false);
    }
  };

  const onSubmit = async (data: ProjectForm) => {
    try {
      if (editingProject) {
        const response = await projectsApi.update(editingProject.id, {
          ...data,
          themes: data.themes ? data.themes.split(',').map(t => t.trim()) : [],
        });
        updateProject(response.data.id, response.data);
      } else {
        const response = await projectsApi.create({
          ...data,
          themes: data.themes ? data.themes.split(',').map(t => t.trim()) : [],
        });
        addProject(response.data);
      }
      reset();
      setShowCreateModal(false);
      setEditingProject(null);
    } catch (err) {
      console.error('Failed to save project:', err);
    }
  };

  const handleEdit = (project: typeof projects[0]) => {
    setEditingProject(project);
    reset({
      title: project.title,
      description: project.description || '',
      genre: project.genre || '',
      themes: project.themes?.join(', ') || '',
      total_episodes: project.total_episodes,
    });
    setShowCreateModal(true);
  };

  const handleDelete = async (id: string) => {
    try {
      await projectsApi.delete(id);
      removeProject(id);
      setDeleteConfirm(null);
    } catch (err) {
      console.error('Failed to delete project:', err);
    }
  };

  const handleSetCurrent = (project: typeof projects[0]) => {
    setCurrentProject(project);
  };

  const filteredProjects = projects.filter((project) => {
    const matchesSearch = project.title.toLowerCase().includes(search.toLowerCase()) ||
      project.description?.toLowerCase().includes(search.toLowerCase()) ||
      project.genre?.toLowerCase().includes(search.toLowerCase());
    const matchesStatus = statusFilter === 'all' || project.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const getStatusBadge = (status: ProjectStatus) => {
    const variants: Record<ProjectStatus, string> = {
      [ProjectStatus.DRAFT]: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
      [ProjectStatus.IN_PROGRESS]: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
      [ProjectStatus.COMPLETED]: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
      [ProjectStatus.ARCHIVED]: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
    };
    return variants[status] || variants[ProjectStatus.DRAFT];
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-dark-900 dark:text-white">Projects</h1>
          <p className="text-dark-500 dark:text-dark-400 mt-1">
            Manage your micro drama productions
          </p>
        </div>
        <button
          onClick={() => {
            reset();
            setEditingProject(null);
            setShowCreateModal(true);
          }}
          className="btn-primary"
        >
          <Plus className="w-4 h-4 mr-2" />
          New Project
        </button>
      </div>

      {/* Search and filters */}
      <div className="card p-4">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-dark-400 w-5 h-5" />
            <input
              type="text"
              placeholder="Search projects..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="input pl-10"
            />
          </div>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as any)}
            className="input w-auto"
          >
            <option value="all">All Status</option>
            <option value={ProjectStatus.DRAFT}>Draft</option>
            <option value={ProjectStatus.IN_PROGRESS}>In Progress</option>
            <option value={ProjectStatus.COMPLETED}>Completed</option>
            <option value={ProjectStatus.ARCHIVED}>Archived</option>
          </select>
        </div>
      </div>

      {/* Projects grid */}
      <div className="card overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-4 border-primary-600 border-t-transparent mx-auto"></div>
          </div>
        ) : filteredProjects.length === 0 ? (
          <div className="p-12 text-center">
            <FolderOpen className="w-16 h-16 text-dark-300 dark:text-dark-600 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-dark-900 dark:text-white mb-2">
              {search || statusFilter !== 'all' ? 'No projects found' : 'No projects yet'}
            </h3>
            <p className="text-dark-500 dark:text-dark-400 mb-6">
              {search || statusFilter !== 'all'
                ? 'Try adjusting your search or filters'
                : 'Create your first micro drama project'}
            </p>
            {!search && statusFilter === 'all' && (
              <button
                onClick={() => {
                  reset();
                  setEditingProject(null);
                  setShowCreateModal(true);
                }}
                className="btn-primary"
              >
                <Plus className="w-4 h-4 mr-2" />
                Create Project
              </button>
            )}
          </div>
        ) : (
          <div className="divide-y divide-dark-200 dark:divide-dark-800">
            {filteredProjects.map((project) => (
              <div key={project.id} className="p-4 hover:bg-dark-50 dark:hover:bg-dark-800/50 transition-colors">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4 flex-1 min-w-0">
                    <div className={cn(
                      'w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0',
                      currentProject?.id === project.id
                        ? 'bg-primary-100 dark:bg-primary-900/30'
                        : 'bg-dark-100 dark:bg-dark-800'
                    )}>
                      <FolderKanban className={cn(
                        'w-5 h-5',
                        currentProject?.id === project.id
                          ? 'text-primary-600 dark:text-primary-400'
                          : 'text-dark-500 dark:text-dark-400'
                      )} />
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <h3 className="font-medium text-dark-900 dark:text-white truncate">
                          {project.title}
                        </h3>
                        {currentProject?.id === project.id && (
                          <span className="px-2 py-0.5 text-xs font-medium bg-primary-100 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400 rounded">
                            Current
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-4 text-sm text-dark-500 dark:text-dark-400 mt-1">
                        {project.genre && <span>{project.genre}</span>}
                        <span>{project.total_episodes} episodes</span>
                        <span>Updated {formatDate(project.updated_at)}</span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={cn('px-2 py-1 text-xs font-medium rounded-full', getStatusBadge(project.status))}>
                      {project.status.replace('_', ' ')}
                    </span>
                    <div className="relative">
                      <button
                        className="p-2 text-dark-400 hover:text-dark-600 hover:bg-dark-100 dark:hover:bg-dark-800 rounded-lg transition-colors"
                      >
                        <MoreVertical className="w-5 h-5" />
                      </button>
                      <div className="absolute right-0 top-full mt-1 w-40 bg-white dark:bg-dark-800 rounded-lg shadow-lg border border-dark-200 dark:border-dark-700 py-1 z-10">
                        <button
                          onClick={() => handleSetCurrent(project)}
                          className="w-full px-4 py-2 text-left text-sm text-dark-700 dark:text-dark-300 hover:bg-dark-100 dark:hover:bg-dark-700 flex items-center gap-2"
                        >
                          <Eye className="w-4 h-4" />
                          Set as Current
                        </button>
                        <button
                          onClick={() => handleEdit(project)}
                          className="w-full px-4 py-2 text-left text-sm text-dark-700 dark:text-dark-300 hover:bg-dark-100 dark:hover:bg-dark-700 flex items-center gap-2"
                        >
                          <Edit className="w-4 h-4" />
                          Edit
                        </button>
                        <button
                          onClick={() => setDeleteConfirm(project.id)}
                          className="w-full px-4 py-2 text-left text-sm text-red-600 dark:text-red-400 hover:bg-dark-100 dark:hover:bg-dark-700 flex items-center gap-2"
                        >
                          <Trash2 className="w-4 h-4" />
                          Delete
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Create/Edit Modal */}
      {(showCreateModal || editingProject) && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-white dark:bg-dark-900 rounded-xl shadow-xl max-w-md w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-dark-200 dark:border-dark-800 flex items-center justify-between">
              <h2 className="text-xl font-semibold text-dark-900 dark:text-white">
                {editingProject ? 'Edit Project' : 'New Project'}
              </h2>
              <button
                onClick={() => {
                  setShowCreateModal(false);
                  setEditingProject(null);
                  reset();
                }}
                className="p-1 text-dark-400 hover:text-dark-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleSubmit(onSubmit)} className="p-6 space-y-4">
              <div>
                <label htmlFor="title" className="label">Title *</label>
                <input
                  {...register('title')}
                  id="title"
                  className="input"
                  placeholder="My Micro Drama Series"
                />
                {errors.title && <p className="mt-1 text-sm text-red-600">{errors.title.message}</p>}
              </div>
              <div>
                <label htmlFor="description" className="label">Description</label>
                <textarea
                  {...register('description')}
                  id="description"
                  rows={3}
                  className="input"
                  placeholder="Brief description of your series..."
                />
              </div>
              <div>
                <label htmlFor="genre" className="label">Genre</label>
                <input
                  {...register('genre')}
                  id="genre"
                  className="input"
                  placeholder="Romance, Thriller, Comedy, etc."
                />
              </div>
              <div>
                <label htmlFor="themes" className="label">Themes (comma separated)</label>
                <input
                  {...register('themes')}
                  id="themes"
                  className="input"
                  placeholder="Love, Betrayal, Redemption, Family"
                />
              </div>
              <div>
                <label htmlFor="total_episodes" className="label">Total Episodes</label>
                <input
                  {...register('total_episodes', { valueAsNumber: true })}
                  id="total_episodes"
                  type="number"
                  min="1"
                  max="100"
                  className="input"
                />
                {errors.total_episodes && <p className="mt-1 text-sm text-red-600">{errors.total_episodes.message}</p>}
              </div>
              {!editingProject && (
                <div>
                  <label htmlFor="template" className="label">Start from a genre template (optional)</label>
                  {templatesState === 'loading' && (
                    <p className="text-sm text-dark-500 dark:text-dark-400">Loading templates…</p>
                  )}
                  {templatesState === 'unavailable' && (
                    <p className="text-sm text-dark-500 dark:text-dark-400">
                      Templates belum tersedia — endpoint /templates belum aktif di backend. Buat proyek manual seperti biasa.
                    </p>
                  )}
                  {templatesState === 'ready' && templates.length === 0 && (
                    <p className="text-sm text-dark-500 dark:text-dark-400">No templates available yet.</p>
                  )}
                  {templatesState === 'ready' && templates.length > 0 && (
                    <>
                      <select
                        id="template"
                        value={selectedTemplateId}
                        onChange={(e) => setSelectedTemplateId(e.target.value)}
                        className="input"
                      >
                        <option value="">— No template (blank project) —</option>
                        {templates.map((t) => (
                          <option key={t.id} value={t.id}>
                            {t.name}{t.genre ? ` — ${t.genre}` : ''}
                          </option>
                        ))}
                      </select>
                      {selectedTemplateId && (
                        <div className="mt-2">
                          <p className="text-sm text-dark-500 dark:text-dark-400">
                            {templates.find((t) => t.id === selectedTemplateId)?.description || ''}
                          </p>
                          <button
                            type="button"
                            onClick={handleCreateFromTemplate}
                            disabled={templateCreating}
                            className="btn-primary mt-2"
                          >
                            {templateCreating ? 'Creating…' : 'Create Project from Template'}
                          </button>
                          {templateError && <p className="mt-1 text-sm text-red-600">{templateError}</p>}
                        </div>
                      )}
                    </>
                  )}
                </div>
              )}
              <div className="flex justify-end gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => {
                    setShowCreateModal(false);
                    setEditingProject(null);
                    reset();
                  }}
                  className="btn-secondary"
                >
                  Cancel
                </button>
                <button type="submit" className="btn-primary">
                  {editingProject ? 'Save Changes' : 'Create Project'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-white dark:bg-dark-900 rounded-xl shadow-xl max-w-md w-full">
            <div className="p-6">
              <h3 className="text-lg font-semibold text-dark-900 dark:text-white mb-2">Delete Project</h3>
              <p className="text-dark-500 dark:text-dark-400 mb-6">
                Are you sure you want to delete this project? This action cannot be undone.
              </p>
              <div className="flex justify-end gap-3">
                <button
                  onClick={() => setDeleteConfirm(null)}
                  className="btn-secondary"
                >
                  Cancel
                </button>
                <button
                  onClick={() => handleDelete(deleteConfirm)}
                  className="btn-danger"
                >
                  Delete
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}