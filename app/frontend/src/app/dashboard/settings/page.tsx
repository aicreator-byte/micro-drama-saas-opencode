'use client';

import { useState, useEffect } from 'react';
import { useAuthStore, useGoogleAccountStore } from '@/store';
import { authApi, googleAccountsApi, projectsApi } from '@/lib/api';
import { User, Mail, Lock, Key, Save, AlertCircle, CheckCircle, Plus, Trash2, Edit, ExternalLink, RefreshCw, Settings, Shield, Database, Cloud, Download } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

const profileSchema = z.object({
  full_name: z.string().min(1, 'Name is required').max(255),
  email: z.string().email('Invalid email'),
});

const passwordSchema = z.object({
  current_password: z.string().min(1, 'Current password is required'),
  new_password: z.string().min(8, 'Password must be at least 8 characters'),
  confirm_password: z.string(),
}).refine((data) => data.new_password === data.confirm_password, {
  message: 'Passwords do not match',
  path: ['confirm_password'],
});

const googleAccountSchema = z.object({
  email: z.string().email('Invalid email'),
  session_data: z.string().min(1, 'Session data is required'),
});

type ProfileForm = z.infer<typeof profileSchema>;
type PasswordForm = z.infer<typeof passwordSchema>;
type GoogleAccountForm = z.infer<typeof googleAccountSchema>;

