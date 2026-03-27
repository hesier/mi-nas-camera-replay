import { useEffect, useRef, useState } from 'react';

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
  const requestIdRef = useRef(0);

  function beginRequest(): number {
    requestIdRef.current += 1;
    return requestIdRef.current;
  }

  function isCurrentRequest(requestId: number): boolean {
    return requestId === requestIdRef.current;
  }

  async function refresh(): Promise<void> {
    const requestId = beginRequest();
    setLoading(true);
    setError(null);
    try {
      const next = await getAuthStatus();
      if (isCurrentRequest(requestId)) {
        setStatus(next);
      }
    } catch (err) {
      if (isCurrentRequest(requestId)) {
        setError(err instanceof Error ? err.message : '获取登录状态失败');
      }
    } finally {
      if (isCurrentRequest(requestId)) {
        setLoading(false);
      }
    }
  }

  async function loginWithPassword(password: string): Promise<void> {
    const requestId = beginRequest();
    setLoading(true);
    setError(null);
    try {
      const next = await login(password);
      if (isCurrentRequest(requestId)) {
        setStatus(next);
      }
    } catch (err) {
      if (isCurrentRequest(requestId)) {
        setError(err instanceof Error ? err.message : '登录失败');
      }
      throw err;
    } finally {
      if (isCurrentRequest(requestId)) {
        setLoading(false);
      }
    }
  }

  async function logoutCurrent(): Promise<void> {
    const requestId = beginRequest();
    setLoading(true);
    setError(null);
    try {
      const next = await logout();
      if (isCurrentRequest(requestId)) {
        setStatus(next);
      }
    } catch (err) {
      if (isCurrentRequest(requestId)) {
        setError(err instanceof Error ? err.message : '退出登录失败');
      }
      throw err;
    } finally {
      if (isCurrentRequest(requestId)) {
        setLoading(false);
      }
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
