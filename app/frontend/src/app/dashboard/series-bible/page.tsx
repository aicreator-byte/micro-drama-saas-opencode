'use client';

import { useState, useEffect } from 'react';
import { useProjectStore } from '@/store';
import { seriesBibleApi } from '@/lib/api';
import { FileText, Edit, Save, X, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

const seriesBibleSchema = z.object({
  premise: z.string().optional(),
  main_plot: z.string().optional(),
  subplots: z.array(z.string()).optional(),
  character_relationships: z.string().optional(),
  world_settings: z.string().optional(),
  tone_and_visual_style: z.string().optional(),
  ending_direction: z.string().optional(),
  episode_structure: z.string().optional(),
});

type SeriesBibleForm = z.infer<typeof seriesBibleSchema>;

export default function SeriesBiblePage() {
  const { currentProject } = useProjectStore();
  const [isLoading, setIsLoading] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [bible, setBible] = useState<SeriesBibleForm | null>(null);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const {
    register,
    handleSubmit,
    reset,
    setValue,
    watch,
    formState: { errors },
  } = useForm<SeriesBibleForm>({
    resolver: zodResolver(seriesBibleSchema),
    defaultValues: {
      premise: '',
      main_plot: '',
      subplots: [],
      character_relationships: '',
      world_settings: '',
      tone_and_visual_style: '',
      ending_direction: '',
      episode_structure: '',
    },
  });

  const subplots = watch('subplots') || [];
  const [newSubplot, setNewSubplot] = useState('');

  useEffect(() => {
    const loadBible = async () => {
      if (!currentProject) {
        setBible(null);
        setIsLoading(false);
        return;
      }
      setIsLoading(true);
      try {
        const response = await seriesBibleApi.get(currentProject.id);
        setBible(response.data);
        reset(response.data);
      } catch (err: any) {
        if (err.response?.status !== 404) {
          setError('Failed to load series bible');
        }
      } finally {
        setIsLoading(false);
      }
    };
    loadBible();
  }, [currentProject, reset]);

  const addSubplot = () => {
    if (newSubplot.trim() && !subplots.includes(newSubplot.trim())) {
      setValue('subplots', [...subplots, newSubplot.trim()]);
      setNewSubplot('');
    }
  };

  const removeSubplot = (index: number) => {
    setValue('subplots', subplots.filter((_, i) => i !== index));
  };

  const onSubmit = async (data: SeriesBibleForm) => {
    if (!currentProject) return;
    setIsLoading(true);
    setError('');
    setSuccess('');
    try {
      if (bible) {
        await seriesBibleApi.update(currentProject.id, data);
      } else {
        await seriesBibleApi.create(currentProject.id, data);
      }
      setBible(data);
      setIsEditing(false);
      setSuccess('Series bible saved successfully');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save series bible');
    } finally {
      setIsLoading(false);
    }
  };

  const handleEdit = () => {
    if (bible) {
      reset(bible);
    }
    setIsEditing(true);
  };

  const handleCancel = () => {
    if (bible) {
      reset(bible);
    }
    setIsEditing(false);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-12 w-12 animate-spin text-primary-600" />
      </div>
    );
  }

  if (!currentProject) {
    return (
      <div className="text-center py-12">
        <FileText className="w-16 h-16 text-dark-300 dark:text-dark-600 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-dark-900 dark:text-white mb-2">No project selected</h3>
        <p className="text-dark-500 dark:text-dark-400">Select a project from the sidebar to manage the series bible</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-dark-900 dark:text-white">Series Bible</h1>
          <p className="text-dark-500 dark:text-dark-400 mt-1">
            {bible ? `Manage series bible for ${currentProject.title}` : `Create series bible for ${currentProject.title}`}
          </p>
        </div>
        {!bible && (
          <button
            onClick={() => setIsEditing(true)}
            className="btn-primary"
            disabled={isLoading}
          >
            <FileText className="w-4 h-4 mr-2" /> Create Series Bible
          </button>
        )}
      </div>

      {error && (
        <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-600 dark:text-red-400">
          {error}
        </div>
      )}

      {success && (
        <div className="p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg text-green-600 dark:text-green-400">
          {success}
        </div>
      )}

      <div className="card overflow-hidden">
        {!bible && !isEditing ? (
          <div className="p-12 text-center">
            <FileText className="w-16 h-16 text-dark-300 dark:text-dark-600 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-dark-900 dark:text-white mb-2">No series bible yet</h3>
            <p className="text-dark-500 dark:text-dark-400 mb-6">Create your series bible to define the core story elements</p>
            <button onClick={() => setIsEditing(true)} className="btn-primary">
              <FileText className="w-4 h-4 mr-2" /> Create Series Bible
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit(onSubmit)} className="p-6 space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-semibold text-dark-900 dark:text-white">
                {isEditing ? 'Edit Series Bible' : 'Series Bible'}
              </h2>
              {bible && !isEditing && (
                <button type="button" onClick={handleEdit} className="btn-secondary">
                  <Edit className="w-4 h-4 mr-2" /> Edit
                </button>
              )}
              {isEditing && (
                <div className="flex gap-2">
                  <button type="button" onClick={handleCancel} className="btn-secondary">
                    <X className="w-4 h-4 mr-2" /> Cancel
                  </button>
                  <button type="submit" className="btn-primary" disabled={isLoading}>
                    <Save className="w-4 h-4 mr-2" /> {isLoading ? 'Saving...' : 'Save'}
                  </button>
                </div>
              )}
            </div>

            <div className="space-y-6">
              <div>
                <label className="label">Premise</label>
                <textarea
                  {...register('premise')}
                  rows={3}
                  className="input"
                  placeholder="The core concept of your story in one or two sentences..."
                  disabled={!isEditing}
                />
                {errors.premise && <p className="mt-1 text-sm text-red-600">{errors.premise.message}</p>}
              </div>

              <div>
                <label className="label">Main Plot</label>
                <textarea
                  {...register('main_plot')}
                  rows={4}
                  className="input"
                  placeholder="Describe the main storyline..."
                  disabled={!isEditing}
                />
                {errors.main_plot && <p className="mt-1 text-sm text-red-600">{errors.main_plot.message}</p>}
              </div>

              <div>
                <label className="label">Subplots</label>
                <div className="space-y-2">
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={newSubplot}
                      onChange={(e) => setNewSubplot(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addSubplot())}
                      className="input flex-1"
                      placeholder="Add a subplot..."
                      disabled={!isEditing}
                    />
                    <button type="button" onClick={addSubplot} className="btn-secondary" disabled={!isEditing || !newSubplot.trim()}>
                      Add
                    </button>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {subplots.map((subplot, index) => (
                      <span key={index} className="px-3 py-1 bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-400 rounded-full text-sm flex items-center gap-1">
                        {subplot}
                        {isEditing && (
                          <button type="button" onClick={() => removeSubplot(index)} className="hover:text-primary-900 dark:hover:text-primary-200">
                            <X className="w-3 h-3" />
                          </button>
                        )}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              <div>
                <label className="label">Character Relationships</label>
                <textarea
                  {...register('character_relationships')}
                  rows={3}
                  className="input"
                  placeholder="Describe the key relationships between characters..."
                  disabled={!isEditing}
                />
              </div>

              <div>
                <label className="label">World Settings</label>
                <textarea
                  {...register('world_settings')}
                  rows={3}
                  className="input"
                  placeholder="Describe the world, setting, and rules..."
                  disabled={!isEditing}
                />
              </div>

              <div>
                <label className="label">Tone and Visual Style</label>
                <textarea
                  {...register('tone_and_visual_style')}
                  rows={3}
                  className="input"
                  placeholder="Describe the tone, mood, and visual aesthetic..."
                  disabled={!isEditing}
                />
              </div>

              <div>
                <label className="label">Ending Direction</label>
                <textarea
                  {...register('ending_direction')}
                  rows={3}
                  className="input"
                  placeholder="How does the story end? What is the ultimate resolution?"
                  disabled={!isEditing}
                />
              </div>

              <div>
                <label className="label">Episode Structure</label>
                <textarea
                  {...register('episode_structure')}
                  rows={3}
                  className="input"
                  placeholder="Describe the episode structure (e.g., 20 episodes, each revealing a piece of the puzzle)..."
                  disabled={!isEditing}
                />
              </div>
            </div>

            {isEditing && (
              <div className="flex justify-end gap-2 pt-4 border-t border-dark-200 dark:border-dark-800">
                <button type="button" onClick={handleCancel} className="btn-secondary">
                  <X className="w-4 h-4 mr-2" /> Cancel
                </button>
                <button type="submit" className="btn-primary" disabled={isLoading}>
                  <Save className="w-4 h-4 mr-2" /> {isLoading ? 'Saving...' : 'Save'}
                </button>
              </div>
            )}
          </form>
        )}
      </div>
    </div>
  );
}