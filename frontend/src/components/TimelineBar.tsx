import { useState } from 'react';

import type { TimelineGap, TimelineSegment } from '../types/api';
import { buildGapBlocks, buildSegmentBlocks, DAY_SECONDS, positionToSecond, secondToPercent } from '../utils/timeline';
import { formatClock, formatClockWithSeconds, isoToSecondOfDay } from '../utils/time';

interface TimelineBarProps {
  day: string;
  embedded?: boolean;
  segments: TimelineSegment[];
  gaps: TimelineGap[];
  selectedAt: string | null;
  onSelectTime: (secondOfDay: number) => void;
}

const AXIS_SECONDS = [0, 6 * 3600, 12 * 3600, 18 * 3600, 23 * 3600 + 59 * 60];
const INLINE_LABEL_MIN_WIDTH_PERCENT = 8;

function eventToSecond(event: { clientX: number; currentTarget: HTMLDivElement }): number {
  const rect = event.currentTarget.getBoundingClientRect();
  const position = (event.clientX - rect.left) / rect.width;
  return positionToSecond(position, DAY_SECONDS);
}

export function TimelineBar({
  day,
  embedded = false,
  segments,
  gaps,
  selectedAt,
  onSelectTime,
}: TimelineBarProps) {
  const [hoverSecond, setHoverSecond] = useState<number | null>(null);
  const segmentBlocks = buildSegmentBlocks(segments);
  const gapBlocks = buildGapBlocks(gaps);
  const selectedSecond = selectedAt == null ? null : isoToSecondOfDay(selectedAt);

  const content = (
    <>
      <div className="timeline-track-shell">
        {hoverSecond != null ? (
          <div
            aria-label={`悬停时间 ${formatClockWithSeconds(hoverSecond)}`}
            className="timeline-hover-marker"
            style={{ left: `${secondToPercent(hoverSecond)}%` }}
          >
            <span className="timeline-hover-label">{formatClockWithSeconds(hoverSecond)}</span>
          </div>
        ) : null}
        <div
          aria-label={`${day} 时间轴`}
          className="timeline-track"
          role="button"
          tabIndex={0}
          onClick={(event) => {
            onSelectTime(eventToSecond(event));
          }}
          onMouseMove={(event) => {
            setHoverSecond(eventToSecond(event));
          }}
          onMouseLeave={() => {
            setHoverSecond(null);
          }}
          onKeyDown={(event) => {
            if (event.key === 'ArrowLeft') {
              onSelectTime(Math.max((selectedSecond ?? 0) - 60, 0));
            }
            if (event.key === 'ArrowRight') {
              onSelectTime(Math.min((selectedSecond ?? 0) + 60, DAY_SECONDS - 1));
            }
          }}
        >
          {gapBlocks.map((gap) => (
            <div
              key={gap.id}
              aria-label={`断档 ${gap.label}`}
              className="timeline-gap"
              style={{ left: `${gap.leftPercent}%`, width: `${gap.widthPercent}%` }}
            />
          ))}
          {segmentBlocks.map((segment) => (
            <div
              key={segment.id}
              aria-label={`录像片段 ${segment.label}`}
              className={`timeline-segment${segment.widthPercent >= INLINE_LABEL_MIN_WIDTH_PERCENT ? ' timeline-segment-labeled' : ''}`}
              style={{ left: `${segment.leftPercent}%`, width: `${segment.widthPercent}%` }}
              title={segment.label}
            >
              {segment.widthPercent >= INLINE_LABEL_MIN_WIDTH_PERCENT ? (
                <span>{segment.label.split(' - ')[0]}</span>
              ) : null}
            </div>
          ))}
          {selectedSecond != null ? (
            <div
              className="timeline-cursor"
              style={{ left: `${secondToPercent(selectedSecond)}%` }}
            />
          ) : null}
        </div>
      </div>
      <div className="timeline-axis">
        {AXIS_SECONDS.map((second) => (
          <span key={second}>{formatClock(second)}</span>
        ))}
      </div>
    </>
  );

  if (embedded) {
    return <div className="timeline-embedded">{content}</div>;
  }

  return (
    <section className="panel timeline-panel">
      {content}
    </section>
  );
}
