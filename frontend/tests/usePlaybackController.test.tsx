import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { usePlaybackController } from '../src/hooks/usePlaybackController';
import type { LocateResponse, TimelineResponse } from '../src/types/api';

const { locateAtMock } = vi.hoisted(() => ({
  locateAtMock: vi.fn<Promise<LocateResponse>, [string]>(),
}));

vi.mock('../src/api/replay', async () => {
  const actual = await vi.importActual<typeof import('../src/api/replay')>('../src/api/replay');
  return {
    ...actual,
    locateAt: locateAtMock,
  };
});

const gapTimeline: TimelineResponse = {
  day: '2026-03-20',
  timezone: 'Asia/Shanghai',
  summary: {
    segmentCount: 2,
    recordedSeconds: 1200,
    gapSeconds: 40,
    warningCount: 0,
  },
  segments: [
    {
      id: 1,
      fileId: 11,
      startAt: '2026-03-20T03:00:00+08:00',
      endAt: '2026-03-20T03:10:00+08:00',
      durationSec: 600,
      playbackUrl: '/api/videos/11/stream',
      fileOffsetSec: 0,
      status: 'ready',
      issueFlags: [],
    },
    {
      id: 2,
      fileId: 12,
      startAt: '2026-03-20T03:10:40+08:00',
      endAt: '2026-03-20T03:20:40+08:00',
      durationSec: 600,
      playbackUrl: '/api/videos/12/stream',
      fileOffsetSec: 0,
      status: 'ready',
      issueFlags: [],
    },
  ],
  gaps: [
    {
      startAt: '2026-03-20T03:10:00+08:00',
      endAt: '2026-03-20T03:10:40+08:00',
      durationSec: 40,
    },
  ],
};

const continuousTimeline: TimelineResponse = {
  ...gapTimeline,
  summary: {
    ...gapTimeline.summary,
    gapSeconds: 0,
  },
  segments: [
    gapTimeline.segments[0],
    {
      ...gapTimeline.segments[1],
      startAt: '2026-03-20T03:10:01+08:00',
      endAt: '2026-03-20T03:20:01+08:00',
    },
  ],
  gaps: [],
};

describe('usePlaybackController', () => {
  beforeEach(() => {
    locateAtMock.mockReset();
  });

  it('shows gap state when locate returns no recording', async () => {
    locateAtMock.mockResolvedValue({
      found: false,
      segment: null,
      seekOffsetSec: null,
      gap: {
        startAt: '2026-03-20T03:10:00+08:00',
        endAt: '2026-03-20T03:10:40+08:00',
      },
      nextSegment: gapTimeline.segments[1],
    });

    const { result } = renderHook(() =>
      usePlaybackController({
        day: gapTimeline.day,
        timeline: gapTimeline,
      }),
    );

    await act(async () => {
      await result.current.selectSecond(3 * 3600 + 10 * 60 + 20);
    });

    await waitFor(() => {
      expect(result.current.playbackState).toBe('gap');
    });
    expect(result.current.activeSegment).toBeNull();
    expect(result.current.gapMessage).toContain('该时间点无录像');
  });

  it('autoplays next segment when gap is within 2 seconds', async () => {
    const { result } = renderHook(() =>
      usePlaybackController({
        day: continuousTimeline.day,
        timeline: continuousTimeline,
      }),
    );

    act(() => {
      result.current.setPlaybackRate(2);
      result.current.selectSecond(3 * 3600 + 5 * 60);
    });

    await waitFor(() => {
      expect(result.current.activeSegment?.id).toBe(1);
    });

    act(() => {
      result.current.handleSegmentEnded();
    });

    await waitFor(() => {
      expect(result.current.activeSegment?.id).toBe(2);
    });
    expect(result.current.playbackRate).toBe(2);
    expect(result.current.playbackState).toBe('playing');
  });

  it('ignores stale locate responses when user clicks a newer time point', async () => {
    let resolveFirst: ((value: LocateResponse) => void) | null = null;
    locateAtMock
      .mockImplementationOnce(
        () =>
          new Promise<LocateResponse>((resolve) => {
            resolveFirst = resolve;
          }),
      )
      .mockResolvedValueOnce({
        found: false,
        segment: null,
        seekOffsetSec: null,
        gap: {
          startAt: '2026-03-20T03:10:00+08:00',
          endAt: '2026-03-20T03:10:40+08:00',
        },
        nextSegment: gapTimeline.segments[1],
      });

    const { result } = renderHook(() =>
      usePlaybackController({
        day: gapTimeline.day,
        timeline: gapTimeline,
      }),
    );

    await act(async () => {
      const firstCall = result.current.selectSecond(3 * 3600 + 10 * 60 + 20);
      const secondCall = result.current.selectSecond(3 * 3600 + 5 * 60);
      await secondCall;
      resolveFirst?.({
        found: false,
        segment: null,
        seekOffsetSec: null,
        gap: {
          startAt: '2026-03-20T03:10:00+08:00',
          endAt: '2026-03-20T03:10:40+08:00',
        },
        nextSegment: gapTimeline.segments[1],
      });
      await firstCall;
    });

    expect(result.current.playbackState).toBe('playing');
    expect(result.current.activeSegment?.id).toBe(1);
  });

  it('does not autoplay next segment when precise gap is greater than 2 seconds', async () => {
    const preciseGapTimeline: TimelineResponse = {
      ...continuousTimeline,
      segments: [
        continuousTimeline.segments[0],
        {
          ...continuousTimeline.segments[1],
          startAt: '2026-03-20T03:10:02.500000+08:00',
          endAt: '2026-03-20T03:20:02.500000+08:00',
        },
      ],
    };

    const { result } = renderHook(() =>
      usePlaybackController({
        day: preciseGapTimeline.day,
        timeline: preciseGapTimeline,
      }),
    );

    act(() => {
      result.current.selectSecond(3 * 3600 + 5 * 60);
    });

    await waitFor(() => {
      expect(result.current.activeSegment?.id).toBe(1);
    });

    act(() => {
      result.current.handleSegmentEnded();
    });

    await waitFor(() => {
      expect(result.current.playbackState).toBe('gap');
    });
    expect(result.current.activeSegment).toBeNull();
  });
});
