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

export function listDays(): Promise<DaySummary[]> {
  return request<DaySummary[]>('/api/days');
}

export async function getTimeline(day: string): Promise<TimelineResponse> {
  const query = new URLSearchParams({ day });
  const response = await request<TimelineResponse>(`/api/timeline?${query.toString()}`);
  return {
    ...response,
    segments: response.segments.map(normalizeSegment),
  };
}

export async function locateAt(at: string): Promise<LocateResponse> {
  const query = new URLSearchParams({ at });
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
