const DAY_SECONDS = 24 * 60 * 60;

function pad(value: number): string {
  return value.toString().padStart(2, '0');
}

export function formatClock(secondOfDay: number): string {
  const normalized = Math.max(0, Math.min(DAY_SECONDS - 1, Math.floor(secondOfDay)));
  const hours = Math.floor(normalized / 3600);
  const minutes = Math.floor((normalized % 3600) / 60);
  return `${pad(hours)}:${pad(minutes)}`;
}

export function formatClockWithSeconds(secondOfDay: number): string {
  const normalized = Math.max(0, Math.min(DAY_SECONDS - 1, Math.floor(secondOfDay)));
  const hours = Math.floor(normalized / 3600);
  const minutes = Math.floor((normalized % 3600) / 60);
  const seconds = normalized % 60;
  return `${pad(hours)}:${pad(minutes)}:${pad(seconds)}`;
}

export function isoToSecondOfDay(isoValue: string): number {
  const match = isoValue.match(/T(\d{2}):(\d{2}):(\d{2})/);
  if (match == null) {
    throw new Error(`invalid iso datetime: ${isoValue}`);
  }

  const [, hoursText, minutesText, secondsText] = match;
  return (
    Number(hoursText) * 3600 +
    Number(minutesText) * 60 +
    Number(secondsText)
  );
}

export function secondOfDayToIso(day: string, secondOfDay: number): string {
  const normalized = Math.max(0, Math.min(DAY_SECONDS - 1, Math.floor(secondOfDay)));
  const hours = Math.floor(normalized / 3600);
  const minutes = Math.floor((normalized % 3600) / 60);
  const seconds = normalized % 60;
  return `${day}T${pad(hours)}:${pad(minutes)}:${pad(seconds)}+08:00`;
}
