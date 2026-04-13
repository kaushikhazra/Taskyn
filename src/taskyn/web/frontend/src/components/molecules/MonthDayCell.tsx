import { OutcomeBar } from '@/components/atoms';
import type { MonthlyDaySummary } from '@/types';

interface MonthDayCellProps {
  day: number;
  /** ISO date for this cell — used to navigate on click. */
  cellDate: string;
  daySummary?: MonthlyDaySummary;
  isCurrentMonth: boolean;
  isToday: boolean;
  onClick: (date: string) => void;
}

export function MonthDayCell({ day, cellDate, daySummary, isCurrentMonth, isToday, onClick }: MonthDayCellProps) {
  const hasPlan = !!daySummary;
  const isCompleted = daySummary?.status === 'completed';

  const className = [
    'month-day-cell',
    !isCurrentMonth && 'month-day-cell--outside',
    isToday && 'month-day-cell--today',
    hasPlan && 'month-day-cell--has-plan',
    isCompleted && 'month-day-cell--completed',
  ]
    .filter(Boolean)
    .join(' ');

  const handleClick = () => {
    if (!isCurrentMonth) return;
    onClick(cellDate);
  };

  return (
    <div
      className={className}
      onClick={isCurrentMonth ? handleClick : undefined}
      role={isCurrentMonth ? 'button' : undefined}
      tabIndex={isCurrentMonth ? 0 : undefined}
    >
      <div className="month-day-cell__header">
        <span className="month-day-cell__day">{day}</span>
        {isCompleted && <span className="month-day-cell__done-dot" />}
      </div>

      {hasPlan && (
        <>
          <OutcomeBar counts={daySummary.outcomes} size="mini" />
          <span className="month-day-cell__count">
            {daySummary.item_count} item{daySummary.item_count !== 1 ? 's' : ''}
          </span>
        </>
      )}
    </div>
  );
}
