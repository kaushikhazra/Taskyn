import { Button, Icon } from '@/components/atoms';

interface EmptyPlanStateProps {
  date: string;
  onCreatePlan: () => void;
  isCreating?: boolean;
}

export function EmptyPlanState({ date, onCreatePlan, isCreating = false }: EmptyPlanStateProps) {
  return (
    <div className="plan-empty-state">
      <Icon name="planner" size={48} className="plan-empty-state__icon" />
      <p className="plan-empty-state__message">No plan for {date}</p>
      <Button
        variant="primary"
        onClick={onCreatePlan}
        disabled={isCreating}
        icon={<Icon name="plus" size={16} />}
      >
        {isCreating ? 'Creating...' : 'Create Plan'}
      </Button>
    </div>
  );
}
