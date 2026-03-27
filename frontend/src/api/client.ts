function getApiBaseUrl(): string {
  return (import.meta.env.VITE_API_BASE_URL ?? '').trim();
}

export function resolveApiUrl(path: string, baseUrl: string = getApiBaseUrl()): string {
  if (path.length === 0) {
    return path;
  }

  if (/^https?:\/\//.test(path)) {
    return path;
  }

  if (baseUrl.length === 0) {
    return path;
  }

  return new URL(path, baseUrl).toString();
}

async function parseError(response: Response): Promise<string> {
  const contentType = response.headers.get('content-type') ?? '';
  if (contentType.includes('application/json')) {
    const payload = (await response.json()) as { detail?: string };
    if (typeof payload.detail === 'string' && payload.detail.length > 0) {
      return payload.detail;
    }
  }

  return `request failed: ${response.status}`;
}

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(resolveApiUrl(path), {
    credentials: 'include',
    ...init,
    headers: {
      Accept: 'application/json',
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    throw new Error(await parseError(response));
  }

  return (await response.json()) as T;
}
