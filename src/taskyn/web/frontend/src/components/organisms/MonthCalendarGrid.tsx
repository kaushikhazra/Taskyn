import { useMemo } from 'react';
import { MonthDayCell } from '@/components/molecules/MonthDayCell';
import type { MonthlyDaySummary } from '@/types';

interface MonthCalendarGridProps {
  year: number;
  month: number; // 1-12
  days: MonthlyDaySummary[];
  onDayClick: (date: string) => void;
}

const DAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

function toISODate(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

interface CalendarCell {
  date: Date;
  day: number;
  cellDate: string;
  isCurrentMonth: boolean;
  isToday: boolean;
  summary?: MonthlyDaySummary;
}

export function MonthCalendarGrid({ year, month, days, onDayClick }: MonthCalendarGridProps) {
  const cells = useMemo(() => {
    const today = toISODate(new Date());

    // Build lookup from ISO date -> summary
    const summaryMap = new Map<string, MonthlyDaySummary>();
    days.forEach((d) => summaryMap.set(d.date, d));

    // First day of month
    const firstOfMonth = new Date(year, month - 1, 1);
    // Day of week for first (0=Sun, 1=Mon, ...) -> convert to Mon-based (0=Mon)
    const firstDow = firstOfMonth.getDay();
    const startOffset = firstDow === 0 ? 6 : firstDow - 1; // days from Monday

    // Last day of month
    const lastOfMonth = new Date(year, month, 0);
    const daysInMonth = lastOfMonth.getDate();

    // Build cells: fill in previous month, current month, next month
    const result: CalendarCell[] = [];

    // Previous month fill
    for (let i = startOffset - 1; i >= 0; i--) {
      const d = new Date(year, month - 1, -i);
      const iso = toISODate(d);
      result.push({
        date: d,
        day: d.getDate(),
        cellDate: iso,
        isCurrentMonth: false,
        isToday: iso === today,
        summary: summaryMap.get(iso),
      });
    }

    // Current month
    for (let day = 1; day <= daysInMonth; day++) {
      const d = new Date(year, month - 1, day);
      const iso = toISODate(d);
      result.push({
        date: d,
        day,
        cellDate: iso,
        isCurrentMonth: true,
        isToday: iso === today,
        summary: summaryMap.get(iso),
      });
    }

    // Next month fill (to complete the grid to a multiple of 7)
    const remaining = (7 - (result.length % 7)) % 7;
    for (let i = 1; i <= remaining; i++) {
      const d = new Date(year, month, i);
      const iso = toISODate(d);
      result.push({
        date: d,
        day: d.getDate(),
        cellDate: iso,
        isCurrentMonth: false,
        isToday: iso === today,
        summary: summaryMap.get(iso),
      });
    }

    return result;
  }, [year, month, days]);

  return (
    <div className="month-calendar-grid">
      {/* Header row */}
      {DAY_LABELS.map((label) => (
        <div key={label} className="month-calendar-grid__header">
          {label}
        </div>
      ))}

      {/* Day cells */}
      {cells.map((cell) => (
        <MonthDayCell
          key={cell.cellDate}
          day={cell.day}
          cellDate={cell.cellDate}
          daySummary={cell.summary}
          isCurrentMonth={cell.isCurrentMonth}
          isToday={cell.isToday}
          onClick={onDayClick}
        />
      ))}
    </div>
  );
}
