import { MonthSummarySection } from '@/components/molecules/MonthSummarySection';
import { MonthCalendarGrid } from '@/components/organisms/MonthCalendarGrid';
import type { MonthlyPlan } from '@/types';

interface MonthPanelProps {
  monthlyPlan: MonthlyPlan;
  onDayClick: (date: string) => void;
}

export function MonthPanel({ monthlyPlan, onDayClick }: MonthPanelProps) {
  return (
    <div className="month-panel">
      <MonthSummarySection plan={monthlyPlan} />
      <MonthCalendarGrid
        year={monthlyPlan.year}
        month={monthlyPlan.month}
        days={monthlyPlan.days}
        onDayClick={onDayClick}
      />
    </div>
  );
}
