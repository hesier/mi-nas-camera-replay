import { useEffect, useRef } from 'react';
import type { ReactNode } from 'react';

import type { TimelineSegment } from '../types/api';
import type { PlaybackState } from '../hooks/usePlaybackController';

interface PlayerPanelProps {
  activeSegment: TimelineSegment | null;
  children?: ReactNode;
  gapMessage: string | null;
  playbackRate: number;
  playbackState: PlaybackState;
  seekOffsetSec: number | null;
  selectedAtLabel: string;
  onEnded: () => void;
}

export function PlayerPanel({
  activeSegment,
  children,
  gapMessage,
  playbackRate,
  playbackState,
  seekOffsetSec,
  selectedAtLabel,
  onEnded,
}: PlayerPanelProps) {
  const videoRef = useRef<HTMLVideoElement | null>(null);

  useEffect(() => {
    const video = videoRef.current;
    if (video == null) {
      return;
    }

    if (seekOffsetSec != null) {
      video.currentTime = seekOffsetSec;
    }
  }, [activeSegment?.id, seekOffsetSec]);

  useEffect(() => {
    const video = videoRef.current;
    if (video == null) {
      return;
    }

    video.playbackRate = playbackRate;
  }, [playbackRate]);

  useEffect(() => {
    const video = videoRef.current;
    if (video == null) {
      return;
    }

    if (playbackState === 'playing') {
      void video.play().catch(() => {});
    }
    if (playbackState === 'paused') {
      video.pause();
    }
  }, [playbackState, activeSegment?.id]);

  return (
    <section className="panel player-panel">
      <div className="panel-header">
        <h2>播放器</h2>
        <span className="panel-note">{selectedAtLabel}</span>
      </div>
      <div className="video-shell">
        <video
          key={activeSegment?.id ?? 'empty'}
          ref={videoRef}
          className="video-element"
          controls
          playsInline
          preload="metadata"
          src={activeSegment?.playbackUrl}
          onEnded={onEnded}
          onLoadedMetadata={() => {
            if (videoRef.current != null && seekOffsetSec != null) {
              videoRef.current.currentTime = seekOffsetSec;
            }
            if (videoRef.current != null && playbackState === 'playing') {
              void videoRef.current.play().catch(() => {});
            }
          }}
        />
      </div>
      {activeSegment == null ? (
        <p className="empty-text">
          {gapMessage ?? '该时间点无录像，请点击时间轴上的有效片段。'}
        </p>
      ) : null}
      {children != null ? <div className="player-panel-footer">{children}</div> : null}
    </section>
  );
}
