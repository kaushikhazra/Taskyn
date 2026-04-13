import { useState, useMemo } from 'react';
import { Modal } from '@/components/organisms/Modal';
import { Badge, Button, Checkbox } from '@/components/atoms';
import { useCarryOverPlan } from '@/hooks/mutations/usePlanMutations';
import type { Plan, PlanItemEnriched } from '@/types';

interface CarryOverModalProps {
  open: boolean;
  onClose: () => void;
  plan: Plan;
  onSuccess: (targetDate: string) => void;
}

/** Format a date for display. */
function formatDate(iso: string): string {
  const d = new Date(iso + 'T00:00:00');
  return d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' });
}

/** Get tomorrow's date as ISO string. */
function getTomorrow(fromDate: string): string {
  const d = new Date(fromDate + 'T00:00:00');
  d.setDate(d.getDate() + 1);
  return d.toISOString().split('T')[0]!;
}

/** Outcome badge label. */
function outcomeBadgeClass(outcome: string): string {
  switch (outcome) {
    case 'completed': return 'badge-success';
    case 'partial': return 'badge-warning';
    case 'dropped': return 'badge-muted';
    case 'carried_over': return 'badge-muted';
    default: return '';
  }
}

export function CarryOverModal({ open, onClose, plan, onSuccess }: CarryOverModalProps) {
  const [targetDate, setTargetDate] = useState(() => getTomorrow(plan.date));
  const [selectedIds, setSelectedIds] = useState<Set<string>>(() => {
    // Pre-check pending + partial items; uncheck deleted-node items (M-03)
    const set = new Set<string>();
    plan.items.forEach((item) => {
      const isCarryable = item.outcome === 'pending' || item.outcome === 'partial';
      if (isCarryable && !item.node_deleted) {
        set.add(item.id);
      }
    });
    return set;
  });

  const carryOver = useCarryOverPlan();

  // Items eligible for carry-over display: pending, partial, and deleted-node items
  const eligibleItems = useMemo(
    () => plan.items.filter(
      (item) => item.outcome === 'pending' || item.outcome === 'partial',
    ),
    [plan.items],
  );

  const toggleItem = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleCarryOver = () => {
    carryOver.mutate(
      {
        planId: plan.id,
        data: {
          target_date: targetDate,
          item_ids: Array.from(selectedIds),
        },
      },
      {
        onSuccess: () => {
          onClose();
          onSuccess(targetDate);
        },
      },
    );
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={`Carry over from ${formatDate(plan.date)}`}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button
            variant="primary"
            onClick={handleCarryOver}
            disabled={selectedIds.size === 0 || carryOver.isPending}
          >
            {carryOver.isPending ? 'Carrying over...' : 'Carry Over'}
          </Button>
        </>
      }
    >
      <div className="carry-over">
        <div className="carry-over__list">
          {eligibleItems.length === 0 ? (
            <div className="carry-over__empty">No pending or partial items to carry over.</div>
          ) : (
            eligibleItems.map((item) => (
              <CarryOverItemRow
                key={item.id}
                item={item}
                checked={selectedIds.has(item.id)}
                onToggle={() => toggleItem(item.id)}
              />
            ))
          )}
        </div>

        <div className="carry-over__target">
          <label className="form-label">Target date</label>
          <input
            className="form-input"
            type="date"
            value={targetDate}
            onChange={(e) => setTargetDate(e.target.value)}
            min={getTomorrow(plan.date)}
          />
        </div>

        <div className="carry-over__summary">
          {selectedIds.size} of {eligibleItems.length} items selected
        </div>
      </div>
    </Modal>
  );
}

// ── Internal sub-component ──────────────────────────────────────

interface CarryOverItemRowProps {
  item: PlanItemEnriched;
  checked: boolean;
  onToggle: () => void;
}

function CarryOverItemRow({ item, checked, onToggle }: CarryOverItemRowProps) {
  const isDeleted = item.node_deleted;

  return (
    <div className={`carry-over__item${isDeleted ? ' carry-over__item--deleted' : ''}`}>
      <Checkbox checked={checked} onChange={onToggle} />
      {isDeleted && (
        <span className="carry-over__warning" title="This node has been deleted">
          <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" fill="none" strokeWidth="2" aria-hidden="true">
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
            <line x1="12" y1="9" x2="12" y2="13" />
            <line x1="12" y1="17" x2="12.01" y2="17" />
          </svg>
        </span>
      )}
      <span className="carry-over__title">
        {item.node_title ?? '(untitled)'}
        {isDeleted && <span className="carry-over__deleted-label"> (deleted)</span>}
      </span>
      <Badge className={outcomeBadgeClass(item.outcome)}>{item.outcome}</Badge>
    </div>
  );
}
