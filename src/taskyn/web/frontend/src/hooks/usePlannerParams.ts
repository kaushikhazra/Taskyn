import { useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';

export type PlannerView = 'day' | 'week' | 'month';

const VALID_VIEWS: PlannerView[] = ['day', 'week', 'month'];

function toISODate(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

function parseDate(value: string | null): Date {
  if (value) {
    const d = new Date(value + 'T00:00:00');
    if (!isNaN(d.getTime())) return d;
  }
  return new Date();
}

/** Snap date to the Monday of its week (ISO week starts Monday). */
function snapToWeekStart(d: Date): Date {
  const copy = new Date(d);
  const day = copy.getDay(); // 0=Sun, 1=Mon, ...
  const diff = day === 0 ? -6 : 1 - day;
  copy.setDate(copy.getDate() + diff);
  return copy;
}

/** Snap date to the first of its month. */
function snapToMonthStart(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth(), 1);
}

/** Snap a date for the given view. */
function snapDate(d: Date, view: PlannerView): Date {
  if (view === 'week') return snapToWeekStart(d);
  if (view === 'month') return snapToMonthStart(d);
  return d;
}

export interface PlannerParams {
  view: PlannerView;
  date: string;
  actor: string;
  setView: (view: PlannerView) => void;
  setDate: (date: string) => void;
  setDateAndView: (date: string, view: PlannerView) => void;
}

export function usePlannerParams(): PlannerParams {
  const [searchParams, setSearchParams] = useSearchParams();
  const { user } = useAuth();

  const rawView = searchParams.get('view');
  const view: PlannerView = rawView && VALID_VIEWS.includes(rawView as PlannerView)
    ? (rawView as PlannerView)
    : 'day';

  const rawDate = searchParams.get('date');
  const snapped = snapDate(parseDate(rawDate), view);
  const date = toISODate(snapped);

  const actor = searchParams.get('actor') ?? user?.name ?? '';

  const setView = useCallback(
    (newView: PlannerView) => {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        // Capture old view BEFORE overwriting it
        const oldView = (prev.get('view') as PlannerView) ?? 'day';
        next.set('view', newView);
        // Snap current date for the new view.
        // When switching TO day view, prefer today if today falls within the
        // currently displayed period (avoids landing on a month/week anchor like
        // the 1st of the month instead of today).
        const currentDate = parseDate(next.get('date'));
        let resolvedDate = currentDate;
        if (newView === 'day') {
          const today = new Date();
          const todayISO = toISODate(today);
          if (oldView === 'month') {
            // Today is within the displayed month
            if (
              today.getFullYear() === currentDate.getFullYear() &&
              today.getMonth() === currentDate.getMonth()
            ) {
              resolvedDate = today;
            }
          } else if (oldView === 'week') {
            // Today is within the displayed week (Mon–Sun)
            const weekStart = snapToWeekStart(currentDate);
            const weekEnd = new Date(weekStart);
            weekEnd.setDate(weekEnd.getDate() + 6);
            if (todayISO >= toISODate(weekStart) && todayISO <= toISODate(weekEnd)) {
              resolvedDate = today;
            }
          }
        }
        next.set('date', toISODate(snapDate(resolvedDate, newView)));
        return next;
      });
    },
    [setSearchParams],
  );

  const setDate = useCallback(
    (newDate: string) => {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        const currentView = (next.get('view') as PlannerView) ?? 'day';
        next.set('date', toISODate(snapDate(parseDate(newDate), currentView)));
        return next;
      });
    },
    [setSearchParams],
  );

  const setDateAndView = useCallback(
    (newDate: string, newView: PlannerView) => {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        next.set('view', newView);
        next.set('date', toISODate(snapDate(parseDate(newDate), newView)));
        return next;
      });
    },
    [setSearchParams],
  );

  return { view, date, actor, setView, setDate, setDateAndView };
}
