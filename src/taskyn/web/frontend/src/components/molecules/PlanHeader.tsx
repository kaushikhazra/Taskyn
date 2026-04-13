import { useState } from 'react';
import { Badge, Button, Icon } from '@/components/atoms';
import type { Plan } from '@/types';

interface PlanHeaderProps {
  plan: Plan;
  onCompletePlan: () => void;
  onCarryOver: () => void;
  onToggleVsActual: () => void;
  onDeletePlan: () => void;
  showVsActual: boolean;
  /** Pending item titles — non-empty disables the Complete button (US-13 AC-2). */
  pendingItemTitles: string[];
  isCompleting?: boolean;
}

export function PlanHeader({
  plan,
  onCompletePlan,
  onCarryOver,
  onToggleVsActual,
  onDeletePlan,
  showVsActual,
  pendingItemTitles,
  isCompleting = false,
}: PlanHeaderProps) {
  const [notesExpanded, setNotesExpanded] = useState(false);
  const isCompleted = plan.status === 'completed';
  const hasPending = pendingItemTitles.length > 0;

  return (
    <div className="plan-header">
      <div className="plan-header__top">
        <Badge className={`plan-status-badge plan-status-badge--${plan.status}`}>
          {plan.status}
        </Badge>

        {!isCompleted && (
          <div className="plan-header__actions">
            <Button
              variant="ghost"
              size="sm"
              onClick={onToggleVsActual}
              className={showVsActual ? 'btn--active' : ''}
            >
              Plan vs Actual
            </Button>
            <Button variant="ghost" size="sm" onClick={onCarryOver}>
              Carry Over
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={onCompletePlan}
              disabled={hasPending || isCompleting}
              title={hasPending ? 'All items must have an outcome before completing' : undefined}
            >
              {isCompleting ? 'Completing...' : 'Complete Plan'}
            </Button>
            <Button variant="ghost" size="sm" onClick={onDeletePlan} title="Delete plan">
              <Icon name="trash" size={14} />
            </Button>
          </div>
        )}

        {isCompleted && (
          <div className="plan-header__actions">
            <Button
              variant="ghost"
              size="sm"
              onClick={onToggleVsActual}
              className={showVsActual ? 'btn--active' : ''}
            >
              Plan vs Actual
            </Button>
          </div>
        )}
      </div>

      {/* Completion gate warning */}
      {!isCompleted && hasPending && (
        <div className="plan-header__warning">
          <span>Pending items: </span>
          {pendingItemTitles.map((title, i) => (
            <span key={i}>
              {i > 0 && ', '}
              <strong>{title}</strong>
            </span>
          ))}
        </div>
      )}

      {/* Collapsible plan notes */}
      {plan.notes && (
        <div className="plan-header__notes">
          <button
            className="plan-header__notes-toggle"
            onClick={() => setNotesExpanded(!notesExpanded)}
            aria-expanded={notesExpanded}
          >
            <Icon name={notesExpanded ? 'chevronDown' : 'chevronRight'} size={14} />
            <span>Notes</span>
          </button>
          {notesExpanded && (
            <div className="plan-header__notes-content">{plan.notes}</div>
          )}
        </div>
      )}
    </div>
  );
}
