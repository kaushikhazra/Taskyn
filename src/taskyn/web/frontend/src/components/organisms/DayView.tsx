import { useState, useMemo, useCallback } from 'react';
import { usePlan } from '@/hooks/queries/usePlans';
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
  const { data: plan, isLoading } = usePlan(date, actor);
  const createPlan = useCreatePlan();
  const deletePlan = useDeletePlan();

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
            queryClient.invalidateQueries({ queryKey: queryKeys.plans.byDate(date, actor) });
            addToast('info', 'A plan already exists for this date');
          }
        },
      },
    );
  }, [createPlan, date, actor, queryClient, addToast]);

  // ── Plan deletion with conditional confirmation (M-04) ────────
  const handleDeleteRequest = useCallback(() => {
    setDeleteConfirmOpen(true);
  }, []);

  const handleDeleteConfirm = useCallback(() => {
    if (!plan) return;
    deletePlan.mutate(plan.id);
    setDeleteConfirmOpen(false);
  }, [plan, deletePlan]);

  const recordedOutcomeCount = useMemo(() => {
    if (!plan) return 0;
    return plan.items.filter((item) => item.outcome !== 'pending').length;
  }, [plan]);

  // ── CarryOver success handler ─────────────────────────────────
  const handleCarryOverSuccess = useCallback(
    (targetDate: string) => {
      if (onNavigateToDate) onNavigateToDate(targetDate);
    },
    [onNavigateToDate],
  );

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

  if (!plan) {
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
      <DayPlanPanel
        plan={plan}
        date={date}
        actor={actor}
        onCarryOver={() => setCarryOverOpen(true)}
        onAddItem={() => setNodePickerOpen(true)}
        onDeletePlan={handleDeleteRequest}
      />

      {/* NodePickerModal (US-7) */}
      <NodePickerModal
        open={nodePickerOpen}
        onClose={() => setNodePickerOpen(false)}
        planId={plan.id}
      />

      {/* CarryOverModal (US-11) */}
      {carryOverOpen && (
        <CarryOverModal
          open={carryOverOpen}
          onClose={() => setCarryOverOpen(false)}
          plan={plan}
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
