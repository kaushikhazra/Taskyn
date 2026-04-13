import type { PlanVsActualItem, UnplannedItem } from '@/types';

/** Format minutes for display. */
function formatMinutes(m: number | null): string {
  if (m === null || m === 0) return '0m';
  const hours = Math.floor(Math.abs(m) / 60);
  const mins = Math.abs(m) % 60;
  const sign = m < 0 ? '-' : '';
  if (hours > 0 && mins > 0) return `${sign}${hours}h ${mins}m`;
  if (hours > 0) return `${sign}${hours}h`;
  return `${sign}${mins}m`;
}

// ── Planned item row ─────────────────────────────────────────────

interface PlanVsActualRowProps {
  item: PlanVsActualItem;
}

export function PlanVsActualRow({ item }: PlanVsActualRowProps) {
  const delta = item.delta_minutes ?? 0;
  const deltaClass = delta > 0 ? 'pva-delta--positive' : delta < 0 ? 'pva-delta--negative' : '';

  return (
    <div className="pva-row">
      <span className="pva-row__title">{item.title ?? '(untitled)'}</span>
      <span className="pva-row__planned">{formatMinutes(item.planned_minutes)}</span>
      <span className="pva-row__actual">{formatMinutes(item.actual_minutes)}</span>
      <span className={`pva-row__delta ${deltaClass}`}>{formatMinutes(delta)}</span>
    </div>
  );
}

// ── Unplanned item row ───────────────────────────────────────────

interface UnplannedRowProps {
  item: UnplannedItem;
}

export function UnplannedRow({ item }: UnplannedRowProps) {
  return (
    <div className="pva-row pva-row--unplanned">
      <span className="pva-row__title">{item.title}</span>
      <span className="pva-row__actual">{formatMinutes(item.actual_minutes)}</span>
      <span className="pva-row__project">{item.project_name}</span>
    </div>
  );
}
