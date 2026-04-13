import { WeekSummaryBar } from '@/components/molecules/WeekSummaryBar';
import { WeekGrid } from '@/components/organisms/WeekGrid';
import type { WeeklyPlan } from '@/types';

interface WeekPanelProps {
  weeklyPlan: WeeklyPlan;
  onDayClick: (date: string) => void;
}

export function WeekPanel({ weeklyPlan, onDayClick }: WeekPanelProps) {
  return (
    <div className="week-panel">
      <WeekSummaryBar summary={weeklyPlan.summary} />
      <WeekGrid days={weeklyPlan.days} onDayClick={onDayClick} />
    </div>
  );
}
