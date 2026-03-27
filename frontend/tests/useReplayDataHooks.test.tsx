import { act, renderHook, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { useDays } from '../src/hooks/useDays';
import { useTimeline } from '../src/hooks/useTimeline';
import type { DaySummary, TimelineResponse } from '../src/types/api';

const { listDaysMock, getTimelineMock } = vi.hoisted(() => ({
  listDaysMock: vi.fn<Promise<DaySummary[]>, [number]>(),
  getTimelineMock: vi.fn<Promise<TimelineResponse>, [number, string]>(),
}));

vi.mock('../src/api/replay', async () => {
  const actual = await vi.importActual<typeof import('../src/api/replay')>('../src/api/replay');
  return {
    ...actual,
    listDays: listDaysMock,
    getTimeline: getTimelineMock,
  };
});

describe('replay data hooks', () => {
  it('clears stale days immediately when camera changes', async () => {
    let resolveSecondCamera: ((value: DaySummary[]) => void) | null = null;
    listDaysMock
      .mockResolvedValueOnce([
        {
          day: '2026-03-20',
          segmentCount: 1,
          recordedSeconds: 60,
          gapSeconds: 0,
          hasWarning: false,
          firstSegmentAt: '2026-03-20T00:00:00+08:00',
          lastSegmentAt: '2026-03-20T00:01:00+08:00',
        },
      ])
      .mockImplementationOnce(
        () =>
          new Promise<DaySummary[]>((resolve) => {
            resolveSecondCamera = resolve;
          }),
      );

    const { result, rerender } = renderHook(
      ({ cameraNo }) => useDays(cameraNo),
      { initialProps: { cameraNo: 1 } },
    );

    await waitFor(() => {
      expect(result.current.data).toHaveLength(1);
    });

    rerender({ cameraNo: 2 });

    expect(result.current.data).toEqual([]);
    expect(result.current.loading).toBe(true);

    await act(async () => {
      resolveSecondCamera?.([]);
    });

    await waitFor(() => {
      expect(result.current.data).toEqual([]);
      expect(result.current.loading).toBe(false);
    });
  });

  it('clears stale timeline immediately when camera changes', async () => {
    let resolveSecondCamera: ((value: TimelineResponse) => void) | null = null;
    getTimelineMock
      .mockResolvedValueOnce({
        day: '2026-03-20',
        timezone: 'Asia/Shanghai',
        summary: {
          segmentCount: 1,
          recordedSeconds: 60,
          gapSeconds: 0,
          warningCount: 0,
        },
        segments: [
          {
            id: 1,
            fileId: 10,
            startAt: '2026-03-20T00:00:00+08:00',
            endAt: '2026-03-20T00:01:00+08:00',
            durationSec: 60,
            playbackUrl: '/api/videos/10/stream',
            fileOffsetSec: 0,
            status: 'ready',
            issueFlags: [],
          },
        ],
        gaps: [],
      })
      .mockImplementationOnce(
        () =>
          new Promise<TimelineResponse>((resolve) => {
            resolveSecondCamera = resolve;
          }),
      );

    const { result, rerender } = renderHook(
      ({ cameraNo, day }) => useTimeline(cameraNo, day),
      { initialProps: { cameraNo: 1, day: '2026-03-20' } },
    );

    await waitFor(() => {
      expect(result.current.data?.day).toBe('2026-03-20');
    });

    rerender({ cameraNo: 2, day: '2026-03-20' });

    expect(result.current.data).toBeNull();
    expect(result.current.loading).toBe(true);

    await act(async () => {
      resolveSecondCamera?.({
        day: '2026-03-20',
        timezone: 'Asia/Shanghai',
        summary: {
          segmentCount: 0,
          recordedSeconds: 0,
          gapSeconds: 0,
          warningCount: 0,
        },
        segments: [],
        gaps: [],
      });
    });

    await waitFor(() => {
      expect(result.current.data?.segments).toEqual([]);
      expect(result.current.loading).toBe(false);
    });
  });
});
