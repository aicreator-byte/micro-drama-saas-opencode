'use client';

import { useState, useEffect } from 'react';
import { useProjectStore, useEpisodeStore } from '@/store';
import { episodesApi } from '@/lib/api';
import { Plus, Search, MoreVertical, Edit, Trash2, Film, FilePlus, ChevronRight, ChevronDown, Clapperboard, FileText } from 'lucide-react';
import { EpisodeStatus, SceneStatus } from '@/types';
import { cn, formatDate } from '@/lib/utils';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

const episodeSchema = z.object({
  episode_number: z.number().min(1).max(100),
  title: z.string().optional(),
  summary: z.string().optional(),
});

const sceneSchema = z.object({
  scene_number: z.number().min(1),
  title: z.string().optional(),
  description: z.string().optional(),
  location_id: z.string().optional(),
  time_of_day: z.string().optional(),
  action: z.string().optional(),
  dialogue: z.string().optional(),
});

type EpisodeForm = z.infer<typeof episodeSchema>;
type SceneForm = z.infer<typeof sceneSchema>;

export default function EpisodesPage() {
  const { currentProject } = useProjectStore();
  const { episodes, setEpisodes, currentEpisode, setCurrentEpisode, scenes, setScenes, addScene, updateScene, removeScene } = useEpisodeStore();
  const [isLoading, setIsLoading] = useState(true);
  const [showEpisodeModal, setShowEpisodeModal] = useState(false);
  const [editingEpisode, setEditingEpisode] = useState<typeof episodes[0] | null>(null);
  const [deleteEpisodeConfirm, setDeleteEpisodeConfirm] = useState<string | null>(null);
  const [showSceneModal, setShowSceneModal] = useState(false);
  const [editingScene, setEditingScene] = useState<typeof scenes[0] | null>(null);
  const [deleteSceneConfirm, setDeleteSceneConfirm] = useState<string | null>(null);
  const [expandedEpisode, setExpandedEpisode] = useState<string | null>(null);

  const {
    register: registerEpisode,
    handleSubmit: handleSubmitEpisode,
    reset: resetEpisode,
    formState: { errors: episodeErrors },
  } = useForm<EpisodeForm>({
    resolver: zodResolver(episodeSchema),
  });

  const {
    register: registerScene,
    handleSubmit: handleSubmitScene,
    reset: resetScene,
    formState: { errors: sceneErrors },
  } = useForm<SceneForm>({
    resolver: zodResolver(sceneSchema),
  });

  useEffect(() => {
    const loadEpisodes = async () => {
      if (!currentProject) {
        setEpisodes([]);
        setIsLoading(false);
        return;
      }
      setIsLoading(true);
      try {
        const response = await episodesApi.list(currentProject.id);
        setEpisodes(response.data);
      } catch (err) {
        console.error('Failed to load episodes:', err);
      } finally {
        setIsLoading(false);
      }
    };
    loadEpisodes();
  }, [currentProject, setEpisodes]);

  useEffect(() => {
    const loadScenes = async () => {
      if (!currentEpisode) {
        setScenes([]);
        return;
      }
      try {
        const response = await episodesApi.listScenes(currentProject!.id, currentEpisode.id);
        setScenes(response.data);
      } catch (err) {
        console.error('Failed to load scenes:', err);
      }
    };
    loadScenes();
  }, [currentEpisode, currentProject, setScenes]);

  const onSubmitEpisode = async (data: EpisodeForm) => {
    if (!currentProject) return;
    try {
      if (editingEpisode) {
        const response = await episodesApi.update(currentProject.id, editingEpisode.id, data);
        // updateEpisode would need to be added to store
      } else {
        const response = await episodesApi.create(currentProject.id, data);
        // addEpisode would need to be added to store
      }
      resetEpisode();
      setShowEpisodeModal(false);
      setEditingEpisode(null);
      // Reload episodes
      const response = await episodesApi.list(currentProject.id);
      setEpisodes(response.data);
    } catch (err) {
      console.error('Failed to save episode:', err);
    }
  };

  const onSubmitScene = async (data: SceneForm) => {
    if (!currentProject || !currentEpisode) return;
    try {
      if (editingScene) {
        const response = await episodesApi.updateScene(currentProject.id, currentEpisode.id, editingScene.id, data);
        updateScene(response.data.id, response.data);
      } else {
        const response = await episodesApi.createScene(currentProject.id, currentEpisode.id, data);
        addScene(response.data);
      }
      resetScene();
      setShowSceneModal(false);
      setEditingScene(null);
    } catch (err) {
      console.error('Failed to save scene:', err);
    }
  };

  const handleEditEpisode = (episode: typeof episodes[0]) => {
    setEditingEpisode(episode);
    resetEpisode({
      episode_number: episode.episode_number,
      title: episode.title || '',
      summary: episode.summary || '',
    });
    setShowEpisodeModal(true);
  };

  const handleDeleteEpisode = async (id: string) => {
    if (!currentProject) return;
    try {
      await episodesApi.delete(currentProject.id, id);
      // removeEpisode would need to be added to store
      setDeleteEpisodeConfirm(null);
      const response = await episodesApi.list(currentProject.id);
      setEpisodes(response.data);
    } catch (err) {
      console.error('Failed to delete episode:', err);
    }
  };

  const handleEditScene = (scene: typeof scenes[0]) => {
    setEditingScene(scene);
    resetScene({
      scene_number: scene.scene_number,
      title: scene.title || '',
      description: scene.description || '',
      location_id: scene.location_id || '',
      time_of_day: scene.time_of_day || '',
      action: scene.action || '',
      dialogue: scene.dialogue || '',
    });
    setShowSceneModal(true);
  };

  const handleDeleteScene = async (id: string) => {
    if (!currentProject || !currentEpisode) return;
    try {
      await episodesApi.deleteScene(currentProject.id, currentEpisode.id, id);
      removeScene(id);
      setDeleteSceneConfirm(null);
    } catch (err) {
      console.error('Failed to delete scene:', err);
    }
  };

  const getEpisodeStatusBadge = (status: EpisodeStatus) => {
    const variants: Record<EpisodeStatus, string> = {
      [EpisodeStatus.PLANNED]: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
      [EpisodeStatus.OUTLINED]: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
      [EpisodeStatus.SCENES_WRITTEN]: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
      [EpisodeStatus.PROMPTS_READY]: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
      [EpisodeStatus.IN_PRODUCTION]: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
      [EpisodeStatus.POST_PRODUCTION]: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400',
      [EpisodeStatus.COMPLETED]: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
    };
    return variants[status] || variants[EpisodeStatus.PLANNED];
  };

  const getSceneStatusBadge = (status: SceneStatus) => {
    const variants: Record<SceneStatus, string> = {
      [SceneStatus.PLANNED]: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
      [SceneStatus.WRITTEN]: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
      [SceneStatus.PROMPTS_READY]: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
      [SceneStatus.GENERATING]: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
      [SceneStatus.GENERATED]: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
      [SceneStatus.APPROVED]: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
      [SceneStatus.NEEDS_REVISION]: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
    };
    return variants[status] || variants[SceneStatus.PLANNED];
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-dark-900 dark:text-white">Episodes</h1>
          <p className="text-dark-500 dark:text-dark-400 mt-1">
            {currentProject ? `Manage episodes for ${currentProject.title}` : 'Select a project to manage episodes'}
          </p>
        </div>
        <button onClick={() => { resetEpisode(); setEditingEpisode(null); setShowEpisodeModal(true); }} className="btn-primary" disabled={!currentProject}>
          <FilePlus className="w-4 h-4 mr-2" /> Add Episode
        </button>
      </div>

      <div className="card overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center"><div className="animate-spin rounded-full h-12 w-12 border-4 border-primary-600 border-t-transparent mx-auto"></div></div>
        ) : !currentProject ? (
          <div className="p-12 text-center">
            <Film className="w-16 h-16 text-dark-300 dark:text-dark-600 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-dark-900 dark:text-white mb-2">No project selected</h3>
            <p className="text-dark-500 dark:text-dark-400">Select a project from the sidebar to manage episodes</p>
          </div>
        ) : episodes.length === 0 ? (
          <div className="p-12 text-center">
            <Film className="w-16 h-16 text-dark-300 dark:text-dark-600 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-dark-900 dark:text-white mb-2">No episodes yet</h3>
            <p className="text-dark-500 dark:text-dark-400 mb-6">Create your first episode for {currentProject.title}</p>
            <button onClick={() => { resetEpisode(); setEditingEpisode(null); setShowEpisodeModal(true); }} className="btn-primary"><FilePlus className="w-4 h-4 mr-2" /> Add Episode</button>
          </div>
        ) : (
          <div className="divide-y divide-dark-200 dark:divide-dark-800">
            {episodes.map((episode) => (
              <div key={episode.id} className="border-b border-dark-200 dark:border-dark-800 last:border-0">
                <button
                  onClick={() => setExpandedEpisode(expandedEpisode === episode.id ? null : episode.id)}
                  className="w-full p-4 flex items-center justify-between hover:bg-dark-50 dark:hover:bg-dark-800/50 transition-colors text-left"
                >
                  <div className="flex items-center gap-4 flex-1 min-w-0">
                    <div className="w-10 h-10 bg-primary-100 dark:bg-primary-900/30 rounded-lg flex items-center justify-center flex-shrink-0">
                      <span className="text-lg font-bold text-primary-600 dark:text-primary-400">Ep {episode.episode_number}</span>
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <h3 className="font-medium text-dark-900 dark:text-white truncate">{episode.title || 'Untitled'}</h3>
                        <span className={cn('px-2 py-0.5 text-xs font-medium rounded-full', getEpisodeStatusBadge(episode.status))}>
                          {episode.status.replace('_', ' ')}
                        </span>
                        {currentEpisode?.id === episode.id && (
                          <span className="px-2 py-0.5 text-xs font-medium bg-primary-100 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400 rounded">Current</span>
                        )}
                      </div>
                      <p className="text-sm text-dark-500 dark:text-dark-400 truncate">{episode.summary || 'No summary'}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={(e) => { e.stopPropagation(); setCurrentEpisode(episode); }}
                      className="p-2 text-dark-400 hover:text-dark-600 hover:bg-dark-100 dark:hover:bg-dark-800 rounded transition-colors"
                      title="View Scenes"
                    >
                      <Clapperboard className="w-5 h-5" />
                    </button>
                    <button onClick={(e) => { e.stopPropagation(); handleEditEpisode(episode); }} className="p-2 text-dark-400 hover:text-dark-600 hover:bg-dark-100 dark:hover:bg-dark-800 rounded transition-colors"><Edit className="w-4 h-4" /></button>
                    <button onClick={(e) => { e.stopPropagation(); setDeleteEpisodeConfirm(episode.id); }} className="p-2 text-dark-400 hover:text-red-600 hover:bg-dark-100 dark:hover:bg-dark-800 rounded transition-colors"><Trash2 className="w-4 h-4" /></button>
                    <ChevronDown className={cn('w-5 h-5 text-dark-400 transition-transform', expandedEpisode === episode.id && 'rotate-180')} />
                  </div>
                </button>

                {expandedEpisode === episode.id && (
                  <div className="bg-dark-50 dark:bg-dark-800/50 p-4 border-t border-dark-200 dark:border-dark-800">
                    <div className="flex items-center justify-between mb-3">
                      <h4 className="font-medium text-dark-900 dark:text-white">Scenes</h4>
                      <button
                        onClick={() => { resetScene(); setEditingScene(null); setShowSceneModal(true); }}
                        className="btn-secondary text-sm"
                        disabled={!currentEpisode}
                      >
                        <FilePlus className="w-4 h-4 mr-2" /> Add Scene
                      </button>
                    </div>
                    {scenes.length === 0 ? (
                      <p className="text-dark-500 dark:text-dark-400 text-center py-4">No scenes yet. Add your first scene.</p>
                    ) : (
                      <div className="space-y-2">
                        {scenes.map((scene) => (
                          <div key={scene.id} className="flex items-center justify-between p-3 bg-white dark:bg-dark-900 rounded-lg border border-dark-200 dark:border-dark-700">
                            <div className="flex items-center gap-3 flex-1 min-w-0">
                              <div className="w-8 h-8 bg-purple-100 dark:bg-purple-900/30 rounded-lg flex items-center justify-center flex-shrink-0">
                                <span className="text-sm font-bold text-purple-600 dark:text-purple-400">Sc {scene.scene_number}</span>
                              </div>
                              <div className="min-w-0">
                                <h5 className="font-medium text-dark-900 dark:text-white truncate">{scene.title || 'Untitled Scene'}</h5>
                                <p className="text-xs text-dark-500 dark:text-dark-400 truncate">{scene.description || 'No description'}</p>
                              </div>
                            </div>
                            <div className="flex items-center gap-2">
                              <span className={cn('px-2 py-0.5 text-xs font-medium rounded-full', getSceneStatusBadge(scene.status))}>
                                {scene.status.replace('_', ' ')}
                              </span>
                              <button onClick={(e) => { e.stopPropagation(); handleEditScene(scene); }} className="p-1.5 text-dark-400 hover:text-dark-600 hover:bg-dark-100 dark:hover:bg-dark-800 rounded"><Edit className="w-4 h-4" /></button>
                              <button onClick={(e) => { e.stopPropagation(); setDeleteSceneConfirm(scene.id); }} className="p-1.5 text-dark-400 hover:text-red-600 hover:bg-dark-100 dark:hover:bg-dark-800 rounded"><Trash2 className="w-4 h-4" /></button>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Episode Modal */}
      {(showEpisodeModal || editingEpisode) && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-white dark:bg-dark-900 rounded-xl shadow-xl max-w-md w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-dark-200 dark:border-dark-800 flex items-center justify-between">
              <h2 className="text-xl font-semibold text-dark-900 dark:text-white">{editingEpisode ? 'Edit Episode' : 'New Episode'}</h2>
              <button onClick={() => { setShowEpisodeModal(false); setEditingEpisode(null); resetEpisode(); }} className="p-1 text-dark-400 hover:text-dark-600"><X className="w-5 h-5" /></button>
            </div>
            <form onSubmit={handleSubmitEpisode(onSubmitEpisode)} className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div><label htmlFor="episode_number" className="label">Episode Number *</label><input {...registerEpisode('episode_number', { valueAsNumber: true })} id="episode_number" type="number" min="1" max="100" className="input" />{episodeErrors.episode_number && <p className="mt-1 text-sm text-red-600">{episodeErrors.episode_number.message}</p>}</div>
              </div>
              <div><label htmlFor="title" className="label">Title</label><input {...registerEpisode('title')} id="title" className="input" placeholder="Episode title" /></div>
              <div><label htmlFor="summary" className="label">Summary</label><textarea {...registerEpisode('summary')} id="summary" rows={3} className="input" placeholder="Brief summary of the episode..." /></div>
              <div className="flex justify-end gap-3 pt-4">
                <button type="button" onClick={() => { setShowEpisodeModal(false); setEditingEpisode(null); resetEpisode(); }} className="btn-secondary">Cancel</button>
                <button type="submit" className="btn-primary">{editingEpisode ? 'Save Changes' : 'Create Episode'}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Scene Modal */}
      {(showSceneModal || editingScene) && currentEpisode && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-white dark:bg-dark-900 rounded-xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-dark-200 dark:border-dark-800 flex items-center justify-between">
              <h2 className="text-xl font-semibold text-dark-900 dark:text-white">{editingScene ? 'Edit Scene' : 'New Scene'}</h2>
              <button onClick={() => { setShowSceneModal(false); setEditingScene(null); resetScene(); }} className="p-1 text-dark-400 hover:text-dark-600"><X className="w-5 h-5" /></button>
            </div>
            <form onSubmit={handleSubmitScene(onSubmitScene)} className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div><label htmlFor="scene_number" className="label">Scene Number *</label><input {...registerScene('scene_number', { valueAsNumber: true })} id="scene_number" type="number" min="1" className="input" />{sceneErrors.scene_number && <p className="mt-1 text-sm text-red-600">{sceneErrors.scene_number.message}</p>}</div>
              </div>
              <div><label htmlFor="title" className="label">Title</label><input {...registerScene('title')} id="title" className="input" placeholder="Scene title" /></div>
              <div><label htmlFor="description" className="label">Description</label><textarea {...registerScene('description')} id="description" rows={3} className="input" placeholder="Scene description..." /></div>
              <div className="grid grid-cols-2 gap-4">
                <div><label htmlFor="time_of_day" className="label">Time of Day</label><input {...registerScene('time_of_day')} id="time_of_day" className="input" placeholder="Morning, Noon, Night" /></div>
              </div>
              <div><label htmlFor="action" className="label">Action</label><textarea {...registerScene('action')} id="action" rows={3} className="input" placeholder="Describe the action..." /></div>
              <div><label htmlFor="dialogue" className="label">Dialogue (JSON format)</label><textarea {...registerScene('dialogue')} id="dialogue" rows={4} className="input font-mono text-sm" placeholder='[{"character": "John", "line": "Hello!"}]' /></div>
              <div className="flex justify-end gap-3 pt-4">
                <button type="button" onClick={() => { setShowSceneModal(false); setEditingScene(null); resetScene(); }} className="btn-secondary">Cancel</button>
                <button type="submit" className="btn-primary">{editingScene ? 'Save Changes' : 'Create Scene'}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirmations */}
      {deleteEpisodeConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-white dark:bg-dark-900 rounded-xl shadow-xl max-w-md w-full">
            <div className="p-6"><h3 className="text-lg font-semibold text-dark-900 dark:text-white mb-2">Delete Episode</h3><p className="text-dark-500 dark:text-dark-400 mb-6">Are you sure? This action cannot be undone.</p><div className="flex justify-end gap-3"><button onClick={() => setDeleteEpisodeConfirm(null)} className="btn-secondary">Cancel</button><button onClick={() => handleDeleteEpisode(deleteEpisodeConfirm)} className="btn-danger">Delete</button></div></div>
          </div>
        </div>
      )}
      {deleteSceneConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-white dark:bg-dark-900 rounded-xl shadow-xl max-w-md w-full">
            <div className="p-6"><h3 className="text-lg font-semibold text-dark-900 dark:text-white mb-2">Delete Scene</h3><p className="text-dark-500 dark:text-dark-400 mb-6">Are you sure? This action cannot be undone.</p><div className="flex justify-end gap-3"><button onClick={() => setDeleteSceneConfirm(null)} className="btn-secondary">Cancel</button><button onClick={() => handleDeleteScene(deleteSceneConfirm)} className="btn-danger">Delete</button></div></div>
          </div>
        </div>
      )}
    </div>
  );
}

import { X } from 'lucide-react';