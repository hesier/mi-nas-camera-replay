import { useEffect, useState } from 'react';

import { DatePicker } from '../components/DatePicker';
import { PlaybackControls } from '../components/PlaybackControls';
import { PlayerPanel } from '../components/PlayerPanel';
import { TimelineBar } from '../components/TimelineBar';
import { usePlaybackController } from '../hooks/usePlaybackController';
import { useDays } from '../hooks/useDays';
import { useTimeline } from '../hooks/useTimeline';
import { formatClockWithSeconds } from '../utils/time';

export function ReplayPage() {
  const { data: days, error: daysError, loading: daysLoading } = useDays();
  const [selectedDay, setSelectedDay] = useState<string | null>(null);
  const { data: timeline, error: timelineError, loading: timelineLoading } = useTimeline(selectedDay);
  const playback = usePlaybackController({
    day: selectedDay,
    timeline,
  });

  useEffect(() => {
    if (selectedDay == null && days.length > 0) {
      setSelectedDay(days[0].day);
    }
  }, [days, selectedDay]);

  return (
    <main className="app-shell">
      <section className="hero-panel">
        <h1>监控回放工作台</h1>
        <p className="hero-copy">
          按天查看、时间轴定位与基础回放。
        </p>
      </section>

      <section className="top-grid">
        <section className="panel compact-panel">
          {daysError ? <p className="error-text">{daysError}</p> : null}
          {daysLoading ? <p className="panel-note compact-loading-note">日期加载中...</p> : null}
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
        {selectedDay != null && timeline != null ? (
          <TimelineBar
            day={selectedDay}
            embedded
            segments={timeline.segments}
            gaps={timeline.gaps}
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
