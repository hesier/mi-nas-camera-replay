import { afterEach, describe, expect, it, vi } from 'vitest';

import { getAuthStatus } from './auth';
import { listCameras } from './cameras';
import { getTimeline, listDays, locateAt } from './replay';

const originalFetch = globalThis.fetch;

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllEnvs();
  globalThis.fetch = originalFetch;
});

describe('replay api', () => {
  it('maps day summary payload from listDays', async () => {
    globalThis.fetch = vi.fn(async () =>
      new Response(
        JSON.stringify([
          {
            day: '2026-03-20',
            segmentCount: 12,
            recordedSeconds: 7200,
            gapSeconds: 40,
            hasWarning: true,
            firstSegmentAt: '2026-03-20T00:00:00+08:00',
            lastSegmentAt: '2026-03-20T23:59:59+08:00',
          },
        ]),
        {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        },
      ),
    ) as typeof fetch;

    const days = await listDays(1);

    expect(days[0].day).toBe('2026-03-20');
    expect(days[0].segmentCount).toBe(12);
    expect(days[0].hasWarning).toBe(true);
    expect(globalThis.fetch).toHaveBeenCalledWith('/api/days?camera=1', {
      headers: {
        Accept: 'application/json',
      },
      credentials: 'include',
    });
  });

  it('passes camera query when requesting days', async () => {
    globalThis.fetch = vi.fn(async () =>
      new Response(JSON.stringify([]), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    ) as typeof fetch;

    await listDays(2);

    expect(globalThis.fetch).toHaveBeenCalledWith('/api/days?camera=2', {
      credentials: 'include',
      headers: { Accept: 'application/json' },
    });
  });

  it('passes day query when requesting timeline', async () => {
    globalThis.fetch = vi.fn(async () =>
      new Response(
        JSON.stringify({
          day: '2026-03-20',
          timezone: 'Asia/Shanghai',
          summary: {
            segmentCount: 2,
            recordedSeconds: 600,
            gapSeconds: 0,
            warningCount: 0,
          },
          segments: [
            {
              id: 278,
              fileId: 278,
              startAt: '2026-03-20T00:00:00+08:00',
              endAt: '2026-03-20T00:10:00+08:00',
              durationSec: 600,
              playbackUrl: '/api/videos/278/stream',
              fileOffsetSec: 0,
              status: 'ready',
              issueFlags: [],
            },
          ],
          gaps: [],
        }),
        {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        },
      ),
    ) as typeof fetch;

    vi.stubEnv('VITE_API_BASE_URL', 'http://127.0.0.1:8101');

    const timeline = await getTimeline(1, '2026-03-20');

    expect(globalThis.fetch).toHaveBeenCalledWith('http://127.0.0.1:8101/api/timeline?camera=1&day=2026-03-20', {
      headers: {
        Accept: 'application/json',
      },
      credentials: 'include',
    });
    expect(timeline.segments[0].playbackUrl).toBe('http://127.0.0.1:8101/api/videos/278/stream');
  });

  it('throws backend error message on non-ok response', async () => {
    globalThis.fetch = vi.fn(async () =>
      new Response(JSON.stringify({ detail: 'timeline not found' }), {
        status: 404,
        headers: { 'Content-Type': 'application/json' },
      }),
    ) as typeof fetch;

    await expect(getTimeline(1, '2026-03-21')).rejects.toThrow('timeline not found');
  });

  it('resolves playback urls for locate response against api base url', async () => {
    globalThis.fetch = vi.fn(async () =>
      new Response(
        JSON.stringify({
          found: true,
          segment: {
            id: 278,
            fileId: 278,
            startAt: '2026-03-20T00:00:00+08:00',
            endAt: '2026-03-20T00:10:00+08:00',
            durationSec: 600,
            playbackUrl: '/api/videos/278/stream',
            fileOffsetSec: 12,
            status: 'ready',
            issueFlags: [],
          },
          seekOffsetSec: 12,
          gap: null,
          nextSegment: {
            id: 279,
            fileId: 279,
            startAt: '2026-03-20T00:10:00+08:00',
            endAt: '2026-03-20T00:20:00+08:00',
            durationSec: 600,
            playbackUrl: '/api/videos/279/stream',
            fileOffsetSec: 0,
            status: 'ready',
            issueFlags: [],
          },
        }),
        {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        },
      ),
    ) as typeof fetch;

    vi.stubEnv('VITE_API_BASE_URL', 'http://127.0.0.1:8101');

    const located = await locateAt(1, '2026-03-20T00:00:12+08:00');

    expect(globalThis.fetch).toHaveBeenCalledWith(
      'http://127.0.0.1:8101/api/locate?camera=1&at=2026-03-20T00%3A00%3A12%2B08%3A00',
      {
        headers: {
          Accept: 'application/json',
        },
        credentials: 'include',
      },
    );
    expect(located.segment?.playbackUrl).toBe('http://127.0.0.1:8101/api/videos/278/stream');
    expect(located.nextSegment?.playbackUrl).toBe('http://127.0.0.1:8101/api/videos/279/stream');
  });

  it('requests auth status with credentials included', async () => {
    globalThis.fetch = vi.fn(async () =>
      new Response(JSON.stringify({ authenticated: true }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    ) as typeof fetch;

    await getAuthStatus();

    expect(globalThis.fetch).toHaveBeenCalledWith(
      '/api/auth/status',
      expect.objectContaining({
        credentials: 'include',
      }),
    );
  });

  it('lists cameras with credentials included', async () => {
    globalThis.fetch = vi.fn(async () =>
      new Response(JSON.stringify([{ cameraNo: 1, label: '通道 1' }]), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    ) as typeof fetch;

    await listCameras();

    expect(globalThis.fetch).toHaveBeenCalledWith(
      '/api/cameras',
      expect.objectContaining({
        credentials: 'include',
      }),
    );
  });
});
