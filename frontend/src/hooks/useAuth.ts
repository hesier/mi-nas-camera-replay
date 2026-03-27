import { useEffect, useState } from 'react';

import { getAuthStatus, login, logout } from '../api/auth';
import type { AuthStatus } from '../types/api';

interface UseAuthState {
  authenticated: boolean;
  error: string | null;
  loading: boolean;
  loginWithPassword: (password: string) => Promise<void>;
  refresh: () => Promise<void>;
  logoutCurrent: () => Promise<void>;
}

export function useAuth(): UseAuthState {
  const [status, setStatus] = useState<AuthStatus>({ authenticated: false });
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  async function refresh(): Promise<void> {
    setLoading(true);
    setError(null);
    try {
      const next = await getAuthStatus();
      setStatus(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : '获取登录状态失败');
    } finally {
      setLoading(false);
    }
  }

  async function loginWithPassword(password: string): Promise<void> {
    setLoading(true);
    setError(null);
    try {
      const next = await login(password);
      setStatus(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : '登录失败');
      throw err;
    } finally {
      setLoading(false);
    }
  }

  async function logoutCurrent(): Promise<void> {
    setLoading(true);
    setError(null);
    try {
      const next = await logout();
      setStatus(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : '退出登录失败');
      throw err;
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  return {
    authenticated: status.authenticated,
    error,
    loading,
    loginWithPassword,
    refresh,
    logoutCurrent,
  };
}
