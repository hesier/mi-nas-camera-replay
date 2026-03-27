import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ReplayPage } from '../src/pages/ReplayPage';
import type { CameraItem, DaySummary, TimelineResponse } from '../src/types/api';

const { useCamerasMock, useDaysMock, useTimelineMock, usePlaybackControllerMock } = vi.hoisted(() => ({
  useCamerasMock: vi.fn<
    { data: CameraItem[]; error: string | null; loading: boolean },
    []
  >(),
  useDaysMock: vi.fn<
    { data: DaySummary[]; error: string | null; loading: boolean },
    [number]
  >(),
  useTimelineMock: vi.fn<
    { data: TimelineResponse | null; error: string | null; loading: boolean },
    [number, string | null]
  >(),
  usePlaybackControllerMock: vi.fn(),
}));

vi.mock('../src/hooks/useCameras', () => ({
  useCameras: () => useCamerasMock(),
}));

vi.mock('../src/hooks/useDays', () => ({
  useDays: (cameraNo: number) => useDaysMock(cameraNo),
}));

vi.mock('../src/hooks/useTimeline', () => ({
  useTimeline: (cameraNo: number, day: string | null) => useTimelineMock(cameraNo, day),
}));

vi.mock('../src/hooks/usePlaybackController', () => ({
  usePlaybackController: (options: unknown) => usePlaybackControllerMock(options),
}));

function buildTimeline(day: string): TimelineResponse {
  return {
    day,
    timezone: 'Asia/Shanghai',
    summary: {
      segmentCount: 1,
      recordedSeconds: 600,
      gapSeconds: 0,
      warningCount: 0,
    },
    segments: [
      {
        id: 1,
        fileId: 11,
        startAt: `${day}T03:00:00+08:00`,
        endAt: `${day}T03:10:00+08:00`,
        durationSec: 600,
        playbackUrl: '/api/videos/11/stream',
        fileOffsetSec: 0,
        status: 'ready',
        issueFlags: [],
      },
    ],
    gaps: [],
  };
}

function buildDays(day: string): DaySummary[] {
  return [
    {
      day,
      segmentCount: 1,
      recordedSeconds: 600,
      gapSeconds: 0,
      hasWarning: false,
      firstSegmentAt: `${day}T03:00:00+08:00`,
      lastSegmentAt: `${day}T03:10:00+08:00`,
    },
  ];
}

