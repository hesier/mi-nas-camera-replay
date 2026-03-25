import type { TimelineGap, TimelineSegment } from '../types/api';
import { formatClock, isoToSecondOfDay } from './time';

export const DAY_SECONDS = 24 * 60 * 60;

export interface TimelineBlock {
  id: string;
  leftPercent: number;
  widthPercent: number;
  label: string;
}

export function positionToSecond(position: number, durationSeconds: number): number {
  const clamped = Math.max(0, Math.min(1, position));
  return Math.floor(clamped * durationSeconds);
}

export function secondToPercent(secondOfDay: number): number {
  return (secondOfDay / DAY_SECONDS) * 100;
}

export function buildSegmentBlocks(segments: TimelineSegment[]): TimelineBlock[] {
  return segments.map((segment) => {
    const start = isoToSecondOfDay(segment.startAt);
    const end = isoToSecondOfDay(segment.endAt);
    return {
      id: `segment-${segment.id}`,
      leftPercent: secondToPercent(start),
      widthPercent: Math.max(secondToPercent(end - start), 0.4),
      label: `${formatClock(start)} - ${formatClock(end)}`,
    };
  });
}

export function buildGapBlocks(gaps: TimelineGap[]): TimelineBlock[] {
  return gaps.map((gap, index) => {
    const start = isoToSecondOfDay(gap.startAt);
    const end = isoToSecondOfDay(gap.endAt);
    return {
      id: `gap-${index}`,
      leftPercent: secondToPercent(start),
      widthPercent: Math.max(secondToPercent(end - start), 0.4),
      label: `${formatClock(start)} - ${formatClock(end)}`,
    };
  });
}

export function findSegmentAtSecond(
  segments: TimelineSegment[],
  secondOfDay: number,
): TimelineSegment | null {
  for (const segment of segments) {
    const start = isoToSecondOfDay(segment.startAt);
    const end = isoToSecondOfDay(segment.endAt);
    if (secondOfDay >= start && secondOfDay < end) {
      return segment;
    }
  }

  return null;
}
