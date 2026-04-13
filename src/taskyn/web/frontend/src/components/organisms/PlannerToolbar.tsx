import { DateNavigator } from '@/components/molecules/DateNavigator';
import { ViewSwitcher } from '@/components/molecules/ViewSwitcher';
import type { PlannerView } from '@/hooks/usePlannerParams';

interface PlannerToolbarProps {
  date: string;
  view: PlannerView;
  onDateChange: (date: string) => void;
  onViewChange: (view: PlannerView) => void;
  className?: string;
}

export function PlannerToolbar({
  date,
  view,
  onDateChange,
  onViewChange,
  className = '',
}: PlannerToolbarProps) {
  return (
    <div className={`planner-toolbar ${className}`}>
      <DateNavigator date={date} view={view} onChange={onDateChange} />
      <ViewSwitcher view={view} onChange={onViewChange} />
    </div>
  );
}
