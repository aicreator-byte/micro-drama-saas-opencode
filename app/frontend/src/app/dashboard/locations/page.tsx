'use client';

import { useState, useEffect } from 'react';
import { useProjectStore, useLocationStore } from '@/store';
import { locationsApi } from '@/lib/api';
import { Plus, Search, MoreVertical, Edit, Trash2, MapPin, MapPin as MapPinPlus } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

const locationSchema = z.object({
  name: z.string().min(1, 'Name is required').max(255),
  type: z.string().optional(),
  description: z.string().optional(),
  atmosphere: z.string().optional(),
  time_of_day: z.string().optional(),
  weather: z.string().optional(),
  consistency_instructions: z.string().optional(),
});

type LocationForm = z.infer<typeof locationSchema>;

export default function LocationsPage() {
  const { currentProject } = useProjectStore();
  const { locations, setLocations, addLocation, updateLocation, removeLocation } = useLocationStore();
  const [isLoading, setIsLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingLocation, setEditingLocation] = useState<typeof locations[0] | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<LocationForm>({
    resolver: zodResolver(locationSchema),
  });

  useEffect(() => {
    const loadLocations = async () => {
      if (!currentProject) {
        setLocations([]);
        setIsLoading(false);
        return;
      }
      setIsLoading(true);
      try {
        const response = await locationsApi.list(currentProject.id);
        setLocations(response.data);
      } catch (err) {
        console.error('Failed to load locations:', err);
      } finally {
        setIsLoading(false);
      }
    };
    loadLocations();
  }, [currentProject, setLocations]);

  const onSubmit = async (data: LocationForm) => {
    if (!currentProject) return;
    try {
      if (editingLocation) {
        const response = await locationsApi.update(currentProject.id, editingLocation.id, data);
        updateLocation(response.data.id, response.data);
      } else {
        const response = await locationsApi.create(currentProject.id, data);
        addLocation(response.data);
      }
      reset();
      setShowCreateModal(false);
      setEditingLocation(null);
    } catch (err) {
      console.error('Failed to save location:', err);
    }
  };

  const handleEdit = (location: typeof locations[0]) => {
    setEditingLocation(location);
    reset({
      name: location.name,
      type: location.type || '',
      description: location.description || '',
      atmosphere: location.atmosphere || '',
      time_of_day: location.time_of_day || '',
      weather: location.weather || '',
      consistency_instructions: location.consistency_instructions || '',
    });
    setShowCreateModal(true);
  };

  const handleDelete = async (id: string) => {
    if (!currentProject) return;
    try {
      await locationsApi.delete(currentProject.id, id);
      removeLocation(id);
      setDeleteConfirm(null);
    } catch (err) {
      console.error('Failed to delete location:', err);
    }
  };

  const filteredLocations = locations.filter((l) =>
    l.name.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-dark-900 dark:text-white">Locations</h1>
          <p className="text-dark-500 dark:text-dark-400 mt-1">Manage your shooting locations</p>
        </div>
        <button onClick={() => { reset(); setEditingLocation(null); setShowCreateModal(true); }} className="btn-primary" disabled={!currentProject}>
          <MapPinPlus className="w-4 h-4 mr-2" /> Add Location
        </button>
      </div>

      <div className="card p-4">
        <div className="relative max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-dark-400 w-5 h-5" />
          <input type="text" placeholder="Search locations..." value={search} onChange={(e) => setSearch(e.target.value)} className="input pl-10" />
        </div>
      </div>

      <div className="card overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center"><div className="animate-spin rounded-full h-12 w-12 border-4 border-primary-600 border-t-transparent mx-auto"></div></div>
        ) : !currentProject ? (
          <div className="p-12 text-center">
            <MapPin className="w-16 h-16 text-dark-300 dark:text-dark-600 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-dark-900 dark:text-white mb-2">No project selected</h3>
            <p className="text-dark-500 dark:text-dark-400">Select a project to manage locations</p>
          </div>
        ) : filteredLocations.length === 0 ? (
          <div className="p-12 text-center">
            <MapPin className="w-16 h-16 text-dark-300 dark:text-dark-600 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-dark-900 dark:text-white mb-2">{search ? 'No locations found' : 'No locations yet'}</h3>
            <p className="text-dark-500 dark:text-dark-400 mb-6">{search ? 'Try adjusting your search' : `Add locations to ${currentProject.title}`}</p>
            {!search && <button onClick={() => { reset(); setEditingLocation(null); setShowCreateModal(true); }} className="btn-primary"><MapPinPlus className="w-4 h-4 mr-2" /> Add Location</button>}
          </div>
        ) : (
          <div className="divide-y divide-dark-200 dark:divide-dark-800">
            {filteredLocations.map((location) => (
              <div key={location.id} className="p-4 hover:bg-dark-50 dark:hover:bg-dark-800/50 flex items-center justify-between">
                <div className="flex items-center gap-4 flex-1 min-w-0">
                  <div className="w-10 h-10 bg-green-100 dark:bg-green-900/30 rounded-lg flex items-center justify-center">
                    <MapPin className="w-5 h-5 text-green-600 dark:text-green-400" />
                  </div>
                  <div>
                    <h3 className="font-medium text-dark-900 dark:text-white truncate">{location.name}</h3>
                    <p className="text-sm text-dark-500 dark:text-dark-400">
                      {location.type || 'Location'} • {location.atmosphere || 'No atmosphere'}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-1">
                  <button onClick={() => handleEdit(location)} className="p-1.5 text-dark-400 hover:text-dark-600 hover:bg-dark-100 dark:hover:bg-dark-800 rounded transition-colors"><Edit className="w-4 h-4" /></button>
                  <button onClick={() => setDeleteConfirm(location.id)} className="p-1.5 text-dark-400 hover:text-red-600 hover:bg-dark-100 dark:hover:bg-dark-800 rounded transition-colors"><Trash2 className="w-4 h-4" /></button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {(showCreateModal || editingLocation) && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-white dark:bg-dark-900 rounded-xl shadow-xl max-w-md w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-dark-200 dark:border-dark-800 flex items-center justify-between">
              <h2 className="text-xl font-semibold text-dark-900 dark:text-white">{editingLocation ? 'Edit Location' : 'New Location'}</h2>
              <button onClick={() => { setShowCreateModal(false); setEditingLocation(null); reset(); }} className="p-1 text-dark-400 hover:text-dark-600"><X className="w-5 h-5" /></button>
            </div>
            <form onSubmit={handleSubmit(onSubmit)} className="p-6 space-y-4">
              <div><label htmlFor="name" className="label">Name *</label><input {...register('name')} id="name" className="input" placeholder="Location name" />{errors.name && <p className="mt-1 text-sm text-red-600">{errors.name.message}</p>}</div>
              <div><label htmlFor="type" className="label">Type</label><input {...register('type')} id="type" className="input" placeholder="Interior, Exterior, Studio" /></div>
              <div><label htmlFor="description" className="label">Description</label><textarea {...register('description')} id="description" rows={3} className="input" placeholder="Describe the location..." /></div>
              <div className="grid grid-cols-2 gap-4">
                <div><label htmlFor="atmosphere" className="label">Atmosphere</label><input {...register('atmosphere')} id="atmosphere" className="input" placeholder="Moody, Bright, Dark, etc." /></div>
                <div><label htmlFor="time_of_day" className="label">Time of Day</label><input {...register('time_of_day')} id="time_of_day" className="input" placeholder="Morning, Noon, Night" /></div>
              </div>
              <div><label htmlFor="weather" className="label">Weather</label><input {...register('weather')} id="weather" className="input" placeholder="Sunny, Rainy, Cloudy" /></div>
              <div><label htmlFor="consistency_instructions" className="label">Consistency Instructions</label><textarea {...register('consistency_instructions')} id="consistency_instructions" rows={2} className="input" placeholder="Visual consistency notes..." /></div>
              <div className="flex justify-end gap-3 pt-4">
                <button type="button" onClick={() => { setShowCreateModal(false); setEditingLocation(null); reset(); }} className="btn-secondary">Cancel</button>
                <button type="submit" className="btn-primary">{editingLocation ? 'Save Changes' : 'Create Location'}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {deleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-white dark:bg-dark-900 rounded-xl shadow-xl max-w-md w-full">
            <div className="p-6"><h3 className="text-lg font-semibold text-dark-900 dark:text-white mb-2">Delete Location</h3><p className="text-dark-500 dark:text-dark-400 mb-6">Are you sure? This action cannot be undone.</p><div className="flex justify-end gap-3"><button onClick={() => setDeleteConfirm(null)} className="btn-secondary">Cancel</button><button onClick={() => handleDelete(deleteConfirm)} className="btn-danger">Delete</button></div></div>
          </div>
        </div>
      )}
    </div>
  );
}

import { X } from 'lucide-react';