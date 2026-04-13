import { useCallback, useState, type DragEvent } from 'react';
import { Badge } from '@/components/atoms';
import { DragHandle } from '@/components/atoms/DragHandle';
import { PlannedMinutes } from '@/components/atoms/PlannedMinutes';
import { OutcomeControl } from './OutcomeControl';
import { OutcomeNotes } from './OutcomeNotes';
import type { PlanItemEnriched, PlanOutcome, PlanStatus } from '@/types';

interface PlanItemRowProps {
  item: PlanItemEnriched;
  planStatus: PlanStatus;
  onOutcomeChange: (itemId: string, outcome: PlanOutcome) => void;
  onNotesChange: (itemId: string, notes: string) => void;
  onMinutesChange: (itemId: string, minutes: number | null) => void;
  onRemove: (itemId: string) => void;
  // DnD callbacks
  onDragStart: (e: DragEvent, itemId: string) => void;
  onDragOver: (e: DragEvent, index: number) => void;
  onDragLeave: () => void;
  onDrop: (e: DragEvent, index: number) => void;
  onDragEnd: () => void;
  index: number;
  isDragging: boolean;
  isDropTarget: boolean;
}

export function PlanItemRow({
  item,
  planStatus,
  onOutcomeChange,
  onNotesChange,
  onMinutesChange,
  onRemove,
  onDragStart,
  onDragOver,
  onDragLeave,
  onDrop,
  onDragEnd,
  index,
  isDragging,
  isDropTarget,
}: PlanItemRowProps) {
  const [showRemoveConfirm, setShowRemoveConfirm] = useState(false);
  const isCompleted = planStatus === 'completed';
  const isDeleted = item.node_deleted;

  const outcomeClass =
    item.outcome === 'dropped'
      ? 'plan-item--dropped'
      : item.outcome === 'carried_over'
        ? 'plan-item--carried'
        : item.outcome === 'completed'
          ? 'plan-item--completed'
          : item.outcome === 'partial'
            ? 'plan-item--partial'
            : '';

  const rowClasses = [
    'plan-item',
    outcomeClass,
    isDragging ? 'plan-item--dragging' : '',
    isDropTarget ? 'plan-item--drop-above' : '',
  ]
    .filter(Boolean)
    .join(' ');

  const handleRemoveClick = useCallback(() => {
    // US-8 AC-3: confirm if outcome is not pending
    if (item.outcome !== 'pending') {
      setShowRemoveConfirm(true);
    } else {
      onRemove(item.id);
    }
  }, [item.id, item.outcome, onRemove]);

  const handleConfirmRemove = useCallback(() => {
    setShowRemoveConfirm(false);
    onRemove(item.id);
  }, [item.id, onRemove]);

  return (
    <div
      className={rowClasses}
      draggable={!isCompleted}
      onDragStart={(e) => onDragStart(e, item.id)}
      onDragOver={(e) => onDragOver(e, index)}
      onDragLeave={onDragLeave}
      onDrop={(e) => onDrop(e, index)}
      onDragEnd={onDragEnd}
    >
      {/* Drag handle — hidden on completed plans */}
      {!isCompleted && <DragHandle />}

      {/* Node type badge */}
      {item.node_type && (
        <Badge className="plan-item__type-badge">{item.node_type}</Badge>
      )}

      {/* Title (or "(deleted)") */}
      <div className="plan-item__title">
        {isDeleted ? (
          <span className="plan-item__deleted">(deleted)</span>
        ) : (
          item.node_title ?? '(untitled)'
        )}
      </div>

      {/* Project name */}
      {item.project_name && (
        <span className="plan-item__project">{item.project_name}</span>
      )}

      {/* Planned minutes chip */}
      <PlannedMinutes
        minutes={item.planned_minutes}
        editable={!isCompleted}
        onChange={(mins) => onMinutesChange(item.id, mins)}
      />

      {/* Outcome control */}
      <OutcomeControl
        value={item.outcome}
        onChange={(outcome) => onOutcomeChange(item.id, outcome)}
        disabled={isCompleted}
      />

      {/* Outcome notes — editable even on completed plans (US-13 AC-5) */}
      <OutcomeNotes
        notes={item.outcome_notes}
        onNotesChange={(notes) => onNotesChange(item.id, notes)}
      />

      {/* Remove button — hidden on completed plans */}
      {!isCompleted && (
        <div className="plan-item__remove">
          {showRemoveConfirm ? (
            <span className="plan-item__remove-confirm">
              <span>Remove?</span>
              <button
                type="button"
                className="plan-item__remove-yes"
                onClick={handleConfirmRemove}
              >
                Yes
              </button>
              <button
                type="button"
                className="plan-item__remove-no"
                onClick={() => setShowRemoveConfirm(false)}
              >
                No
              </button>
            </span>
          ) : (
            <button
              type="button"
              className="plan-item__remove-btn"
              onClick={handleRemoveClick}
              title="Remove item"
              aria-label="Remove item"
            >
              &times;
            </button>
          )}
        </div>
      )}
    </div>
  );
}
