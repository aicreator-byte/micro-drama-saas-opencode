'use client';

import { useState, useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import Link from 'next/link';
import { useAuthStore, useProjectStore, useUIStore } from '@/store';
import { authApi, projectsApi } from '@/lib/api';
import { LayoutDashboard, FolderKanban, Users, MapPin, Film, Clapperboard, Settings, LogOut, Menu, X, ChevronRight, FileText } from 'lucide-react';
import { cn } from '@/lib/utils';
import { ProjectStatus } from '@/types';

const navigation = [
  { name: 'Overview', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Projects', href: '/dashboard/projects', icon: FolderKanban },
  { name: 'Series Bible', href: '/dashboard/series-bible', icon: FileText },
  { name: 'Characters', href: '/dashboard/characters', icon: Users },
  { name: 'Locations', href: '/dashboard/locations', icon: MapPin },
  { name: 'Episodes', href: '/dashboard/episodes', icon: Film },
  { name: 'Prompts', href: '/dashboard/prompts', icon: Clapperboard },
  { name: 'Settings', href: '/dashboard/settings', icon: Settings },
];

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const { user, token, isAuthenticated, setAuth, clearAuth } = useAuthStore();
  const { projects, setProjects, currentProject, setCurrentProject } = useProjectStore();
  const { sidebarOpen, setSidebarOpen } = useUIStore();
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const initDashboard = async () => {
      if (!token) {
        router.push('/login');
        return;
      }
      if (!isAuthenticated && token) {
        try {
          const response = await authApi.getMe();
          setAuth(response.data, token);
        } catch {
          clearAuth();
          router.push('/login');
          return;
        }
      }
      // Load projects
      try {
        const response = await projectsApi.list({ page_size: 100 });
        setProjects(response.data.projects);
      } catch (err) {
        console.error('Failed to load projects:', err);
      } finally {
        setIsLoading(false);
      }
    };
    initDashboard();
  }, [token, isAuthenticated, setAuth, clearAuth, router, setProjects]);

  const handleLogout = async () => {
    try {
      await authApi.logout();
    } catch {
      // Ignore logout errors
    }
    clearAuth();
    router.push('/login');
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-4 border-primary-600 border-t-transparent"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-dark-50 dark:bg-dark-950">
      {/* Mobile sidebar overlay */}
      <div
        className={cn(
          'fixed inset-0 z-40 bg-black/50 transition-opacity lg:hidden',
          sidebarOpen ? 'opacity-100' : 'opacity-0 pointer-events-none'
        )}
        onClick={() => setSidebarOpen(false)}
      />

      {/* Sidebar */}
      <aside
        className={cn(
          'fixed lg:static inset-y-0 left-0 z-50 w-64 bg-white dark:bg-dark-900 border-r border-dark-200 dark:border-dark-800 transform transition-transform duration-200 flex flex-col',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        )}
      >
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className="p-4 border-b border-dark-200 dark:border-dark-800">
            <Link href="/dashboard" className="flex items-center gap-2">
              <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
                <Film className="w-5 h-5 text-white" />
              </div>
              <span className="text-xl font-bold text-dark-900 dark:text-white">Micro Drama</span>
            </Link>
          </div>

          {/* Navigation */}
          <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
            {navigation.map((item) => {
              const isActive = pathname === item.href || (item.href !== '/dashboard' && pathname.startsWith(item.href));
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={cn(
                    'sidebar-link',
                    isActive && 'sidebar-link-active'
                  )}
                >
                  <item.icon className="w-5 h-5" />
                  {item.name}
                </Link>
              );
            })}
          </nav>

          {/* Current Project */}
          {currentProject && (
            <div className="p-4 border-t border-dark-200 dark:border-dark-800">
              <p className="text-xs font-medium text-dark-500 dark:text-dark-400 uppercase tracking-wider mb-2">
                Current Project
              </p>
              <div className="flex items-center gap-3 p-3 bg-dark-50 dark:bg-dark-800 rounded-lg">
                <div className="w-8 h-8 bg-primary-100 dark:bg-primary-900/30 rounded-lg flex items-center justify-center">
                  <FolderKanban className="w-4 h-4 text-primary-600 dark:text-primary-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-dark-900 dark:text-white truncate">
                    {currentProject.title}
                  </p>
                  <p className="text-xs text-dark-500 dark:text-dark-400 capitalize">
                    {currentProject.status.replace('_', ' ')}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* User & Logout */}
          <div className="p-4 border-t border-dark-200 dark:border-dark-800">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-8 h-8 bg-primary-100 dark:bg-primary-900/30 rounded-full flex items-center justify-center">
                <span className="text-sm font-medium text-primary-600 dark:text-primary-400">
                  {user?.full_name?.charAt(0).toUpperCase() || user?.email?.charAt(0).toUpperCase()}
                </span>
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-dark-900 dark:text-white truncate">
                  {user?.full_name || 'User'}
                </p>
                <p className="text-xs text-dark-500 dark:text-dark-400 truncate">
                  {user?.email}
                </p>
              </div>
            </div>
            <button
              onClick={handleLogout}
              className="w-full flex items-center gap-3 px-3 py-2 text-dark-600 dark:text-dark-300 hover:bg-dark-100 dark:hover:bg-dark-800 rounded-lg transition-colors"
            >
              <LogOut className="w-5 h-5" />
              Sign out
            </button>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <div className="lg:pl-64 flex flex-col min-h-screen">
        {/* Top bar */}
        <header className="sticky top-0 z-30 bg-white/80 dark:bg-dark-900/80 backdrop-blur-sm border-b border-dark-200 dark:border-dark-800">
          <div className="flex items-center justify-between h-16 px-4 lg:px-6">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="lg:hidden p-2 text-dark-600 dark:text-dark-300 hover:bg-dark-100 dark:hover:bg-dark-800 rounded-lg"
            >
              <Menu className="w-6 h-6" />
            </button>
            <div className="flex-1 lg:flex-none">
              <h1 className="text-lg font-semibold text-dark-900 dark:text-white">
                {navigation.find((n) => pathname === n.href || (n.href !== '/dashboard' && pathname.startsWith(n.href)))?.name || 'Dashboard'}
              </h1>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 p-4 lg:p-6">
          {children}
        </main>
      </div>
    </div>
  );
}