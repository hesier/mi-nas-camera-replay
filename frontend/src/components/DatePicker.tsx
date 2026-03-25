import type { DaySummary } from '../types/api';

interface DatePickerProps {
  days: DaySummary[];
  selectedDay: string | null;
  onSelectDay: (day: string) => void;
}

export function DatePicker({
  days,
  selectedDay,
  onSelectDay,
}: DatePickerProps) {
  return (
    <label className="field-group compact-field-group">
      <span className="field-label">回放日期</span>
      <select
        className="field-input"
        value={selectedDay ?? ''}
        onChange={(event) => onSelectDay(event.target.value)}
      >
        {days.length === 0 ? <option value="">暂无可用日期</option> : null}
        {days.map((day) => (
          <option key={day.day} value={day.day}>
            {day.day}
          </option>
        ))}
      </select>
    </label>
  );
}
