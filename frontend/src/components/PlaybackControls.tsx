interface PlaybackControlsProps {
  playbackRate: number;
  selectedAtLabel: string;
  onPlaybackRateChange: (value: number) => void;
}

const PLAYBACK_RATES = [0.5, 1, 2, 4];

export function PlaybackControls({
  playbackRate,
  selectedAtLabel,
  onPlaybackRateChange,
}: PlaybackControlsProps) {
  return (
    <section className="panel compact-panel controls-panel">
      <div className="controls-row compact-controls-row">
        <div className="compact-time-group">
          <span className="field-label">当前时间</span>
          <div className="control-value">{selectedAtLabel}</div>
        </div>
        <label className="field-group compact-field-group inline">
          <span className="field-label">倍速</span>
          <select
            className="field-input"
            value={playbackRate}
            onChange={(event) => onPlaybackRateChange(Number(event.target.value))}
          >
            {PLAYBACK_RATES.map((rate) => (
              <option key={rate} value={rate}>
                {rate}x
              </option>
            ))}
          </select>
        </label>
      </div>
    </section>
  );
}
