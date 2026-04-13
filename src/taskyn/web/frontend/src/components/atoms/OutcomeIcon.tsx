import type { PlanOutcome } from '@/types';

interface OutcomeIconProps {
  outcome: PlanOutcome;
  size?: number;
  className?: string;
}

const OUTCOME_CLASSES: Record<PlanOutcome, string> = {
  pending: 'outcome-icon--pending',
  completed: 'outcome-icon--completed',
  partial: 'outcome-icon--partial',
  dropped: 'outcome-icon--dropped',
  carried_over: 'outcome-icon--carried',
};

export function OutcomeIcon({ outcome, size = 18, className = '' }: OutcomeIconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      width={size}
      height={size}
      className={`outcome-icon ${OUTCOME_CLASSES[outcome]} ${className}`}
      stroke="currentColor"
      fill="none"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-label={outcome}
    >
      {outcome === 'pending' && <circle cx="12" cy="12" r="8" />}
      {outcome === 'completed' && (
        <>
          <circle cx="12" cy="12" r="8" />
          <polyline points="9 12 11 14 15 10" />
        </>
      )}
      {outcome === 'partial' && (
        <>
          <circle cx="12" cy="12" r="8" />
          <path d="M12 4a8 8 0 0 1 0 16" fill="currentColor" opacity={0.3} />
        </>
      )}
      {outcome === 'dropped' && (
        <>
          <circle cx="12" cy="12" r="8" />
          <line x1="9" y1="9" x2="15" y2="15" />
          <line x1="15" y1="9" x2="9" y2="15" />
        </>
      )}
      {outcome === 'carried_over' && (
        <>
          <circle cx="12" cy="12" r="8" />
          <polyline points="10 9 14 12 10 15" />
        </>
      )}
    </svg>
  );
}
