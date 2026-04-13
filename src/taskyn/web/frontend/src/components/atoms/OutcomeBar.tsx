import type { PlanOutcome } from '@/types';

type OutcomeCounts = Record<PlanOutcome, number>;

interface OutcomeBarProps {
  counts: OutcomeCounts;
  size?: 'normal' | 'mini';
  className?: string;
}

const SEGMENTS: { key: PlanOutcome; cssClass: string }[] = [
  { key: 'completed', cssClass: 'outcome-bar__segment--completed' },
  { key: 'partial', cssClass: 'outcome-bar__segment--partial' },
  { key: 'dropped', cssClass: 'outcome-bar__segment--dropped' },
  { key: 'carried_over', cssClass: 'outcome-bar__segment--carried' },
  { key: 'pending', cssClass: 'outcome-bar__segment--pending' },
];

export function OutcomeBar({ counts, size = 'normal', className = '' }: OutcomeBarProps) {
  const total = Object.values(counts).reduce((sum, n) => sum + n, 0);
  if (total === 0) return null;

  return (
    <div className={`outcome-bar ${size === 'mini' ? 'outcome-bar--mini' : ''} ${className}`}>
      {SEGMENTS.map(({ key, cssClass }) => {
        const count = counts[key] ?? 0;
        if (count === 0) return null;
        const pct = (count / total) * 100;
        return (
          <div
            key={key}
            className={cssClass}
            style={{ width: `${pct}%` }}
            title={`${key}: ${count}`}
          />
        );
      })}
    </div>
  );
}
