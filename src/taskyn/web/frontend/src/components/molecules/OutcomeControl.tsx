import { OutcomeIcon } from '@/components/atoms/OutcomeIcon';
import type { PlanOutcome } from '@/types';

/** The four outcomes a user can select — carried_over is display-only. */
const SELECTABLE_OUTCOMES: PlanOutcome[] = ['pending', 'completed', 'partial', 'dropped'];

const OUTCOME_LABELS: Record<PlanOutcome, string> = {
  pending: 'Pending',
  completed: 'Completed',
  partial: 'Partial',
  dropped: 'Dropped',
  carried_over: 'Carried over',
};

interface OutcomeControlProps {
  value: PlanOutcome;
  onChange: (outcome: PlanOutcome) => void;
  disabled?: boolean;
}

export function OutcomeControl({ value, onChange, disabled = false }: OutcomeControlProps) {
  // If the item has been carried over, show read-only indicator
  if (value === 'carried_over') {
    return (
      <div className="outcome-control outcome-control--readonly" role="group" aria-label="Item outcome">
        <div
          className="outcome-control__option outcome-control__option--active"
          title={OUTCOME_LABELS.carried_over}
        >
          <OutcomeIcon outcome="carried_over" />
        </div>
      </div>
    );
  }

  return (
    <div className="outcome-control" role="radiogroup" aria-label="Item outcome">
      {SELECTABLE_OUTCOMES.map((outcome) => {
        const isActive = value === outcome;
        return (
          <button
            key={outcome}
            type="button"
            className={`outcome-control__option ${isActive ? 'outcome-control__option--active' : ''}`}
            onClick={() => {
              if (!disabled && !isActive) onChange(outcome);
            }}
            disabled={disabled}
            role="radio"
            aria-checked={isActive}
            aria-label={OUTCOME_LABELS[outcome]}
            title={OUTCOME_LABELS[outcome]}
          >
            <OutcomeIcon outcome={outcome} />
          </button>
        );
      })}
    </div>
  );
}
