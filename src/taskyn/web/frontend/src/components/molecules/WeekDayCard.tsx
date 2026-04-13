import { OutcomeBar } from '@/components/atoms';
import { Badge } from '@/components/atoms';
import type { WeeklyDaySummary } from '@/types';

interface WeekDayCardProps {
  daySummary: WeeklyDaySummary;
  onClick: (date: string) => void;
}

function formatDayLabel(iso: string): string {
  const d = new Date(iso + 'T00:00:00');
  return d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
}

function formatMinutes(m: number): string {
  if (m === 0) return '0m';
  const h = Math.floor(m / 60);
  const r = m % 60;
  if (h === 0) return `${r}m`;
  if (r === 0) return `${h}h`;
  return `${h}h ${r}m`;
}

export function WeekDayCard({ daySummary, onClick }: WeekDayCardProps) {
  const { date, plan_id, status, item_count, outcomes, planned_minutes, actual_minutes } = daySummary;
  const hasPlan = plan_id !== null;
  const isCompleted = status === 'completed';

  const className = [
    'week-day-card',
    !hasPlan && 'week-day-card--no-plan',
    isCompleted && 'week-day-card--completed',
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <div className={className} onClick={() => onClick(date)} role="button" tabIndex={0}>
      <div className="week-day-card__header">
        <span className="week-day-card__label">{formatDayLabel(date)}</span>
        {hasPlan && (
          <Badge className={isCompleted ? 'badge--success' : ''}>
            {isCompleted ? 'done' : 'active'}
          </Badge>
        )}
      </div>

      {hasPlan ? (
        <>
          <div className="week-day-card__count">
            {item_count} item{item_count !== 1 ? 's' : ''}
          </div>
          <OutcomeBar counts={outcomes} size="normal" />
          <div className="week-day-card__minutes">
            <span>planned: {formatMinutes(planned_minutes)}</span>
            <span>actual: {formatMinutes(actual_minutes)}</span>
          </div>
        </>
      ) : (
        <div className="week-day-card__empty">No plan</div>
      )}
    </div>
  );
}
