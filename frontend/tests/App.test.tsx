import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import App from '../src/App';
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

vi.mock('../src/pages/ReplayPage', () => ({
  ReplayPage: ({ onLogout }: { onLogout?: () => Promise<void> }) => (
    <div>
      <span>监控回放工作台</span>
      <button type="button" onClick={() => void onLogout?.()}>
        退出登录
      </button>
    </div>
  ),
}));

describe('App', () => {
  it('renders login page when auth status is false', async () => {
    getAuthStatusMock.mockResolvedValue({ authenticated: false });
    loginMock.mockResolvedValue({ authenticated: true });
    logoutMock.mockResolvedValue({ authenticated: false });

    render(<App />);

    expect(await screen.findByLabelText('访问密码')).toBeInTheDocument();
  });

  it('restores replay page after auth status confirms existing session', async () => {
    getAuthStatusMock.mockResolvedValue({ authenticated: true });
    loginMock.mockResolvedValue({ authenticated: true });
    logoutMock.mockResolvedValue({ authenticated: false });

    render(<App />);

    expect(await screen.findByText('监控回放工作台')).toBeInTheDocument();
  });

  it('returns to login page after logout succeeds', async () => {
    getAuthStatusMock.mockResolvedValue({ authenticated: true });
    loginMock.mockResolvedValue({ authenticated: true });
    logoutMock.mockResolvedValue({ authenticated: false });

    render(<App />);

    fireEvent.click(await screen.findByText('退出登录'));

    expect(await screen.findByLabelText('访问密码')).toBeInTheDocument();
  });
});
