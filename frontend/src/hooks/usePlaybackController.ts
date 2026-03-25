import { useEffect, useRef, useState } from 'react';

import { locateAt } from '../api/replay';
import type { TimelineResponse, TimelineSegment } from '../types/api';
import { secondOfDayToIso } from '../utils/time';
import { findSegmentAtSecond } from '../utils/timeline';

export type PlaybackState = 'idle' | 'loading' | 'playing' | 'paused' | 'gap' | 'error';

interface UsePlaybackControllerOptions {
  day: string | null;
  timeline: TimelineResponse | null;
}

interface UsePlaybackControllerResult {
  activeSegment: TimelineSegment | null;
  gapMessage: string | null;
  nextSegment: TimelineSegment | null;
  playbackRate: number;
  playbackState: PlaybackState;
  seekOffsetSec: number | null;
  selectedAt: string | null;
  selectedSecond: number;
  handleSegmentEnded: () => void;
  selectSecond: (second: number) => Promise<void>;
  setPlaybackRate: (value: number) => void;
}

function getSegmentStartSecond(segment: TimelineSegment): number {
  return Number(segment.startAt.slice(11, 13)) * 3600 +
    Number(segment.startAt.slice(14, 16)) * 60 +
    Number(segment.startAt.slice(17, 19));
}

function getSegmentEndSecond(segment: TimelineSegment): number {
  return Number(segment.endAt.slice(11, 13)) * 3600 +
    Number(segment.endAt.slice(14, 16)) * 60 +
    Number(segment.endAt.slice(17, 19));
}

function getPreciseSecondOfDay(isoValue: string): number {
  const match = isoValue.match(/T(\d{2}):(\d{2}):(\d{2})(\.\d+)?/);
  if (match == null) {
    throw new Error(`invalid iso datetime: ${isoValue}`);
  }

  const hours = Number(match[1]);
  const minutes = Number(match[2]);
  const seconds = Number(match[3]);
  const fraction = match[4] == null ? 0 : Number(match[4]);
  return hours * 3600 + minutes * 60 + seconds + fraction;
}

export function usePlaybackController({
  day,
  timeline,
}: UsePlaybackControllerOptions): UsePlaybackControllerResult {
  const [selectedSecond, setSelectedSecond] = useState(0);
  const [playbackRate, setPlaybackRate] = useState(1);
  const [activeSegment, setActiveSegment] = useState<TimelineSegment | null>(null);
  const [nextSegment, setNextSegment] = useState<TimelineSegment | null>(null);
  const [gapMessage, setGapMessage] = useState<string | null>(null);
  const [seekOffsetSec, setSeekOffsetSec] = useState<number | null>(null);
  const [playbackState, setPlaybackState] = useState<PlaybackState>('idle');
  const requestIdRef = useRef(0);

  useEffect(() => {
    requestIdRef.current += 1;
    if (timeline?.segments[0] == null) {
      setActiveSegment(null);
      setNextSegment(null);
      setGapMessage(null);
      setSeekOffsetSec(null);
      setPlaybackState('idle');
      return;
    }

    const firstSegment = timeline.segments[0];
    setSelectedSecond(getSegmentStartSecond(firstSegment));
    setActiveSegment(firstSegment);
    setNextSegment(timeline.segments[1] ?? null);
    setGapMessage(null);
    setSeekOffsetSec(firstSegment.fileOffsetSec);
    setPlaybackState('paused');
  }, [timeline?.day]);

  async function selectSecond(second: number): Promise<void> {
    setSelectedSecond(second);
    requestIdRef.current += 1;
    const currentRequestId = requestIdRef.current;

    if (day == null || timeline == null) {
      setPlaybackState('idle');
      return;
    }

    const localSegment = findSegmentAtSecond(timeline.segments, second);
    if (localSegment != null) {
      const localIndex = timeline.segments.findIndex((segment) => segment.id === localSegment.id);
      setActiveSegment(localSegment);
      setNextSegment(localIndex >= 0 ? timeline.segments[localIndex + 1] ?? null : null);
      setGapMessage(null);
      setSeekOffsetSec(localSegment.fileOffsetSec + (second - getSegmentStartSecond(localSegment)));
      setPlaybackState('playing');
      return;
    }

    setPlaybackState('loading');
    try {
      const response = await locateAt(secondOfDayToIso(day, second));
      if (currentRequestId !== requestIdRef.current) {
        return;
      }

      if (response.found && response.segment != null) {
        setActiveSegment(response.segment);
        setNextSegment(response.nextSegment);
        setGapMessage(null);
        setSeekOffsetSec(response.seekOffsetSec);
        setPlaybackState('playing');
        return;
      }

      setActiveSegment(null);
      setNextSegment(response.nextSegment);
      setGapMessage('该时间点无录像，请点击时间轴上的有效片段。');
      setSeekOffsetSec(null);
      setPlaybackState('gap');
    } catch {
      if (currentRequestId !== requestIdRef.current) {
        return;
      }

      setActiveSegment(null);
      setNextSegment(null);
      setGapMessage('定位失败，请稍后重试。');
      setSeekOffsetSec(null);
      setPlaybackState('error');
    }
  }

  function handleSegmentEnded(): void {
    if (timeline == null || activeSegment == null) {
      return;
    }

    const currentIndex = timeline.segments.findIndex((segment) => segment.id === activeSegment.id);
    if (currentIndex < 0) {
      return;
    }

    const candidate = timeline.segments[currentIndex + 1] ?? null;
    if (candidate == null) {
      setPlaybackState('paused');
      return;
    }

    const gapSec = getPreciseSecondOfDay(candidate.startAt) - getPreciseSecondOfDay(activeSegment.endAt);
    if (gapSec <= 2) {
      setSelectedSecond(getSegmentStartSecond(candidate));
      setActiveSegment(candidate);
      setNextSegment(timeline.segments[currentIndex + 2] ?? null);
      setGapMessage(null);
      setSeekOffsetSec(candidate.fileOffsetSec);
      setPlaybackState('playing');
      return;
    }

    setActiveSegment(null);
    setNextSegment(candidate);
    setGapMessage('当前片段已结束，下一段录像前存在断档。');
    setSeekOffsetSec(null);
    setPlaybackState('gap');
  }

  return {
    activeSegment,
    gapMessage,
    nextSegment,
    playbackRate,
    playbackState,
    seekOffsetSec,
    selectedAt: day == null ? null : secondOfDayToIso(day, selectedSecond),
    selectedSecond,
    handleSegmentEnded,
    selectSecond,
    setPlaybackRate,
  };
}
