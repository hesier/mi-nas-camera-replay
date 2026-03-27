export interface DaySummary {
  day: string;
  segmentCount: number;
  recordedSeconds: number;
  gapSeconds: number;
  hasWarning: boolean;
  firstSegmentAt: string | null;
  lastSegmentAt: string | null;
}

export interface TimelineSummary {
  segmentCount: number;
  recordedSeconds: number;
  gapSeconds: number;
  warningCount: number;
}

export interface TimelineSegment {
  id: number;
  fileId: number;
  startAt: string;
  endAt: string;
  durationSec: number;
  playbackUrl: string;
  fileOffsetSec: number;
  status: string;
  issueFlags: string[];
}

export interface TimelineGap {
  startAt: string;
  endAt: string;
  durationSec: number;
}

export interface TimelineResponse {
  day: string;
  timezone: string;
  summary: TimelineSummary;
  segments: TimelineSegment[];
  gaps: TimelineGap[];
}

export interface LocateGap {
  startAt: string;
  endAt: string;
}

export interface LocateResponse {
  found: boolean;
  segment: TimelineSegment | null;
  seekOffsetSec: number | null;
  gap: LocateGap | null;
  nextSegment: TimelineSegment | null;
}

export interface RebuildResponse {
  accepted: boolean;
  jobId: number;
  scope: string;
  day: string | null;
}

export interface CameraItem {
  cameraNo: number;
  label: string;
}

export interface AuthStatus {
  authenticated: boolean;
}
