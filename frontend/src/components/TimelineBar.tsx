import { useEffect, useRef, useState } from 'react';

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

const INLINE_LABEL_MIN_WIDTH_PERCENT = 8;

function eventToSecond(event: { clientX: number; currentTarget: HTMLDivElement }): number {
  const rect = event.currentTarget.getBoundingClientRect();
  const position = (event.clientX - rect.left) / rect.width;
  return positionToSecond(position, DAY_SECONDS);
}

function getAxisSeconds(zoom: number) {
  const screenSeconds = DAY_SECONDS / zoom;
  let gap = 6 * 3600;
  if (screenSeconds <= 1 * 3600) {
    gap = 10 * 60; // 10m
  } else if (screenSeconds <= 3 * 3600) {
    gap = 30 * 60; // 30m
  } else if (screenSeconds <= 6 * 3600) {
    gap = 3600; // 1h
  } else if (screenSeconds <= 12 * 3600) {
    gap = 2 * 3600; // 2h
  } else {
    gap = 6 * 3600; // 6h
  }
  
  const seconds = [];
  for (let s = 0; s <= DAY_SECONDS; s += gap) {
    if (s === DAY_SECONDS) {
      seconds.push(DAY_SECONDS - 1);
    } else {
      seconds.push(s);
    }
  }
  return seconds;
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
  const [zoom, setZoom] = useState(1);
  const [isDragging, setIsDragging] = useState(false);
  const [dragState, setDragState] = useState({ x: 0, scrollLeft: 0, hasDragged: false });
  
  const viewportRef = useRef<HTMLDivElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);

  const segmentBlocks = buildSegmentBlocks(segments);
  const gapBlocks = buildGapBlocks(gaps);
  const selectedSecond = selectedAt == null ? null : isoToSecondOfDay(selectedAt);

  useEffect(() => {
    const viewport = viewportRef.current;
    if (!viewport) return;

    const handleWheel = (e: WheelEvent) => {
      e.preventDefault();
      const zoomFactor = -e.deltaY * 0.005;
      setZoom((prevZoom) => {
        const newZoom = Math.max(1, Math.min(prevZoom * (1 + zoomFactor), 48));
        if (Math.abs(newZoom - prevZoom) < 0.01) return prevZoom;

        const rect = viewport.getBoundingClientRect();
        const mouseX = e.clientX - rect.left;
        const absoluteX = mouseX + viewport.scrollLeft;
        const newScrollLeft = absoluteX * (newZoom / prevZoom) - mouseX;

        requestAnimationFrame(() => {
          if (viewportRef.current) {
            viewportRef.current.scrollLeft = newScrollLeft;
          }
        });

        return newZoom;
      });
    };

    viewport.addEventListener('wheel', handleWheel, { passive: false });
    return () => {
      viewport.removeEventListener('wheel', handleWheel);
    };
  }, []);

  const handlePointerDown = (e: React.PointerEvent<HTMLDivElement>) => {
    viewportRef.current?.setPointerCapture(e.pointerId);
    setDragState({ x: e.clientX, scrollLeft: viewportRef.current?.scrollLeft ?? 0, hasDragged: false });
    setIsDragging(true);
  };

  const handlePointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    if (!isDragging) {
      if (contentRef.current) {
        setHoverSecond(eventToSecond({ clientX: e.clientX, currentTarget: contentRef.current }));
      }
      return;
    }
    const deltaX = e.clientX - dragState.x;
    if (Math.abs(deltaX) > 5) {
      setDragState(prev => ({ ...prev, hasDragged: true }));
    }
    if (viewportRef.current) {
      viewportRef.current.scrollLeft = dragState.scrollLeft - deltaX;
    }
  };

  const handlePointerUp = (e: React.PointerEvent<HTMLDivElement>) => {
    if (isDragging) {
      setIsDragging(false);
      viewportRef.current?.releasePointerCapture(e.pointerId);
      if (!dragState.hasDragged && contentRef.current) {
        onSelectTime(eventToSecond({ clientX: e.clientX, currentTarget: contentRef.current }));
      }
    }
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLDivElement>) => {
    if (event.key === 'ArrowLeft') {
      onSelectTime(Math.max((selectedSecond ?? 0) - 60, 0));
    }
    if (event.key === 'ArrowRight') {
      onSelectTime(Math.min((selectedSecond ?? 0) + 60, DAY_SECONDS - 1));
    }
  };

  const axisSeconds = getAxisSeconds(zoom);

  const content = (
    <div
      ref={viewportRef}
      className="timeline-viewport"
      style={{ overflow: 'hidden', touchAction: 'none', cursor: isDragging ? 'grabbing' : 'grab', paddingTop: '28px', marginTop: '-28px' }}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onPointerCancel={handlePointerUp}
      onPointerLeave={() => setHoverSecond(null)}
      role="button"
      tabIndex={0}
      onKeyDown={handleKeyDown}
      aria-label={`${day} 时间轴（支持滚轮缩放与鼠标拖拽）`}
    >
      <div
        ref={contentRef}
        className="timeline-content"
        style={{ width: `${zoom * 100}%`, position: 'relative' }}
      >
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
            className="timeline-track"
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
        <div className="timeline-axis" style={{ display: 'block', position: 'relative', height: '24px' }}>
          {axisSeconds.map((second) => (
            <span 
              key={second} 
              style={{ 
                position: 'absolute', 
                left: `${secondToPercent(second)}%`, 
                transform: second === 0 ? 'translateX(0)' : (second === DAY_SECONDS - 1 ? 'translateX(-100%)' : 'translateX(-50%)') 
              }}
            >
              {formatClock(second)}
            </span>
          ))}
        </div>
      </div>
    </div>
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