export default function SettingsPage() {
  const { user, token, updateUser } = useAuthStore();
  const { accounts, setAccounts, addAccount, updateAccount, removeAccount } = useGoogleAccountStore();
  const [activeTab, setActiveTab] = useState<'profile' | 'security' | 'google' | 'data'>('profile');
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const profileForm = useForm<ProfileForm>({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      full_name: user?.full_name || '',
      email: user?.email || '',
    },
  });

  const passwordForm = useForm<PasswordForm>({
    resolver: zodResolver(passwordSchema),
  });

  const googleForm = useForm<GoogleAccountForm>({
    resolver: zodResolver(googleAccountSchema),
  });

  useEffect(() => {
    const loadGoogleAccounts = async () => {
      if (!token) return;
      try {
        const response = await googleAccountsApi.list();
        setAccounts(response.data);
      } catch (err) {
        console.error('Failed to load Google accounts:', err);
      }
    };
    loadGoogleAccounts();
  }, [token, setAccounts]);

  const showMessage = (type: 'success' | 'error', text: string) => {
    setMessage({ type, text });
    setTimeout(() => setMessage(null), 5000);
  };

  const handleProfileSubmit = async (data: ProfileForm) => {
    setIsLoading(true);
    try {
      // Backend doesn't have profile update endpoint yet, just update local state
      updateUser({ full_name: data.full_name, email: data.email });
      showMessage('success', 'Profile updated successfully');
    } catch (err) {
      showMessage('error', 'Failed to update profile');
    } finally {
      setIsLoading(false);
    }
  };

  const handlePasswordSubmit = async (data: PasswordForm) => {
    setIsLoading(true);
    try {
      // Backend doesn't have password change endpoint yet
      showMessage('success', 'Password change feature coming soon');
      passwordForm.reset();
    } catch (err) {
      showMessage('error', 'Failed to change password');
    } finally {
      setIsLoading(false);
    }
  };

  const handleGoogleSubmit = async (data: GoogleAccountForm) => {
    setIsLoading(true);
    try {
      const response = await googleAccountsApi.connect(data);
      addAccount(response.data);
      googleForm.reset();
      showMessage('success', 'Google account connected successfully');
    } catch (err: any) {
      showMessage('error', err.response?.data?.detail || 'Failed to connect Google account');
    } finally {
      setIsLoading(false);
    }
  };

  const handleGoogleDisconnect = async (id: string) => {
    if (!confirm('Are you sure you want to disconnect this Google account?')) return;
    setIsLoading(true);
    try {
      await googleAccountsApi.disconnect(id);
      removeAccount(id);
      showMessage('success', 'Google account disconnected');
    } catch (err) {
      showMessage('error', 'Failed to disconnect Google account');
    } finally {
      setIsLoading(false);
    }
  };

  const handleGoogleVerify = async (id: string) => {
    setIsLoading(true);
    try {
      await googleAccountsApi.verify(id);
      const response = await googleAccountsApi.list();
      setAccounts(response.data);
      showMessage('success', 'Account verified successfully');
    } catch (err) {
      showMessage('error', 'Failed to verify account');
    } finally {
      setIsLoading(false);
    }
  };

  const tabs = [
    { id: 'profile', label: 'Profile', icon: User },
    { id: 'security', label: 'Security', icon: Shield },
    { id: 'google', label: 'Google Accounts', icon: Cloud },
    { id: 'data', label: 'Data & Privacy', icon: Database },
  ];

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-dark-900 dark:text-white">Settings</h1>
        <p className="text-dark-500 dark:text-dark-400 mt-1">Manage your account settings and preferences</p>
      </div>

      {message && (
        <div className={cn(
          'p-4 rounded-lg flex items-center gap-3',
          message.type === 'success' 
            ? 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400 border border-green-200 dark:border-green-800'
            : 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 border border-red-200 dark:border-red-800'
        )}>
          {message.type === 'success' ? <CheckCircle className="w-5 h-5 flex-shrink-0" /> : <AlertCircle className="w-5 h-5 flex-shrink-0" />}
          <span>{message.text}</span>
        </div>
      )}

      {/* Tab Navigation */}
      <div className="card">
        <div className="border-b border-dark-200 dark:border-dark-800">
          <nav className="flex gap-1 p-1" aria-label="Settings tabs">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={cn(
                  'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors',
                  activeTab === tab.id
                    ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-400'
                    : 'text-dark-500 dark:text-dark-400 hover:text-dark-700 dark:hover:text-dark-200 hover:bg-dark-100 dark:hover:bg-dark-800'
                )}
              >
                <tab.icon className="w-4 h-4" />
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Tab Content */}
        <div className="p-6">
          {/* Profile Tab */}
          {activeTab === 'profile' && (
            <form onSubmit={profileForm.handleSubmit(handleProfileSubmit)} className="space-y-6">
              <div>
                <label className="label">Profile Information</label>
                <p className="text-sm text-dark-500 dark:text-dark-400">Update your personal information</p>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="full_name" className="label">Full Name</label>
                  <input
                    {...profileForm.register('full_name')}
                    id="full_name"
                    className="input"
                  />
                  {profileForm.formState.errors.full_name && (
                    <p className="mt-1 text-sm text-red-600">{profileForm.formState.errors.full_name.message}</p>
                  )}
                </div>
                <div>
                  <label htmlFor="email" className="label">Email</label>
                  <input
                    {...profileForm.register('email')}
                    id="email"
                    type="email"
                    className="input"
                    disabled
                  />
                  <p className="mt-1 text-sm text-dark-500 dark:text-dark-400">Email cannot be changed</p>
                </div>
              </div>
              <div className="pt-4 border-t border-dark-200 dark:border-dark-800">
                <button type="submit" className="btn-primary" disabled={isLoading}>
                  <Save className="w-4 h-4 mr-2" />
                  {isLoading ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            </form>
          )}

          {/* Security Tab */}
          {activeTab === 'security' && (
            <form onSubmit={passwordForm.handleSubmit(handlePasswordSubmit)} className="space-y-6">
              <div>
                <label className="label">Change Password</label>
                <p className="text-sm text-dark-500 dark:text-dark-400">Update your account password</p>
              </div>
              <div className="space-y-4">
                <div>
                  <label htmlFor="current_password" className="label">Current Password</label>
                  <input
                    {...passwordForm.register('current_password')}
                    id="current_password"
                    type="password"
                    className="input"
                  />
                </div>
                <div>
                  <label htmlFor="new_password" className="label">New Password</label>
                  <input
                    {...passwordForm.register('new_password')}
                    id="new_password"
                    type="password"
                    className="input"
                  />
                  {passwordForm.formState.errors.new_password && (
                    <p className="mt-1 text-sm text-red-600">{passwordForm.formState.errors.new_password.message}</p>
                  )}
                </div>
                <div>
                  <label htmlFor="confirm_password" className="label">Confirm New Password</label>
                  <input
                    {...passwordForm.register('confirm_password')}
                    id="confirm_password"
                    type="password"
                    className="input"
                  />
                  {passwordForm.formState.errors.confirm_password && (
                    <p className="mt-1 text-sm text-red-600">{passwordForm.formState.errors.confirm_password.message}</p>
                  )}
                </div>
              </div>
              <div className="pt-4 border-t border-dark-200 dark:border-dark-800">
                <button type="submit" className="btn-primary" disabled={isLoading}>
                  <Key className="w-4 h-4 mr-2" />
                  {isLoading ? 'Updating...' : 'Change Password'}
                </button>
              </div>
            </form>
          )}

          {/* Google Accounts Tab */}
          {activeTab === 'google' && (
            <div className="space-y-6">
              <div>
                <label className="label">Connected Google Accounts</label>
                <p className="text-sm text-dark-500 dark:text-dark-400">
                  Connect up to 20 Google accounts for Flow Bridge integration. Session data is encrypted.
                </p>
              </div>

              {/* Add Account Form */}
              <div className="card p-4 bg-primary-50 dark:bg-primary-900/20 border-primary-200 dark:border-primary-800">
                <h3 className="font-medium text-dark-900 dark:text-white mb-4">Add Google Account</h3>
                <form onSubmit={googleForm.handleSubmit(handleGoogleSubmit)} className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label htmlFor="google_email" className="label">Email</label>
                      <input
                        {...googleForm.register('email')}
                        id="google_email"
                        type="email"
                        className="input"
                        placeholder="account@gmail.com"
                      />
                    </div>
                  </div>
                  <div>
                    <label htmlFor="session_data" className="label">Session Data (Encrypted)</label>
                    <textarea
                      {...googleForm.register('session_data')}
                      id="session_data"
                      rows={4}
                      className="input font-mono text-sm"
                      placeholder="Paste exported session data (cookies, localStorage)..."
                    />
                    <p className="mt-1 text-sm text-dark-500 dark:text-dark-400">
                      Export your Google session using browser dev tools or a cookie editor extension.
                    </p>
                  </div>
                  <div className="pt-2">
                    <button type="submit" className="btn-primary" disabled={isLoading || accounts.length >= 20}>
                      <Plus className="w-4 h-4 mr-2" />
                      {isLoading ? 'Connecting...' : `Connect Account (${accounts.length}/20)`}
                    </button>
                    {accounts.length >= 20 && (
                      <p className="mt-2 text-sm text-red-600">Maximum of 20 accounts reached</p>
                    )}
                  </div>
                </form>
              </div>

              {/* Accounts List */}
              <div className="card overflow-hidden">
                {accounts.length === 0 ? (
                  <div className="p-12 text-center">
                    <Cloud className="w-16 h-16 text-dark-300 dark:text-dark-600 mx-auto mb-4" />
                    <h3 className="text-lg font-medium text-dark-900 dark:text-white mb-2">No Google accounts connected</h3>
                    <p className="text-dark-500 dark:text-dark-400">Add accounts above to use with Flow Bridge</p>
                  </div>
                ) : (
                  <div className="divide-y divide-dark-200 dark:divide-dark-800">
                    {accounts.map((account) => (
                      <div key={account.id} className="p-4 flex items-center justify-between hover:bg-dark-50 dark:hover:bg-dark-800/50">
                        <div className="flex items-center gap-4">
                          <div className="w-10 h-10 bg-primary-100 dark:bg-primary-900/30 rounded-full flex items-center justify-center">
                            <Mail className="w-5 h-5 text-primary-600 dark:text-primary-400" />
                          </div>
                          <div>
                            <h4 className="font-medium text-dark-900 dark:text-white">{account.email}</h4>
                            <div className="flex items-center gap-3 text-sm text-dark-500 dark:text-dark-400">
                              <span className={cn(
                                'px-2 py-0.5 rounded-full text-xs font-medium',
                                account.status === 'connected' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' :
                                account.status === 'expired' ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400' :
                                account.status === 'error' ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400' :
                                'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300'
                              )}>
                                {account.status}
                              </span>
                              {account.projects_assigned > 0 && (
                                <span>{account.projects_assigned} project(s)</span>
                              )}
                              {account.last_verified_at && (
                                <span>Verified {new Date(account.last_verified_at).toLocaleDateString()}</span>
                              )}
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => handleGoogleVerify(account.id)}
                            className="p-2 text-dark-400 hover:text-dark-600 hover:bg-dark-100 dark:hover:bg-dark-800 rounded transition-colors"
                            title="Verify"
                          >
                            <RefreshCw className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleGoogleDisconnect(account.id)}
                            className="p-2 text-dark-400 hover:text-red-600 hover:bg-dark-100 dark:hover:bg-dark-800 rounded transition-colors"
                            title="Disconnect"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Data & Privacy Tab */}
          {activeTab === 'data' && (
            <div className="space-y-6">
              <div className="card p-6">
                <h3 className="font-medium text-dark-900 dark:text-white mb-4">Data Export</h3>
                <p className="text-dark-500 dark:text-dark-400 mb-4">Download all your project data in JSON format.</p>
                <button className="btn-secondary">
                  <Download className="w-4 h-4 mr-2" />
                  Export Data
                </button>
              </div>

              <div className="card p-6">
                <h3 className="font-medium text-dark-900 dark:text-white mb-4">Account Deletion</h3>
                <p className="text-dark-500 dark:text-dark-400 mb-4">
                  Permanently delete your account and all associated data. This action cannot be undone.
                </p>
                <button className="btn-danger">
                  <Trash2 className="w-4 h-4 mr-2" />
                  Delete Account
                </button>
              </div>

              <div className="card p-6">
                <h3 className="font-medium text-dark-900 dark:text-white mb-4">API Access</h3>
                <p className="text-dark-500 dark:text-dark-400 mb-4">
                  Manage API tokens for programmatic access.
                </p>
                <button className="btn-secondary">
                  <Key className="w-4 h-4 mr-2" />
                  Manage API Tokens
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}