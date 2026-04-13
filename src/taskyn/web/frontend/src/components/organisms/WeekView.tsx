import { useWeeklyPlan } from '@/hooks/queries/usePlans';
import { WeekPanel } from '@/components/organisms/WeekPanel';

interface WeekViewProps {
  date: string;
  actor: string;
  onDateChange: (date: string, view: 'day') => void;
}

export function WeekView({ date, actor, onDateChange }: WeekViewProps) {
  const { data: weeklyPlan, isLoading } = useWeeklyPlan(date, actor);

  if (isLoading) {
    return (
      <div className="planner-view">
        <div className="plan-loading">
          <div className="skeleton skeleton--block" />
          <div className="skeleton skeleton--block" />
          <div className="skeleton skeleton--block" />
        </div>
      </div>
    );
  }

  if (!weeklyPlan) {
    return (
      <div className="planner-view">
        <div className="plan-empty-state">
          <p className="plan-empty-state__message">No weekly data available.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="planner-view">
      <WeekPanel
        weeklyPlan={weeklyPlan}
        onDayClick={(day) => onDateChange(day, 'day')}
      />
    </div>
  );
}
