import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { positionToSecond } from '../src/utils/timeline';
import { TimelineBar } from '../src/components/TimelineBar';
import type { TimelineGap, TimelineSegment } from '../src/types/api';

const segments: TimelineSegment[] = [
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
];

const gaps: TimelineGap[] = [
  {
    startAt: '2026-03-20T03:10:00+08:00',
    endAt: '2026-03-20T03:15:00+08:00',
    durationSec: 300,
  },
];

describe('TimelineBar', () => {
  it('renders gap and segment blocks', () => {
    render(
      <TimelineBar
        day="2026-03-20"
        segments={segments}
        gaps={gaps}
        selectedAt="2026-03-20T03:05:00+08:00"
        onSelectTime={() => {}}
      />,
    );

    expect(screen.getByText('00:00')).toBeInTheDocument();
    expect(screen.getByLabelText('录像片段 03:00 - 03:10')).toHaveAttribute('title', '03:00 - 03:10');
    expect(screen.getByLabelText('断档 03:10 - 03:15')).toBeInTheDocument();
  });

  it('does not render inline text for narrow segments', () => {
    render(
      <TimelineBar
        day="2026-03-20"
        segments={segments}
        gaps={gaps}
        selectedAt="2026-03-20T03:05:00+08:00"
        onSelectTime={() => {}}
      />,
    );

    const segment = screen.getByLabelText('录像片段 03:00 - 03:10');
    expect(segment).toHaveAttribute('title', '03:00 - 03:10');
    expect(screen.queryByText('03:00')).not.toBeInTheDocument();
  });

  it('converts click position to wall clock second', () => {
    expect(positionToSecond(0.5, 86400)).toBe(43200);
  });

  it('emits selected second when clicking timeline', () => {
    const onSelectTime = vi.fn();
    render(
      <TimelineBar
        day="2026-03-20"
        segments={segments}
        gaps={gaps}
        selectedAt={null}
        onSelectTime={onSelectTime}
      />,
    );

    const track = screen.getByLabelText('2026-03-20 时间轴');
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

    fireEvent.click(track, { clientX: 120 });

    expect(onSelectTime).toHaveBeenCalledWith(43200);
  });

  it('shows hover time and clears it on mouse leave', () => {
    render(
      <TimelineBar
        day="2026-03-20"
        segments={segments}
        gaps={gaps}
        selectedAt={null}
        onSelectTime={() => {}}
      />,
    );

    const track = screen.getByLabelText('2026-03-20 时间轴');
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

    fireEvent.mouseMove(track, { clientX: 120 });
    const hoverMarker = screen.getByLabelText('悬停时间 12:00:00');
    expect(hoverMarker).toBeInTheDocument();
    expect(track).not.toContainElement(hoverMarker);

    fireEvent.mouseLeave(track);
    expect(screen.queryByLabelText('悬停时间 12:00:00')).not.toBeInTheDocument();
  });
});
