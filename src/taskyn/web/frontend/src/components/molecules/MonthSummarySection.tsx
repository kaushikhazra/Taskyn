import { OutcomeBar } from '@/components/atoms';
import { StatCard } from '@/components/molecules/StatCard';
import type { MonthlyPlan, MonthlyMilestone } from '@/types';

interface MonthSummarySectionProps {
  plan: MonthlyPlan;
}

function formatMinutes(m: number): string {
  if (m === 0) return '0m';
  const h = Math.floor(m / 60);
  const r = m % 60;
  if (h === 0) return `${r}m`;
  if (r === 0) return `${h}h`;
  return `${h}h ${r}m`;
}

export function MonthSummarySection({ plan }: MonthSummarySectionProps) {
  const {
    days_in_month,
    days_with_plans,
    total_planned_items,
    total_planned_minutes,
    outcomes,
    actual_minutes,
    milestones,
  } = plan;

  const activeMilestones = milestones.filter((ms: MonthlyMilestone) => ms.status !== 'completed');

  return (
    <div className="month-summary">
      <div className="month-summary__stats">
        <StatCard label="Days Planned" value={`${days_with_plans}/${days_in_month}`} />
        <StatCard label="Items" value={total_planned_items} />
        <StatCard label="Planned" value={formatMinutes(total_planned_minutes)} />
        <StatCard label="Actual" value={formatMinutes(actual_minutes)} />
      </div>

      <div className="month-summary__bar">
        <OutcomeBar counts={outcomes} size="normal" />
      </div>

      {activeMilestones.length > 0 && (
        <div className="month-summary__milestones">
          <span className="month-summary__milestones-label">Active milestones</span>
          <ul className="month-summary__milestones-list">
            {activeMilestones.map((ms: MonthlyMilestone) => (
              <li key={ms.id} className="month-summary__milestone">
                <span className="month-summary__milestone-name">{ms.name}</span>
                <span className="month-summary__milestone-project">{ms.project_name}</span>
                {ms.target_date && (
                  <span className="month-summary__milestone-date">
                    due {new Date(ms.target_date + 'T00:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                  </span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
