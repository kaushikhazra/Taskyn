import { useState, useMemo, useCallback } from 'react';
import { usePlansForDate } from '@/hooks/queries/usePlans';
import { useCreatePlan, useDeletePlan } from '@/hooks/mutations/usePlanMutations';
import { useToast } from '@/hooks/useToast';
import { useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '@/api/queryKeys';
import { Button } from '@/components/atoms';
import { Modal } from '@/components/organisms/Modal';
import { EmptyPlanState } from '@/components/molecules/EmptyPlanState';
import { DayPlanPanel } from '@/components/organisms/DayPlanPanel';
import { NodePickerModal } from '@/components/organisms/NodePickerModal';
import { CarryOverModal } from '@/components/organisms/CarryOverModal';
import { useHotkeys } from '@/hooks/useHotkeys';
import type { Plan } from '@/types';

interface DayViewProps {
  date: string;
  actor: string;
  onNavigateToDate?: (date: string) => void;
}

/** Format a date for display. */
function formatDate(iso: string): string {
  const d = new Date(iso + 'T00:00:00');
  return d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' });
}

export function DayView({ date, actor, onNavigateToDate }: DayViewProps) {
  const queryClient = useQueryClient();
  const { addToast } = useToast();
  const { data: plans = [], isLoading } = usePlansForDate(date);
  const createPlan = useCreatePlan();
  const deletePlan = useDeletePlan();

  // Track which plan is the target for modal actions
  const [activePlan, setActivePlan] = useState<Plan | null>(null);

  // Modal states
  const [nodePickerOpen, setNodePickerOpen] = useState(false);
  const [carryOverOpen, setCarryOverOpen] = useState(false);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);

  // ── Plan creation with 409 conflict handler (M-05) ────────────
  const handleCreatePlan = useCallback(() => {
    createPlan.mutate(
      { date, actor },
      {
        onError: (err: Error & { status?: number }) => {
          if (err.status === 409 || err.message?.includes('409')) {
            queryClient.invalidateQueries({
              queryKey: queryKeys.plans.list({ date_from: date, date_to: date }),
            });
            addToast('info', 'A plan already exists for this date');
          }
        },
      },
    );
  }, [createPlan, date, actor, queryClient, addToast]);

  // ── Per-plan modal handlers ───────────────────────────────────
  const handleAddItem = useCallback((plan: Plan) => {
    setActivePlan(plan);
    setNodePickerOpen(true);
  }, []);

  const handleCarryOver = useCallback((plan: Plan) => {
    setActivePlan(plan);
    setCarryOverOpen(true);
  }, []);

  const handleDeleteRequest = useCallback((plan: Plan) => {
    setActivePlan(plan);
    setDeleteConfirmOpen(true);
  }, []);

  const handleDeleteConfirm = useCallback(() => {
    if (!activePlan) return;
    deletePlan.mutate(activePlan.id);
    setDeleteConfirmOpen(false);
    setActivePlan(null);
  }, [activePlan, deletePlan]);

  // ── CarryOver success handler ─────────────────────────────────
  const handleCarryOverSuccess = useCallback(
    (targetDate: string) => {
      if (onNavigateToDate) onNavigateToDate(targetDate);
    },
    [onNavigateToDate],
  );

  // ── Keyboard shortcut: A = Add Item to the first active plan ──
  const firstActivePlan = useMemo(
    () => plans.find((p) => p.status !== 'completed') ?? null,
    [plans],
  );
  useHotkeys(
    useMemo(
      () =>
        firstActivePlan
          ? [
              {
                key: 'A',
                label: 'Add Item',
                action: () => handleAddItem(firstActivePlan),
              },
            ]
          : [],
      [firstActivePlan, handleAddItem],
    ),
  );

  // ── Delete confirmation: count outcomes across active plan ────
  const recordedOutcomeCount = useMemo(() => {
    if (!activePlan) return 0;
    return activePlan.items.filter((item) => item.outcome !== 'pending').length;
  }, [activePlan]);

  // ── Render ────────────────────────────────────────────────────

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

  if (plans.length === 0) {
    return (
      <div className="planner-view">
        <EmptyPlanState
          date={date}
          onCreatePlan={handleCreatePlan}
          isCreating={createPlan.isPending}
        />
      </div>
    );
  }

  return (
    <div className="planner-view">
      {plans.map((plan) => (
        <DayPlanPanel
          key={plan.id}
          plan={plan}
          date={date}
          actor={plan.actor}
          onCarryOver={() => handleCarryOver(plan)}
          onAddItem={() => handleAddItem(plan)}
          onDeletePlan={() => handleDeleteRequest(plan)}
        />
      ))}

      {/* NodePickerModal (US-7) */}
      <NodePickerModal
        open={nodePickerOpen}
        onClose={() => setNodePickerOpen(false)}
        planId={activePlan?.id ?? ''}
      />

      {/* CarryOverModal (US-11) */}
      {carryOverOpen && activePlan && (
        <CarryOverModal
          open={carryOverOpen}
          onClose={() => setCarryOverOpen(false)}
          plan={activePlan}
          onSuccess={handleCarryOverSuccess}
        />
      )}

      {/* Delete confirmation dialog (M-04) */}
      <Modal
        open={deleteConfirmOpen}
        onClose={() => setDeleteConfirmOpen(false)}
        title="Delete Plan"
        footer={
          <>
            <Button variant="secondary" onClick={() => setDeleteConfirmOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="danger"
              onClick={handleDeleteConfirm}
              disabled={deletePlan.isPending}
            >
              {deletePlan.isPending ? 'Deleting...' : 'Delete Plan'}
            </Button>
          </>
        }
      >
        {recordedOutcomeCount > 0 ? (
          <p>
            This plan has <strong>{recordedOutcomeCount}</strong> item{recordedOutcomeCount !== 1 ? 's' : ''} with
            recorded outcomes. Deleting it will permanently remove all outcome data.
            This cannot be undone.
          </p>
        ) : (
          <p>Delete plan for {formatDate(date)}?</p>
        )}
      </Modal>
    </div>
  );
}
