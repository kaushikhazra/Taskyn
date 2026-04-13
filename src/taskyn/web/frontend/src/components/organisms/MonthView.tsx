import { useMonthlyPlan } from '@/hooks/queries/usePlans';
import { MonthPanel } from '@/components/organisms/MonthPanel';

interface MonthViewProps {
  date: string; // ISO date (month start)
  actor: string;
  onDateChange: (date: string, view: 'day') => void;
}

export function MonthView({ date, actor, onDateChange }: MonthViewProps) {
  const d = new Date(date + 'T00:00:00');
  const year = d.getFullYear();
  const month = d.getMonth() + 1;

  const { data: monthlyPlan, isLoading } = useMonthlyPlan(year, month, actor);

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

  if (!monthlyPlan) {
    return (
      <div className="planner-view">
        <div className="plan-empty-state">
          <p className="plan-empty-state__message">No monthly data available.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="planner-view">
      <MonthPanel
        monthlyPlan={monthlyPlan}
        onDayClick={(day) => onDateChange(day, 'day')}
      />
    </div>
  );
}
