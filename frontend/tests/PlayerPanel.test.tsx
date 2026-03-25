import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { PlayerPanel } from '../src/components/PlayerPanel';
import type { TimelineSegment } from '../src/types/api';

const segment: TimelineSegment = {
  id: 1,
  fileId: 11,
  startAt: '2026-03-20T03:00:00+08:00',
  endAt: '2026-03-20T03:10:00+08:00',
  durationSec: 600,
  playbackUrl: '/api/videos/11/stream',
  fileOffsetSec: 0,
  status: 'ready',
  issueFlags: [],
};

describe('PlayerPanel', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    Object.defineProperty(HTMLMediaElement.prototype, 'pause', {
      configurable: true,
      value: vi.fn(),
    });
  });

  it('syncs seek offset and play intent to video element', async () => {
    const playMock = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(HTMLMediaElement.prototype, 'play', {
      configurable: true,
      value: playMock,
    });

    const { container, rerender } = render(
      <PlayerPanel
        activeSegment={segment}
        gapMessage={null}
        playbackRate={1}
        playbackState="paused"
        seekOffsetSec={10}
        selectedAtLabel="2026-03-20 03:00:10"
        onEnded={() => {}}
      />,
    );

    const element = container.querySelector('video');
    if (!(element instanceof HTMLVideoElement)) {
      throw new Error('video element missing');
    }

    rerender(
      <PlayerPanel
        activeSegment={segment}
        gapMessage={null}
        playbackRate={2}
        playbackState="playing"
        seekOffsetSec={125}
        selectedAtLabel="2026-03-20 03:02:05"
        onEnded={() => {}}
      />,
    );

    fireEvent.loadedMetadata(element);

    await waitFor(() => {
      expect(element.currentTime).toBe(125);
    });
    expect(element.playbackRate).toBe(2);
    expect(playMock).toHaveBeenCalled();
  });

  it('does not reset current time when only playback rate changes', async () => {
    const playMock = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(HTMLMediaElement.prototype, 'play', {
      configurable: true,
      value: playMock,
    });

    const { container, rerender } = render(
      <PlayerPanel
        activeSegment={segment}
        gapMessage={null}
        playbackRate={1}
        playbackState="playing"
        seekOffsetSec={10}
        selectedAtLabel="2026-03-20 03:00:10"
        onEnded={() => {}}
      />,
    );

    const element = container.querySelector('video');
    if (!(element instanceof HTMLVideoElement)) {
      throw new Error('video element missing');
    }

    fireEvent.loadedMetadata(element);

    await waitFor(() => {
      expect(element.currentTime).toBe(10);
    });

    element.currentTime = 180;

    rerender(
      <PlayerPanel
        activeSegment={segment}
        gapMessage={null}
        playbackRate={2}
        playbackState="playing"
        seekOffsetSec={10}
        selectedAtLabel="2026-03-20 03:03:00"
        onEnded={() => {}}
      />,
    );

    expect(element.currentTime).toBe(180);
    expect(element.playbackRate).toBe(2);
  });

  it('does not render active segment status text under the video', () => {
    render(
      <PlayerPanel
        activeSegment={segment}
        gapMessage={null}
        playbackRate={1}
        playbackState="paused"
        seekOffsetSec={0}
        selectedAtLabel="2026-03-20 03:00:00"
        onEnded={() => {}}
      />,
    );

    expect(screen.queryByText(/当前片段文件/)).not.toBeInTheDocument();
    expect(screen.queryByText(/状态：/)).not.toBeInTheDocument();
  });
});
