import { Button } from '@/components/atoms';
import type { PlannerView } from '@/hooks/usePlannerParams';

interface ViewSwitcherProps {
  view: PlannerView;
  onChange: (view: PlannerView) => void;
  className?: string;
}

const VIEWS: { value: PlannerView; label: string }[] = [
  { value: 'day', label: 'Day' },
  { value: 'week', label: 'Week' },
  { value: 'month', label: 'Month' },
];

export function ViewSwitcher({ view, onChange, className = '' }: ViewSwitcherProps) {
  return (
    <div className={`view-switcher ${className}`} role="group" aria-label="View">
      {VIEWS.map(({ value, label }) => (
        <Button
          key={value}
          variant={value === view ? 'primary' : 'ghost'}
          size="sm"
          onClick={() => onChange(value)}
          aria-pressed={value === view}
        >
          {label}
        </Button>
      ))}
    </div>
  );
}
