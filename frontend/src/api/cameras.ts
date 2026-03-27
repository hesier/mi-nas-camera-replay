import { request } from './client';
import type { CameraItem } from '../types/api';

export function listCameras(): Promise<CameraItem[]> {
  return request<CameraItem[]>('/api/cameras');
}
