import { useEffect, useState } from 'react';

import { getTimeline } from '../api/replay';
import type { TimelineResponse } from '../types/api';

interface UseTimelineState {
  data: TimelineResponse | null;
  error: string | null;
  loading: boolean;
}

export function useTimeline(day: string | null): UseTimelineState;
export function useTimeline(cameraNo: number, day: string | null): UseTimelineState;
export function useTimeline(cameraOrDay: number | string | null, maybeDay?: string | null): UseTimelineState {
  const cameraNo = typeof cameraOrDay === 'number' ? cameraOrDay : 1;
  const day = typeof cameraOrDay === 'number' ? maybeDay ?? null : cameraOrDay;
  const [data, setData] = useState<TimelineResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (day == null) {
      setData(null);
      setError(null);
      setLoading(false);
      return;
    }

    const currentDay = day;
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      setData(null);

      try {
        const timeline = await getTimeline(cameraNo, currentDay);
        if (!cancelled) {
          setData(timeline);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : '加载时间轴失败');
          setData(null);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void load();

    return () => {
      cancelled = true;
    };
  }, [cameraNo, day]);

  return { data, error, loading };
}
