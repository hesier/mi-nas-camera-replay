import { request } from './client';
import type { AuthStatus } from '../types/api';

export function login(password: string): Promise<AuthStatus> {
  return request<AuthStatus>('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ password }),
  });
}

export function logout(): Promise<AuthStatus> {
  return request<AuthStatus>('/api/auth/logout', {
    method: 'POST',
  });
}

export function getAuthStatus(): Promise<AuthStatus> {
  return request<AuthStatus>('/api/auth/status');
}
