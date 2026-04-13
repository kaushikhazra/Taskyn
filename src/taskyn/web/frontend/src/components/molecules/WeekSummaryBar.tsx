import { OutcomeBar } from '@/components/atoms';
import { StatCard } from '@/components/molecules/StatCard';
import type { WeeklyPlanSummary } from '@/types';

interface WeekSummaryBarProps {
  summary: WeeklyPlanSummary;
}

function formatMinutes(m: number): string {
  if (m === 0) return '0m';
  const h = Math.floor(m / 60);
  const r = m % 60;
  if (h === 0) return `${r}m`;
  if (r === 0) return `${h}h`;
  return `${h}h ${r}m`;
}

export function WeekSummaryBar({ summary }: WeekSummaryBarProps) {
  const { total_planned_items, total_planned_minutes, outcomes, actual_minutes } = summary;

  return (
    <div className="week-summary-bar">
      <div className="week-summary-bar__stats">
        <StatCard label="Items" value={total_planned_items} />
        <StatCard label="Planned" value={formatMinutes(total_planned_minutes)} />
        <StatCard label="Actual" value={formatMinutes(actual_minutes)} />
      </div>
      <div className="week-summary-bar__bar">
        <OutcomeBar counts={outcomes} size="normal" />
      </div>
    </div>
  );
}
