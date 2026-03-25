import { useEffect, useState } from 'react';

import { listDays } from '../api/replay';
import type { DaySummary } from '../types/api';

interface UseDaysState {
  data: DaySummary[];
  error: string | null;
  loading: boolean;
}

export function useDays(): UseDaysState {
  const [data, setData] = useState<DaySummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);

      try {
        const days = await listDays();
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
  }, []);

  return { data, error, loading };
}
