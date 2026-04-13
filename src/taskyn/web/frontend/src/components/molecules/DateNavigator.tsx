import { useCallback, useMemo } from 'react';
import { Button } from '@/components/atoms';
import type { PlannerView } from '@/hooks/usePlannerParams';

interface DateNavigatorProps {
  date: string;
  view: PlannerView;
  onChange: (date: string) => void;
  className?: string;
}

function toISODate(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

function parseDate(iso: string): Date {
  return new Date(iso + 'T00:00:00');
}

function addDays(d: Date, n: number): Date {
  const copy = new Date(d);
  copy.setDate(copy.getDate() + n);
  return copy;
}

function addMonths(d: Date, n: number): Date {
  const copy = new Date(d);
  copy.setMonth(copy.getMonth() + n);
  return copy;
}

const SHORT_MONTHS = [
  'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
];
const FULL_MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
];
const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

function formatDateLabel(date: Date, view: PlannerView): string {
  if (view === 'day') {
    // Apr 12, 2026 (Sun)
    const m = SHORT_MONTHS[date.getMonth()];
    const d = date.getDate();
    const y = date.getFullYear();
    const dow = DAYS[date.getDay()];
    return `${m} ${d}, ${y} (${dow})`;
  }
  if (view === 'week') {
    // Apr 6 - 12, 2026
    const end = addDays(date, 6);
    const ms = SHORT_MONTHS[date.getMonth()];
    const me = SHORT_MONTHS[end.getMonth()];
    if (date.getMonth() === end.getMonth()) {
      return `${ms} ${date.getDate()} - ${end.getDate()}, ${end.getFullYear()}`;
    }
    return `${ms} ${date.getDate()} - ${me} ${end.getDate()}, ${end.getFullYear()}`;
  }
  // month: April 2026
  return `${FULL_MONTHS[date.getMonth()]} ${date.getFullYear()}`;
}

function todayLabel(view: PlannerView): string {
  if (view === 'week') return 'This Week';
  if (view === 'month') return 'This Month';
  return 'Today';
}

export function DateNavigator({ date, view, onChange, className = '' }: DateNavigatorProps) {
  const parsed = useMemo(() => parseDate(date), [date]);
  const label = useMemo(() => formatDateLabel(parsed, view), [parsed, view]);

  const goPrev = useCallback(() => {
    if (view === 'day') onChange(toISODate(addDays(parsed, -1)));
    else if (view === 'week') onChange(toISODate(addDays(parsed, -7)));
    else onChange(toISODate(addMonths(parsed, -1)));
  }, [parsed, view, onChange]);

  const goNext = useCallback(() => {
    if (view === 'day') onChange(toISODate(addDays(parsed, 1)));
    else if (view === 'week') onChange(toISODate(addDays(parsed, 7)));
    else onChange(toISODate(addMonths(parsed, 1)));
  }, [parsed, view, onChange]);

  const goToday = useCallback(() => {
    onChange(toISODate(new Date()));
  }, [onChange]);

  return (
    <div className={`date-navigator ${className}`}>
      <Button variant="ghost" size="sm" onClick={goPrev} aria-label="Previous">
        <svg viewBox="0 0 24 24" width={16} height={16} stroke="currentColor" fill="none" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
          <polyline points="15 18 9 12 15 6" />
        </svg>
      </Button>
      <span className="date-navigator__label">{label}</span>
      <Button variant="ghost" size="sm" onClick={goNext} aria-label="Next">
        <svg viewBox="0 0 24 24" width={16} height={16} stroke="currentColor" fill="none" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
          <polyline points="9 6 15 12 9 18" />
        </svg>
      </Button>
      <Button variant="ghost" size="sm" onClick={goToday}>
        {todayLabel(view)}
      </Button>
    </div>
  );
}
