'use client';

import { useState, useEffect } from 'react';
import { useProjectStore, usePromptStore } from '@/store';
import { promptsApi } from '@/lib/api';
import { Plus, Search, MoreVertical, Edit, Trash2, Copy, FileText, Download, ClipboardCheck } from 'lucide-react';
import { PromptType, PromptStatus } from '@/types';
import { cn } from '@/lib/utils';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

const promptSchema = z.object({
  prompt_type: z.nativeEnum(PromptType),
  title: z.string().optional(),
  prompt_text: z.string().min(1, 'Prompt text is required'),
  negative_prompt: z.string().optional(),
});

type PromptForm = z.infer<typeof promptSchema>;

export default function PromptsPage() {
  const { currentProject } = useProjectStore();
  const { prompts, setPrompts, addPrompt, updatePrompt, removePrompt } = usePromptStore();
  const [isLoading, setIsLoading] = useState(true);
  const [typeFilter, setTypeFilter] = useState<PromptType | 'all'>('all');
  const [statusFilter, setStatusFilter] = useState<PromptStatus | 'all'>('all');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingPrompt, setEditingPrompt] = useState<typeof prompts[0] | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<PromptForm>({
    resolver: zodResolver(promptSchema),
  });

  useEffect(() => {
    const loadPrompts = async () => {
      if (!currentProject) {
        setPrompts([]);
        setIsLoading(false);
        return;
      }
      setIsLoading(true);
      try {
        const response = await promptsApi.list(currentProject.id);
        setPrompts(response.data);
      } catch (err) {
        console.error('Failed to load prompts:', err);
      } finally {
        setIsLoading(false);
      }
    };
    loadPrompts();
  }, [currentProject, setPrompts]);

  const onSubmit = async (data: PromptForm) => {
    if (!currentProject) return;
    try {
      if (editingPrompt) {
        const response = await promptsApi.update(currentProject.id, editingPrompt.id, data);
        updatePrompt(response.data.id, response.data);
      } else {
        const response = await promptsApi.create(currentProject.id, data);
        addPrompt(response.data);
      }
      reset();
      setShowCreateModal(false);
      setEditingPrompt(null);
    } catch (err) {
      console.error('Failed to save prompt:', err);
    }
  };

  const handleEdit = (prompt: typeof prompts[0]) => {
    setEditingPrompt(prompt);
    reset({
      prompt_type: prompt.prompt_type,
      title: prompt.title || '',
      prompt_text: prompt.prompt_text,
      negative_prompt: prompt.negative_prompt || '',
    });
    setShowCreateModal(true);
  };

  const handleDelete = async (id: string) => {
    if (!currentProject) return;
    try {
      await promptsApi.delete(currentProject.id, id);
      removePrompt(id);
      setDeleteConfirm(null);
    } catch (err) {
      console.error('Failed to delete prompt:', err);
    }
  };

  const handleCopy = async (text: string, id: string) => {
    await navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleUse = async (id: string) => {
    if (!currentProject) return;
    try {
      await promptsApi.use(currentProject.id, id);
      const response = await promptsApi.list(currentProject.id);
      setPrompts(response.data);
    } catch (err) {
      console.error('Failed to mark prompt as used:', err);
    }
  };

  const filteredPrompts = prompts.filter((p) => {
    const matchesType = typeFilter === 'all' || p.prompt_type === typeFilter;
    const matchesStatus = statusFilter === 'all' || p.status === statusFilter;
    return matchesType && matchesStatus;
  });

  const getTypeLabel = (type: PromptType) => {
    const labels: Record<PromptType, string> = {
      [PromptType.CHARACTER_IMAGE]: 'Character Image',
      [PromptType.LOCATION_IMAGE]: 'Location Image',
      [PromptType.SCENE_IMAGE]: 'Scene Image',
      [PromptType.VIDEO_GENERATION]: 'Video Generation',
      [PromptType.CAMERA_MOVEMENT]: 'Camera Movement',
      [PromptType.CHARACTER_ACTION]: 'Character Action',
      [PromptType.DIALOGUE_AUDIO]: 'Dialogue Audio',
      [PromptType.SOUND_EFFECT]: 'Sound Effect',
      [PromptType.MUSIC]: 'Music',
    };
    return labels[type] || type;
  };

  const getStatusBadge = (status: PromptStatus) => {
    const variants: Record<PromptStatus, string> = {
      [PromptStatus.DRAFT]: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
      [PromptStatus.FINALIZED]: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
      [PromptStatus.USED]: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
      [PromptStatus.ARCHIVED]: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
    };
    return variants[status] || variants[PromptStatus.DRAFT];
  };

  const getTypeIcon = (type: PromptType) => {
    const icons: Record<PromptType, string> = {
      [PromptType.CHARACTER_IMAGE]: '👤',
      [PromptType.LOCATION_IMAGE]: '🏞️',
      [PromptType.SCENE_IMAGE]: '🎬',
      [PromptType.VIDEO_GENERATION]: '🎥',
      [PromptType.CAMERA_MOVEMENT]: '📷',
      [PromptType.CHARACTER_ACTION]: '🏃',
      [PromptType.DIALOGUE_AUDIO]: '🎙️',
      [PromptType.SOUND_EFFECT]: '🔊',
      [PromptType.MUSIC]: '🎵',
    };
    return icons[type] || '📝';
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-dark-900 dark:text-white">Prompts</h1>
          <p className="text-dark-500 dark:text-dark-400 mt-1">
            {currentProject ? `Manage prompts for ${currentProject.title}` : 'Select a project to manage prompts'}
          </p>
        </div>
        <button onClick={() => { reset(); setEditingPrompt(null); setShowCreateModal(true); }} className="btn-primary" disabled={!currentProject}>
          <Plus className="w-4 h-4 mr-2" /> New Prompt
        </button>
      </div>

      <div className="card p-4">
        <div className="flex flex-col sm:flex-row gap-4">
          <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value as any)} className="input w-auto">
            <option value="all">All Types</option>
            {Object.values(PromptType).map((type) => (
              <option key={type} value={type}>{getTypeLabel(type)}</option>
            ))}
          </select>
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value as any)} className="input w-auto">
            <option value="all">All Status</option>
            {Object.values(PromptStatus).map((status) => (
              <option key={status} value={status}>{status}</option>
            ))}
          </select>
          <div className="relative flex-1 sm:w-64">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-dark-400 w-5 h-5" />
            <input type="text" placeholder="Search prompts..." className="input pl-10" />
          </div>
        </div>
      </div>

      <div className="card overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center"><div className="animate-spin rounded-full h-12 w-12 border-4 border-primary-600 border-t-transparent mx-auto"></div></div>
        ) : !currentProject ? (
          <div className="p-12 text-center">
            <FileText className="w-16 h-16 text-dark-300 dark:text-dark-600 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-dark-900 dark:text-white mb-2">No project selected</h3>
            <p className="text-dark-500 dark:text-dark-400">Select a project to manage prompts</p>
          </div>
        ) : filteredPrompts.length === 0 ? (
          <div className="p-12 text-center">
            <FileText className="w-16 h-16 text-dark-300 dark:text-dark-600 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-dark-900 dark:text-white mb-2">No prompts found</h3>
            <p className="text-dark-500 dark:text-dark-400 mb-6">Create your first prompt</p>
            <button onClick={() => { reset(); setEditingPrompt(null); setShowCreateModal(true); }} className="btn-primary"><Plus className="w-4 h-4 mr-2" /> New Prompt</button>
          </div>
        ) : (
          <div className="divide-y divide-dark-200 dark:divide-dark-800">
            {filteredPrompts.map((prompt) => (
              <div key={prompt.id} className="p-4 hover:bg-dark-50 dark:hover:bg-dark-800/50">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-2">
                      <span className="text-2xl">{getTypeIcon(prompt.prompt_type)}</span>
                      <div>
                        <h3 className="font-medium text-dark-900 dark:text-white truncate">{prompt.title || 'Untitled Prompt'}</h3>
                        <div className="flex items-center gap-2 mt-1">
                          <span className="px-2 py-0.5 text-xs text-dark-500 dark:text-dark-400 bg-dark-100 dark:bg-dark-800 rounded">{getTypeLabel(prompt.prompt_type)}</span>
                          <span className={cn('px-2 py-0.5 text-xs font-medium rounded-full', getStatusBadge(prompt.status))}>
                            {prompt.status}
                          </span>
                          {prompt.version > 1 && (
                            <span className="px-2 py-0.5 text-xs text-dark-500 dark:text-dark-400 bg-dark-100 dark:bg-dark-800 rounded">v{prompt.version}</span>
                          )}
                        </div>
                      </div>
                    </div>
                    <div className="bg-dark-100 dark:bg-dark-800 rounded-lg p-3 max-h-32 overflow-auto font-mono text-sm text-dark-700 dark:text-dark-300 whitespace-pre-wrap">
                      {prompt.prompt_text}
                    </div>
                    {prompt.negative_prompt && (
                      <div className="mt-2 text-sm text-dark-500 dark:text-dark-400">
                        <span className="font-medium">Negative:</span> {prompt.negative_prompt}
                      </div>
                    )}
                  </div>
                  <div className="flex items-center gap-1 flex-shrink-0">
                    <button onClick={() => handleCopy(prompt.prompt_text, prompt.id)} className="p-2 text-dark-400 hover:text-dark-600 hover:bg-dark-100 dark:hover:bg-dark-800 rounded transition-colors" title={copiedId === prompt.id ? 'Copied!' : 'Copy'}>
                      {copiedId === prompt.id ? <ClipboardCheck className="w-5 h-5 text-green-500" /> : <Copy className="w-5 h-5" />}
                    </button>
                    {prompt.status !== PromptStatus.USED && (
                      <button onClick={() => handleUse(prompt.id)} className="p-2 text-dark-400 hover:text-green-600 hover:bg-dark-100 dark:hover:bg-dark-800 rounded transition-colors" title="Mark as Used">
                        <ClipboardCheck className="w-5 h-5" />
                      </button>
                    )}
                    <button onClick={() => handleEdit(prompt)} className="p-2 text-dark-400 hover:text-dark-600 hover:bg-dark-100 dark:hover:bg-dark-800 rounded transition-colors"><Edit className="w-4 h-4" /></button>
                    <button onClick={() => setDeleteConfirm(prompt.id)} className="p-2 text-dark-400 hover:text-red-600 hover:bg-dark-100 dark:hover:bg-dark-800 rounded transition-colors"><Trash2 className="w-4 h-4" /></button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {(showCreateModal || editingPrompt) && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-white dark:bg-dark-900 rounded-xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-dark-200 dark:border-dark-800 flex items-center justify-between">
              <h2 className="text-xl font-semibold text-dark-900 dark:text-white">{editingPrompt ? 'Edit Prompt' : 'New Prompt'}</h2>
              <button onClick={() => { setShowCreateModal(false); setEditingPrompt(null); reset(); }} className="p-1 text-dark-400 hover:text-dark-600"><X className="w-5 h-5" /></button>
            </div>
            <form onSubmit={handleSubmit(onSubmit)} className="p-6 space-y-4">
              <div><label className="label">Prompt Type *</label>
                <select {...register('prompt_type')} className="input">
                  {Object.values(PromptType).map((type) => <option key={type} value={type}>{getTypeLabel(type)}</option>)}
                </select>
                {errors.prompt_type && <p className="mt-1 text-sm text-red-600">{errors.prompt_type.message}</p>}
              </div>
              <div><label htmlFor="title" className="label">Title</label><input {...register('title')} id="title" className="input" placeholder="Optional title" /></div>
              <div><label htmlFor="prompt_text" className="label">Prompt Text *</label>
                <textarea {...register('prompt_text')} id="prompt_text" rows={6} className="input font-mono text-sm" placeholder="Enter your prompt..." />{errors.prompt_text && <p className="mt-1 text-sm text-red-600">{errors.prompt_text.message}</p>}</div>
              <div><label htmlFor="negative_prompt" className="label">Negative Prompt</label><textarea {...register('negative_prompt')} id="negative_prompt" rows={3} className="input font-mono text-sm" placeholder="Things to avoid..." /></div>
              <div className="flex justify-end gap-3 pt-4">
                <button type="button" onClick={() => { setShowCreateModal(false); setEditingPrompt(null); reset(); }} className="btn-secondary">Cancel</button>
                <button type="submit" className="btn-primary">{editingPrompt ? 'Save Changes' : 'Create Prompt'}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {deleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-white dark:bg-dark-900 rounded-xl shadow-xl max-w-md w-full">
            <div className="p-6"><h3 className="text-lg font-semibold text-dark-900 dark:text-white mb-2">Delete Prompt</h3><p className="text-dark-500 dark:text-dark-400 mb-6">Are you sure? This action cannot be undone.</p><div className="flex justify-end gap-3"><button onClick={() => setDeleteConfirm(null)} className="btn-secondary">Cancel</button><button onClick={() => handleDelete(deleteConfirm)} className="btn-danger">Delete</button></div></div>
          </div>
        </div>
      )}
    </div>
  );
}

import { X } from 'lucide-react';