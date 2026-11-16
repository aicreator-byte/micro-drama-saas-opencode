'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useAuthStore, useProjectStore, useCharacterStore, useLocationStore, useEpisodeStore, usePromptStore } from '@/store';
import { projectsApi, charactersApi, locationsApi, episodesApi, promptsApi } from '@/lib/api';
import { FolderKanban, Users, MapPin, Film, Clapperboard, Plus, ArrowRight, Clock, CheckCircle, AlertTriangle } from 'lucide-react';
import { Project, Episode, ProjectStatus, EpisodeStatus } from '@/types';
import { cn, formatRelativeTime } from '@/lib/utils';

export default function DashboardPage() {
  const { user } = useAuthStore();
  const { projects, currentProject, setCurrentProject } = useProjectStore();
  const { setCharacters } = useCharacterStore();
  const { setLocations } = useLocationStore();
  const { setEpisodes } = useEpisodeStore();
  const { setPrompts } = usePromptStore();
  const [stats, setStats] = useState({
    totalProjects: 0,
    activeProjects: 0,
    totalCharacters: 0,
    totalEpisodes: 0,
    completedEpisodes: 0,
  });
  const [recentProjects, setRecentProjects] = useState<typeof projects>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const loadDashboardData = async () => {
      setIsLoading(true);
      try {
        // Load projects
        const projectsResponse = await projectsApi.list({ page_size: 100 });
        const allProjects: Project[] = projectsResponse.data.projects;
        
        // Calculate stats
        const activeProjects = allProjects.filter(p => p.status === ProjectStatus.IN_PROGRESS).length;
        
        // Load data for current project if exists
        let totalCharacters = 0;
        let totalEpisodes = 0;
        let completedEpisodes = 0;
        
        if (currentProject) {
          try {
            const [charsRes, epsRes] = await Promise.all([
              charactersApi.list(currentProject.id),
              episodesApi.list(currentProject.id),
            ]);
            setCharacters(charsRes.data);
            totalCharacters = charsRes.data.length;
            totalEpisodes = epsRes.data.length;
            completedEpisodes = (epsRes.data as Episode[]).filter(e => e.status === EpisodeStatus.COMPLETED).length;
            
            // Load locations, prompts for current project
            const [locsRes, promptsRes] = await Promise.all([
              locationsApi.list(currentProject.id),
              promptsApi.list(currentProject.id),
            ]);
            setLocations(locsRes.data);
            setPrompts(promptsRes.data);
          } catch (err) {
            console.error('Failed to load project data:', err);
          }
        }
        
        setStats({
          totalProjects: allProjects.length,
          activeProjects,
          totalCharacters,
          totalEpisodes,
          completedEpisodes,
        });
        
        // Recent projects (last 5)
        setRecentProjects(allProjects.slice(0, 5));
      } catch (err) {
        console.error('Failed to load dashboard:', err);
      } finally {
        setIsLoading(false);
      }
    };
    
    loadDashboardData();
  }, [currentProject, setCharacters, setLocations, setEpisodes, setPrompts]);

  const handleProjectSelect = (project: typeof projects[0]) => {
    setCurrentProject(project);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-4 border-primary-600 border-t-transparent"></div>
      </div>
    );
  }

  const statCards = [
    { name: 'Total Projects', value: stats.totalProjects, icon: FolderKanban, color: 'text-blue-600 bg-blue-100 dark:bg-blue-900/30' },
    { name: 'Active Projects', value: stats.activeProjects, icon: FolderKanban, color: 'text-green-600 bg-green-100 dark:bg-green-900/30' },
    { name: 'Characters', value: stats.totalCharacters, icon: Users, color: 'text-purple-600 bg-purple-100 dark:bg-purple-900/30' },
    { name: 'Episodes', value: stats.totalEpisodes, icon: Film, color: 'text-orange-600 bg-orange-100 dark:bg-orange-900/30' },
    { name: 'Completed', value: stats.completedEpisodes, icon: CheckCircle, color: 'text-emerald-600 bg-emerald-100 dark:bg-emerald-900/30' },
  ];

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
      {/* Welcome header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-dark-900 dark:text-white">
            Welcome back, {user?.full_name?.split(' ')[0] || 'User'}!
          </h1>
          <p className="text-dark-500 dark:text-dark-400 mt-1">
            Here's an overview of your micro drama productions.
          </p>
        </div>
        <Link href="/dashboard/projects" className="btn-primary">
          <Plus className="w-4 h-4 mr-2" />
          New Project
        </Link>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
        {statCards.map((stat) => (
          <div key={stat.name} className="card p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-dark-500 dark:text-dark-400">{stat.name}</p>
                <p className="text-2xl font-bold text-dark-900 dark:text-white mt-1">{stat.value}</p>
              </div>
              <div className={cn('p-3 rounded-xl', stat.color)}>
                <stat.icon className="w-6 h-6" />
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Current project quick actions */}
      {currentProject && (
        <div className="card p-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-4">
            <div>
              <h2 className="text-lg font-semibold text-dark-900 dark:text-white">Current Project</h2>
              <p className="text-dark-500 dark:text-dark-400">{currentProject.title}</p>
            </div>
            <div className="flex items-center gap-2">
              <span className={cn('px-2 py-1 text-xs font-medium rounded-full', getStatusBadge(currentProject.status))}>
                {currentProject.status.replace('_', ' ')}
              </span>
            </div>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Link href="/dashboard/characters" className="btn-secondary w-full justify-center">
              <Users className="w-4 h-4 mr-2" />
              Characters
            </Link>
            <Link href="/dashboard/locations" className="btn-secondary w-full justify-center">
              <MapPin className="w-4 h-4 mr-2" />
              Locations
            </Link>
            <Link href="/dashboard/episodes" className="btn-secondary w-full justify-center">
              <Film className="w-4 h-4 mr-2" />
              Episodes
            </Link>
            <Link href="/dashboard/prompts" className="btn-secondary w-full justify-center">
              <Clapperboard className="w-4 h-4 mr-2" />
              Prompts
            </Link>
          </div>
        </div>
      )}

      {/* Recent projects */}
      <div className="card">
        <div className="p-4 border-b border-dark-200 dark:border-dark-800 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-dark-900 dark:text-white">Recent Projects</h2>
          <Link href="/dashboard/projects" className="text-sm text-primary-600 dark:text-primary-400 hover:underline">
            View all <ArrowRight className="w-4 h-4 inline ml-1" />
          </Link>
        </div>
        <div className="divide-y divide-dark-200 dark:divide-dark-800">
          {recentProjects.length === 0 ? (
            <div className="p-8 text-center">
              <FolderKanban className="w-12 h-12 text-dark-300 dark:text-dark-600 mx-auto mb-4" />
              <p className="text-dark-500 dark:text-dark-400">No projects yet</p>
              <Link href="/dashboard/projects" className="btn-primary mt-4 inline-flex">
                <Plus className="w-4 h-4 mr-2" />
                Create your first project
              </Link>
            </div>
          ) : (
            recentProjects.map((project) => (
              <Link
                key={project.id}
                href="/dashboard/projects"
                onClick={(e) => {
                  e.preventDefault();
                  handleProjectSelect(project);
                  window.location.href = '/dashboard/projects';
                }}
                className="flex items-center justify-between p-4 hover:bg-dark-50 dark:hover:bg-dark-800/50 transition-colors"
              >
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 bg-primary-100 dark:bg-primary-900/30 rounded-lg flex items-center justify-center">
                    <FolderKanban className="w-5 h-5 text-primary-600 dark:text-primary-400" />
                  </div>
                  <div>
                    <p className="font-medium text-dark-900 dark:text-white">{project.title}</p>
                    <p className="text-sm text-dark-500 dark:text-dark-400">
                      {project.genre || 'No genre'} • {project.total_episodes} episodes
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <span className={cn('px-2 py-1 text-xs font-medium rounded-full', getStatusBadge(project.status))}>
                    {project.status.replace('_', ' ')}
                  </span>
                  <span className="text-sm text-dark-500 dark:text-dark-400">
                    {formatRelativeTime(project.updated_at)}
                  </span>
                </div>
              </Link>
            ))
          )}
        </div>
      </div>
    </div>
  );
}