import { useEffect, useState } from 'react';

import { listCameras } from '../api/cameras';
import type { CameraItem } from '../types/api';

interface UseCamerasState {
  data: CameraItem[];
  error: string | null;
  loading: boolean;
  refresh: () => Promise<void>;
}

export function useCameras(): UseCamerasState {
  const [data, setData] = useState<CameraItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  async function refresh(): Promise<void> {
    setLoading(true);
    setError(null);
    try {
      const cameras = await listCameras();
      setData(cameras);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载通道列表失败');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  return { data, error, loading, refresh };
}
