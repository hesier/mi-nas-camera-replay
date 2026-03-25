import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ReplayPage } from '../src/pages/ReplayPage';
import type { DaySummary, LocateResponse, TimelineResponse } from '../src/types/api';

const { locateAtMock } = vi.hoisted(() => ({
  locateAtMock: vi.fn<Promise<LocateResponse>, [string]>(),
}));

vi.mock('../src/hooks/useDays', () => ({
  useDays: (): { data: DaySummary[]; error: string | null; loading: boolean } => ({
    data: [
      {
        day: '2026-03-20',
        segmentCount: 2,
        recordedSeconds: 1200,
        gapSeconds: 40,
        hasWarning: false,
        firstSegmentAt: '2026-03-20T03:00:00+08:00',
        lastSegmentAt: '2026-03-20T03:20:00+08:00',
      },
    ],
    error: null,
    loading: false,
  }),
}));

vi.mock('../src/hooks/useTimeline', () => ({
  useTimeline: (): { data: TimelineResponse; error: string | null; loading: boolean } => ({
    data: {
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
    },
    error: null,
    loading: false,
  }),
}));

vi.mock('../src/api/replay', async () => {
  const actual = await vi.importActual<typeof import('../src/api/replay')>('../src/api/replay');
  return {
    ...actual,
    locateAt: locateAtMock,
  };
});

describe('ReplayPage', () => {
  beforeEach(() => {
    locateAtMock.mockReset();
  });

  it('renders compact top controls without section headings', () => {
    render(<ReplayPage />);

    expect(screen.queryByText('回放参数')).not.toBeInTheDocument();
    expect(screen.queryByText('播放控制')).not.toBeInTheDocument();
    expect(screen.getByText('回放日期')).toBeInTheDocument();
    expect(screen.getByText('当前时间')).toBeInTheDocument();
    expect(screen.getByText('倍速')).toBeInTheDocument();
  });

  it('renders timeline inside player panel instead of a separate card', () => {
    render(<ReplayPage />);

    const playerPanel = screen.getByText('播放器').closest('section');
    const timelineTrack = screen.getByLabelText('2026-03-20 时间轴');

    expect(playerPanel).not.toBeNull();
    expect(playerPanel).toContainElement(timelineTrack);
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
      nextSegment: {
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
    });

    render(<ReplayPage />);

    const track = await screen.findByLabelText('2026-03-20 时间轴');
    vi.spyOn(track, 'getBoundingClientRect').mockReturnValue({
      x: 0,
      y: 0,
      width: 240,
      height: 24,
      top: 0,
      right: 240,
      bottom: 24,
      left: 0,
      toJSON: () => ({}),
    });

    fireEvent.click(track, { clientX: 31.72 });

    await waitFor(() => {
      expect(screen.getByText('该时间点无录像，请点击时间轴上的有效片段。')).toBeInTheDocument();
    });
  });
});
