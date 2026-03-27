import { request, resolveApiUrl } from './client';
import type {
  DaySummary,
  LocateResponse,
  TimelineSegment,
  RebuildResponse,
  TimelineResponse,
} from '../types/api';

function normalizeSegment(segment: TimelineSegment): TimelineSegment {
  return {
    ...segment,
    playbackUrl: resolveApiUrl(segment.playbackUrl),
  };
}

export function listDays(cameraNo: number = 1): Promise<DaySummary[]> {
  const query = new URLSearchParams({ camera: String(cameraNo) });
  return request<DaySummary[]>(`/api/days?${query.toString()}`);
}

export function getTimeline(day: string): Promise<TimelineResponse>;
export function getTimeline(cameraNo: number, day: string): Promise<TimelineResponse>;
export async function getTimeline(cameraOrDay: number | string, maybeDay?: string): Promise<TimelineResponse> {
  const cameraNo = typeof cameraOrDay === 'number' ? cameraOrDay : 1;
  const day = typeof cameraOrDay === 'number' ? maybeDay : cameraOrDay;
  if (day == null) {
    throw new Error('day is required');
  }

  const query = new URLSearchParams({
    camera: String(cameraNo),
    day,
  });
  const response = await request<TimelineResponse>(`/api/timeline?${query.toString()}`);
  return {
    ...response,
    segments: response.segments.map(normalizeSegment),
  };
}

export function locateAt(at: string): Promise<LocateResponse>;
export function locateAt(cameraNo: number, at: string): Promise<LocateResponse>;
export async function locateAt(cameraOrAt: number | string, maybeAt?: string): Promise<LocateResponse> {
  const cameraNo = typeof cameraOrAt === 'number' ? cameraOrAt : 1;
  const at = typeof cameraOrAt === 'number' ? maybeAt : cameraOrAt;
  if (at == null) {
    throw new Error('at is required');
  }

  const query = new URLSearchParams({
    camera: String(cameraNo),
    at,
  });
  const response = await request<LocateResponse>(`/api/locate?${query.toString()}`);
  return {
    ...response,
    segment: response.segment == null ? null : normalizeSegment(response.segment),
    nextSegment: response.nextSegment == null ? null : normalizeSegment(response.nextSegment),
  };
}

export function rebuildIndex(day?: string): Promise<RebuildResponse> {
  const path = day == null ? '/api/index/rebuild' : `/api/index/rebuild?day=${encodeURIComponent(day)}`;
  return request<RebuildResponse>(path, {
    method: 'POST',
  });
}
