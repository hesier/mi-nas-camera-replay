import { useEffect, useState } from 'react';

import { listDays } from '../api/replay';
import type { DaySummary } from '../types/api';

interface UseDaysState {
  data: DaySummary[];
  error: string | null;
  loading: boolean;
}

export function useDays(cameraNo: number | null): UseDaysState {
  const [data, setData] = useState<DaySummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(cameraNo != null);

  useEffect(() => {
    if (cameraNo == null) {
      setData([]);
      setError(null);
      setLoading(false);
      return;
    }

    const currentCameraNo = cameraNo;
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      setData([]);

      try {
        const days = await listDays(currentCameraNo);
        if (!cancelled) {
          setData(days);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : '加载日期失败');
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
  }, [cameraNo]);

  return { data, error, loading };
}
