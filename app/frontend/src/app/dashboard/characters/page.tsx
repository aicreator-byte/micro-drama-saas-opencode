'use client';

import { useState, useEffect } from 'react';
import { useProjectStore, useCharacterStore } from '@/store';
import { charactersApi } from '@/lib/api';
import { Plus, Search, MoreVertical, Edit, Trash2, User, UserPlus } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

const characterSchema = z.object({
  name: z.string().min(1, 'Name is required').max(255),
  role: z.string().optional(),
  age: z.string().optional(),
  gender: z.string().optional(),
  ethnicity: z.string().optional(),
  hair_color: z.string().optional(),
  eye_color: z.string().optional(),
  personality_traits: z.string().optional(),
  background: z.string().optional(),
  motivations: z.string().optional(),
  costume_style: z.string().optional(),
  consistency_instructions: z.string().optional(),
});

type CharacterForm = z.infer<typeof characterSchema>;

export default function CharactersPage() {
  const { currentProject } = useProjectStore();
  const { characters, setCharacters, addCharacter, updateCharacter, removeCharacter } = useCharacterStore();
  const [isLoading, setIsLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingCharacter, setEditingCharacter] = useState<typeof characters[0] | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<CharacterForm>({
    resolver: zodResolver(characterSchema),
  });

  useEffect(() => {
    const loadCharacters = async () => {
      if (!currentProject) {
        setCharacters([]);
        setIsLoading(false);
        return;
      }
      setIsLoading(true);
      try {
        const response = await charactersApi.list(currentProject.id);
        setCharacters(response.data);
      } catch (err) {
        console.error('Failed to load characters:', err);
      } finally {
        setIsLoading(false);
      }
    };
    loadCharacters();
  }, [currentProject, setCharacters]);

  const onSubmit = async (data: CharacterForm) => {
    if (!currentProject) return;
    try {
      const payload = {
        ...data,
        personality_traits: data.personality_traits ? data.personality_traits.split(',').map(t => t.trim()) : [],
      };
      if (editingCharacter) {
        const response = await charactersApi.update(currentProject.id, editingCharacter.id, payload);
        updateCharacter(response.data.id, response.data);
      } else {
        if (characters.length >= 6) {
          alert('Maximum of 6 characters allowed per project');
          return;
        }
        const response = await charactersApi.create(currentProject.id, payload);
        addCharacter(response.data);
      }
      reset();
      setShowCreateModal(false);
      setEditingCharacter(null);
    } catch (err) {
      console.error('Failed to save character:', err);
    }
  };

  const handleEdit = (character: typeof characters[0]) => {
    setEditingCharacter(character);
    reset({
      name: character.name,
      role: character.role || '',
      age: character.age || '',
      gender: character.gender || '',
      ethnicity: character.ethnicity || '',
      hair_color: character.hair_color || '',
      eye_color: character.eye_color || '',
      personality_traits: character.personality_traits?.join(', ') || '',
      background: character.background || '',
      motivations: character.motivations || '',
      costume_style: character.costume_style || '',
      consistency_instructions: character.consistency_instructions || '',
    });
    setShowCreateModal(true);
  };

  const handleDelete = async (id: string) => {
    if (!currentProject) return;
    try {
      await charactersApi.delete(currentProject.id, id);
      removeCharacter(id);
      setDeleteConfirm(null);
    } catch (err) {
      console.error('Failed to delete character:', err);
    }
  };

  const filteredCharacters = characters.filter((c) =>
    c.name.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-dark-900 dark:text-white">Characters</h1>
          <p className="text-dark-500 dark:text-dark-400 mt-1">
            Manage your cast of characters
          </p>
        </div>
        <button
          onClick={() => {
            reset();
            setEditingCharacter(null);
            setShowCreateModal(true);
          }}
          className="btn-primary"
          disabled={!currentProject || characters.length >= 6}
        >
          <UserPlus className="w-4 h-4 mr-2" />
          {characters.length >= 6 ? 'Max Characters (6)' : 'Add Character'}
        </button>
      </div>

      <div className="card p-4">
        <div className="relative max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-dark-400 w-5 h-5" />
          <input
            type="text"
            placeholder="Search characters..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="input pl-10"
          />
        </div>
      </div>

      <div className="card overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-4 border-primary-600 border-t-transparent mx-auto"></div>
          </div>
        ) : !currentProject ? (
          <div className="p-12 text-center">
            <User className="w-16 h-16 text-dark-300 dark:text-dark-600 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-dark-900 dark:text-white mb-2">No project selected</h3>
            <p className="text-dark-500 dark:text-dark-400">Select a project from the sidebar to manage characters</p>
          </div>
        ) : filteredCharacters.length === 0 ? (
          <div className="p-12 text-center">
            <User className="w-16 h-16 text-dark-300 dark:text-dark-600 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-dark-900 dark:text-white mb-2">
              {search ? 'No characters found' : 'No characters yet'}
            </h3>
            <p className="text-dark-500 dark:text-dark-400 mb-6">
              {search ? 'Try adjusting your search' : `Add up to 6 characters to ${currentProject.title}`}
            </p>
            {!search && characters.length < 6 && (
              <button
                onClick={() => {
                  reset();
                  setEditingCharacter(null);
                  setShowCreateModal(true);
                }}
                className="btn-primary"
              >
                <UserPlus className="w-4 h-4 mr-2" />
                Add Character
              </button>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 p-4">
            {filteredCharacters.map((character) => (
              <div key={character.id} className="bg-dark-50 dark:bg-dark-800/50 rounded-lg p-4 border border-dark-200 dark:border-dark-700">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 bg-primary-100 dark:bg-primary-900/30 rounded-full flex items-center justify-center">
                      <span className="text-lg font-medium text-primary-600 dark:text-primary-400">
                        {character.name.charAt(0).toUpperCase()}
                      </span>
                    </div>
                    <div>
                      <h3 className="font-medium text-dark-900 dark:text-white">{character.name}</h3>
                      {character.role && (
                        <p className="text-sm text-dark-500 dark:text-dark-400 capitalize">{character.role}</p>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => handleEdit(character)}
                      className="p-1.5 text-dark-400 hover:text-dark-600 hover:bg-dark-100 dark:hover:bg-dark-800 rounded transition-colors"
                    >
                      <Edit className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => setDeleteConfirm(character.id)}
                      className="p-1.5 text-dark-400 hover:text-red-600 hover:bg-dark-100 dark:hover:bg-dark-800 rounded transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
                {character.age && (
                  <p className="mt-3 text-sm text-dark-500 dark:text-dark-400">
                    <span className="font-medium">Age:</span> {character.age}
                  </p>
                )}
                {character.personality_traits && character.personality_traits.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-1">
                    {character.personality_traits.slice(0, 3).map((trait, i) => (
                      <span key={i} className="px-2 py-0.5 text-xs bg-primary-100 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400 rounded-full">
                        {trait}
                      </span>
                    ))}
                    {character.personality_traits.length > 3 && (
                      <span className="px-2 py-0.5 text-xs bg-dark-100 dark:bg-dark-800 text-dark-500 dark:text-dark-400 rounded-full">
                        +{character.personality_traits.length - 3}
                      </span>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Create/Edit Modal */}
      {(showCreateModal || editingCharacter) && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-white dark:bg-dark-900 rounded-xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-dark-200 dark:border-dark-800 flex items-center justify-between">
              <h2 className="text-xl font-semibold text-dark-900 dark:text-white">
                {editingCharacter ? 'Edit Character' : 'New Character'}
              </h2>
              <button
                onClick={() => {
                  setShowCreateModal(false);
                  setEditingCharacter(null);
                  reset();
                }}
                className="p-1 text-dark-400 hover:text-dark-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleSubmit(onSubmit)} className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label htmlFor="name" className="label">Name *</label>
                  <input {...register('name')} id="name" className="input" placeholder="Character name" />
                  {errors.name && <p className="mt-1 text-sm text-red-600">{errors.name.message}</p>}
                </div>
                <div>
                  <label htmlFor="role" className="label">Role</label>
                  <input {...register('role')} id="role" className="input" placeholder="Protagonist, Antagonist, Supporting" />
                </div>
                <div>
                  <label htmlFor="age" className="label">Age</label>
                  <input {...register('age')} id="age" className="input" placeholder="25" />
                </div>
                <div>
                  <label htmlFor="gender" className="label">Gender</label>
                  <input {...register('gender')} id="gender" className="input" placeholder="Male/Female/Other" />
                </div>
                <div>
                  <label htmlFor="ethnicity" className="label">Ethnicity</label>
                  <input {...register('ethnicity')} id="ethnicity" className="input" placeholder="Asian, Caucasian, etc." />
                </div>
                <div>
                  <label htmlFor="hair_color" className="label">Hair Color</label>
                  <input {...register('hair_color')} id="hair_color" className="input" placeholder="Black, Brown, Blonde" />
                </div>
                <div>
                  <label htmlFor="eye_color" className="label">Eye Color</label>
                  <input {...register('eye_color')} id="eye_color" className="input" placeholder="Brown, Blue, Green" />
                </div>
              </div>
              <div>
                <label htmlFor="personality_traits" className="label">Personality Traits (comma separated)</label>
                <input {...register('personality_traits')} id="personality_traits" className="input" placeholder="Brave, Cunning, Loyal" />
              </div>
              <div>
                <label htmlFor="background" className="label">Background</label>
                <textarea {...register('background')} id="background" rows={3} className="input" placeholder="Character backstory..." />
              </div>
              <div>
                <label htmlFor="motivations" className="label">Motivations</label>
                <textarea {...register('motivations')} id="motivations" rows={2} className="input" placeholder="What drives this character..." />
              </div>
              <div>
                <label htmlFor="costume_style" className="label">Costume Style</label>
                <input {...register('costume_style')} id="costume_style" className="input" placeholder="Modern, Period, Fantasy, etc." />
              </div>
              <div>
                <label htmlFor="consistency_instructions" className="label">Consistency Instructions</label>
                <textarea {...register('consistency_instructions')} id="consistency_instructions" rows={2} className="input" placeholder="Visual consistency notes for AI generation..." />
              </div>
              <div className="flex justify-end gap-3 pt-4">
                <button type="button" onClick={() => { setShowCreateModal(false); setEditingCharacter(null); reset(); }} className="btn-secondary">Cancel</button>
                <button type="submit" className="btn-primary">{editingCharacter ? 'Save Changes' : 'Create Character'}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirmation */}
      {deleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-white dark:bg-dark-900 rounded-xl shadow-xl max-w-md w-full">
            <div className="p-6">
              <h3 className="text-lg font-semibold text-dark-900 dark:text-white mb-2">Delete Character</h3>
              <p className="text-dark-500 dark:text-dark-400 mb-6">Are you sure? This action cannot be undone.</p>
              <div className="flex justify-end gap-3">
                <button onClick={() => setDeleteConfirm(null)} className="btn-secondary">Cancel</button>
                <button onClick={() => handleDelete(deleteConfirm)} className="btn-danger">Delete</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

import { X } from 'lucide-react';