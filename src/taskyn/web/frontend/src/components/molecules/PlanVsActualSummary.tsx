import { StatCard } from '@/components/molecules/StatCard';
import type { PlanVsActualSummary as PlanVsActualSummaryType } from '@/types';

interface PlanVsActualSummaryProps {
  summary: PlanVsActualSummaryType;
}

/** Format minutes for display (e.g., "2h 30m" or "45m"). */
function formatMinutes(m: number): string {
  if (m === 0) return '0m';
  const hours = Math.floor(Math.abs(m) / 60);
  const mins = Math.abs(m) % 60;
  const sign = m < 0 ? '-' : '';
  if (hours > 0 && mins > 0) return `${sign}${hours}h ${mins}m`;
  if (hours > 0) return `${sign}${hours}h`;
  return `${sign}${mins}m`;
}

export function PlanVsActualSummary({ summary }: PlanVsActualSummaryProps) {
  const delta = summary.overall_delta ?? 0;
  const deltaClass = delta > 0 ? 'pva-delta--positive' : delta < 0 ? 'pva-delta--negative' : '';

  return (
    <div className="pva-summary">
      <StatCard label="Planned" value={formatMinutes(summary.total_planned_minutes)} />
      <StatCard label="Actual" value={formatMinutes(summary.total_actual_minutes)} />
      <StatCard label="Unplanned" value={formatMinutes(summary.total_unplanned_minutes)} />
      <StatCard label="Delta" value={formatMinutes(delta)} className={deltaClass} />
    </div>
  );
}