describe('ReplayPage', () => {
  beforeEach(() => {
    useCamerasMock.mockReset();
    useDaysMock.mockReset();
    useTimelineMock.mockReset();
    usePlaybackControllerMock.mockReset();

    usePlaybackControllerMock.mockReturnValue({
      activeSegment: null,
      gapMessage: null,
      nextSegment: null,
      playbackRate: 1,
      playbackState: 'idle',
      seekOffsetSec: null,
      selectedAt: null,
      selectedSecond: 0,
      handleSegmentEnded: vi.fn(),
      selectSecond: vi.fn(async () => {}),
      setPlaybackRate: vi.fn(),
    });
  });

  it('shows camera picker when multiple cameras exist', async () => {
    useCamerasMock.mockReturnValue({
      data: [
        { cameraNo: 1, label: '通道 1' },
        { cameraNo: 2, label: '通道 2' },
      ],
      error: null,
      loading: false,
    });
    useDaysMock.mockImplementation((cameraNo) => ({
      data: buildDays(cameraNo === 1 ? '2026-03-20' : '2026-03-21'),
      error: null,
      loading: false,
    }));
    useTimelineMock.mockImplementation((cameraNo, day) => ({
      data: day == null ? null : buildTimeline(cameraNo === 1 ? '2026-03-20' : '2026-03-21'),
      error: null,
      loading: false,
    }));

    render(<ReplayPage />);

    expect(await screen.findByLabelText('回放通道')).toBeInTheDocument();
    expect(useDaysMock).toHaveBeenLastCalledWith(1);
  });

  it('hides camera picker when only one camera exists', () => {
    useCamerasMock.mockReturnValue({
      data: [{ cameraNo: 1, label: '通道 1' }],
      error: null,
      loading: false,
    });
    useDaysMock.mockReturnValue({ data: buildDays('2026-03-20'), error: null, loading: false });
    useTimelineMock.mockReturnValue({ data: buildTimeline('2026-03-20'), error: null, loading: false });

    render(<ReplayPage />);

    expect(screen.queryByLabelText('回放通道')).not.toBeInTheDocument();
  });

  it('shows empty state instead of timeline when selected camera has no days', async () => {
    useCamerasMock.mockReturnValue({
      data: [{ cameraNo: 2, label: '通道 2' }],
      error: null,
      loading: false,
    });
    useDaysMock.mockReturnValue({ data: [], error: null, loading: false });
    useTimelineMock.mockReturnValue({ data: null, error: null, loading: false });

    render(<ReplayPage />);

    expect(await screen.findByText('该通道暂无录像')).toBeInTheDocument();
    expect(screen.queryByText('该时间点无录像，请点击时间轴上的有效片段。')).not.toBeInTheDocument();
    expect(useTimelineMock).toHaveBeenLastCalledWith(2, null);
  });

  it('switches camera by reloading days and selecting latest day before loading timeline', async () => {
    useCamerasMock.mockReturnValue({
      data: [
        { cameraNo: 1, label: '通道 1' },
        { cameraNo: 2, label: '通道 2' },
      ],
      error: null,
      loading: false,
    });
    useDaysMock.mockImplementation((cameraNo) => ({
      data: buildDays(cameraNo === 1 ? '2026-03-20' : '2026-03-21'),
      error: null,
      loading: false,
    }));
    useTimelineMock.mockImplementation((cameraNo, day) => ({
      data: day == null ? null : buildTimeline(cameraNo === 1 ? '2026-03-20' : '2026-03-21'),
      error: null,
      loading: false,
    }));

    render(<ReplayPage />);

    const cameraPicker = await screen.findByLabelText('回放通道');
    fireEvent.change(cameraPicker, { target: { value: '2' } });

    await waitFor(() => {
      expect(useDaysMock).toHaveBeenLastCalledWith(2);
      expect(useTimelineMock).toHaveBeenLastCalledWith(2, '2026-03-21');
    });
  });

  it('does not request timeline when selected camera has no days', async () => {
    useCamerasMock.mockReturnValue({
      data: [
        { cameraNo: 1, label: '通道 1' },
        { cameraNo: 2, label: '通道 2' },
      ],
      error: null,
      loading: false,
    });
    useDaysMock.mockImplementation((cameraNo) => ({
      data: cameraNo === 1 ? buildDays('2026-03-20') : [],
      error: null,
      loading: false,
    }));
    useTimelineMock.mockImplementation((cameraNo, day) => ({
      data: cameraNo === 1 && day != null ? buildTimeline(day) : null,
      error: null,
      loading: false,
    }));

    render(<ReplayPage />);

    const cameraPicker = await screen.findByLabelText('回放通道');
    fireEvent.change(cameraPicker, { target: { value: '2' } });

    await waitFor(() => {
      expect(useTimelineMock).toHaveBeenLastCalledWith(2, null);
    });
  });

  it('passes null timeline to playback controller while switching camera', async () => {
    useCamerasMock.mockReturnValue({
      data: [
        { cameraNo: 1, label: '通道 1' },
        { cameraNo: 2, label: '通道 2' },
        { cameraNo: 3, label: '通道 3' },
      ],
      error: null,
      loading: false,
    });
    useDaysMock.mockImplementation((cameraNo) => ({
      data: cameraNo === 1 ? buildDays('2026-03-20') : cameraNo === 2 ? buildDays('2026-03-21') : [],
      error: null,
      loading: false,
    }));
    useTimelineMock.mockImplementation((_cameraNo, day) => ({
      data: day == null ? buildTimeline('2026-03-21') : buildTimeline(day),
      error: null,
      loading: false,
    }));

    render(<ReplayPage />);

    fireEvent.change(await screen.findByLabelText('回放通道'), {
      target: { value: '2' },
    });

    await waitFor(() => {
      expect(useDaysMock).toHaveBeenLastCalledWith(2);
    });

    expect(usePlaybackControllerMock.mock.calls).toContainEqual([
      expect.objectContaining({
        cameraNo: 2,
        day: null,
        timeline: null,
      }),
    ]);
  });
});
