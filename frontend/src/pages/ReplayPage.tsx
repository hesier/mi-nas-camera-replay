import { useEffect, useState } from 'react';

import { CameraPicker } from '../components/CameraPicker';
import { DatePicker } from '../components/DatePicker';
import { PlaybackControls } from '../components/PlaybackControls';
import { PlayerPanel } from '../components/PlayerPanel';
import { TimelineBar } from '../components/TimelineBar';
import { useCameras } from '../hooks/useCameras';
import { usePlaybackController } from '../hooks/usePlaybackController';
import { useDays } from '../hooks/useDays';
import { useTimeline } from '../hooks/useTimeline';
import { formatClockWithSeconds } from '../utils/time';

interface ReplayPageProps {
  onLogout?: () => Promise<void>;
}

export function ReplayPage({ onLogout }: ReplayPageProps) {
  const { data: cameras, error: camerasError, loading: camerasLoading } = useCameras();
  const [selectedCameraNo, setSelectedCameraNo] = useState<number | null>(null);
  const [logoutError, setLogoutError] = useState<string | null>(null);
  const [selectedDay, setSelectedDay] = useState<string | null>(null);
  const { data: days, error: daysError, loading: daysLoading } = useDays(selectedCameraNo);
  const timelineDay = days.length > 0 ? selectedDay : null;
  const { data: timeline, error: timelineError, loading: timelineLoading } = useTimeline(
    selectedCameraNo ?? 1,
    timelineDay,
  );
  const stableTimeline = timelineDay == null ? null : timeline;
  const playback = usePlaybackController({
    cameraNo: selectedCameraNo ?? 1,
    day: selectedDay,
    timeline: stableTimeline,
  });

  useEffect(() => {
    if (cameras.length === 0) {
      setSelectedCameraNo(null);
      return;
    }

    setSelectedCameraNo((current) => {
      if (current != null && cameras.some((camera) => camera.cameraNo === current)) {
        return current;
      }
      return cameras[0].cameraNo;
    });
  }, [cameras]);

  useEffect(() => {
    setSelectedDay((current) => {
      if (days.length === 0) {
        return null;
      }
      if (current != null && days.some((day) => day.day === current)) {
        return current;
      }
      return days[0].day;
    });
  }, [days, selectedCameraNo]);

  async function handleLogout() {
    if (onLogout == null) {
      return;
    }

    setLogoutError(null);
    try {
      await onLogout();
    } catch {
      setLogoutError('退出登录失败，请稍后重试。');
    }
  }

  return (
    <main className="app-shell">
      <section className="hero-panel">
        <h1>监控回放工作台</h1>
        <p className="hero-copy">
          按天查看、时间轴定位与基础回放。
        </p>
        <button className="secondary-button" type="button" onClick={() => void handleLogout()}>
          退出登录
        </button>
        {logoutError != null ? <p className="error-text">{logoutError}</p> : null}
      </section>

      <section className="top-grid">
        <section className="panel compact-panel">
          {camerasError ? <p className="error-text">{camerasError}</p> : null}
          {camerasLoading ? <p className="panel-note compact-loading-note">通道加载中...</p> : null}
          {daysError ? <p className="error-text">{daysError}</p> : null}
          {daysLoading ? <p className="panel-note compact-loading-note">日期加载中...</p> : null}
          {cameras.length > 1 ? (
            <CameraPicker
              cameras={cameras}
              selectedCameraNo={selectedCameraNo}
              onSelectCamera={(cameraNo) => {
                setSelectedCameraNo(cameraNo);
                setSelectedDay(null);
              }}
            />
          ) : null}
          <DatePicker
            days={days}
            selectedDay={selectedDay}
            onSelectDay={(day) => {
              setSelectedDay(day);
            }}
          />
        </section>

        <PlaybackControls
          playbackRate={playback.playbackRate}
          selectedAtLabel={
            selectedDay == null
              ? '未选择日期'
              : `${selectedDay} ${formatClockWithSeconds(playback.selectedSecond)}`
          }
          onPlaybackRateChange={playback.setPlaybackRate}
        />
      </section>

      <PlayerPanel
        activeSegment={playback.activeSegment}
        gapMessage={playback.gapMessage}
        playbackRate={playback.playbackRate}
        playbackState={playback.playbackState}
        seekOffsetSec={playback.seekOffsetSec}
        selectedAtLabel={
          selectedDay == null
            ? '未选择日期'
            : `${selectedDay} ${formatClockWithSeconds(playback.selectedSecond)}`
        }
        onEnded={playback.handleSegmentEnded}
      >
        {timelineError ? <p className="error-text">{timelineError}</p> : null}
        {timelineLoading ? <p className="panel-note">时间轴加载中...</p> : null}
        {!daysLoading && !timelineLoading && selectedDay == null && days.length === 0 ? (
          <p className="empty-text">该通道暂无录像</p>
        ) : null}
        {selectedDay != null && stableTimeline != null ? (
          <TimelineBar
            day={selectedDay}
            embedded
            segments={stableTimeline.segments}
            gaps={stableTimeline.gaps}
            selectedAt={playback.selectedAt}
            onSelectTime={(second) => {
              void playback.selectSecond(second);
            }}
          />
        ) : null}
      </PlayerPanel>
    </main>
  );
}
