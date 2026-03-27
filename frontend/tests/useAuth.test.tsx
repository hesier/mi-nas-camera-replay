import { act, renderHook, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { useAuth } from '../src/hooks/useAuth';
import type { AuthStatus } from '../src/types/api';

const { getAuthStatusMock, loginMock, logoutMock } = vi.hoisted(() => ({
  getAuthStatusMock: vi.fn<Promise<AuthStatus>, []>(),
  loginMock: vi.fn<Promise<AuthStatus>, [string]>(),
  logoutMock: vi.fn<Promise<AuthStatus>, []>(),
}));

vi.mock('../src/api/auth', () => ({
  getAuthStatus: getAuthStatusMock,
  login: loginMock,
  logout: logoutMock,
}));

describe('useAuth', () => {
  it('ignores stale auth status refresh after login succeeds', async () => {
    let resolveRefresh: ((value: AuthStatus) => void) | null = null;
    getAuthStatusMock.mockImplementation(
      () =>
        new Promise<AuthStatus>((resolve) => {
          resolveRefresh = resolve;
        }),
    );
    loginMock.mockResolvedValue({ authenticated: true });
    logoutMock.mockResolvedValue({ authenticated: false });

    const { result } = renderHook(() => useAuth());

    await act(async () => {
      await result.current.loginWithPassword('secret-pass');
    });

    resolveRefresh?.({ authenticated: false });

    await waitFor(() => {
      expect(result.current.authenticated).toBe(true);
    });
  });
});
