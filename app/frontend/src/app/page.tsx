'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store';
import { authApi } from '@/lib/api';

export default function Home() {
  const router = useRouter();
  const { isAuthenticated, token, setAuth } = useAuthStore();

  useEffect(() => {
    const initAuth = async () => {
      if (token && !isAuthenticated) {
        try {
          const response = await authApi.getMe();
          setAuth(response.data, token);
          router.push('/dashboard');
        } catch {
          // Token invalid, redirect to login
          router.push('/login');
        }
      } else if (isAuthenticated) {
        router.push('/dashboard');
      } else {
        router.push('/login');
      }
    };
    initAuth();
  }, [isAuthenticated, token, setAuth, router]);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="animate-spin rounded-full h-12 w-12 border-4 border-primary-600 border-t-transparent"></div>
    </div>
  );
}