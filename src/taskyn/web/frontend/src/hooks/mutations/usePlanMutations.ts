import { useMutation, useQueryClient } from '@tanstack/react-query';
// TODO: plansApi will be provided by the API client module (parallel worker)
import { plansApi } from '@/api/plans';
import { queryKeys } from '@/api/queryKeys';
import { useToast } from '@/hooks/useToast';
import type {
  Plan, PlanCreate, PlanUpdate,
  PlanItemAdd, PlanItemUpdate,
  CarryOverRequest, CarryOverResult,
} from '@/types';

// ── Invalidation helpers ──────────────────────────────────────

/** Invalidate all plan queries (lists, byDate, detail, aggregates). */
function usePlanInvalidation() {
  const qc = useQueryClient();
  return () => {
    qc.invalidateQueries({ queryKey: queryKeys.plans.all() });
  };
}

/** Invalidate plan queries + dashboard (plan changes affect dashboard stats). */
function usePlanAndDashboardInvalidation() {
  const qc = useQueryClient();
  return () => {
    qc.invalidateQueries({ queryKey: queryKeys.plans.all() });
    qc.invalidateQueries({ queryKey: queryKeys.dashboard.all() });
  };
}

// ── Plan CRUD mutations ───────────────────────────────────────

export function useCreatePlan() {
  const invalidate = usePlanAndDashboardInvalidation();
  const { addToast } = useToast();

  return useMutation({
    mutationFn: (data: PlanCreate) => plansApi.create(data),
    onSuccess: () => {
      invalidate();
      addToast('success', 'Plan created');
    },
    onError: (err: Error) => addToast('error', err.message),
  });
}

export function useUpdatePlan() {
  const invalidate = usePlanInvalidation();
  const { addToast } = useToast();

  return useMutation({
    mutationFn: ({ planId, data }: { planId: string; data: PlanUpdate }) =>
      plansApi.update(planId, data),
    onSuccess: () => {
      invalidate();
    },
    onError: (err: Error) => addToast('error', err.message),
  });
}

export function useDeletePlan() {
  const invalidate = usePlanAndDashboardInvalidation();
  const { addToast } = useToast();

  return useMutation({
    mutationFn: (planId: string) => plansApi.delete(planId),
    onSuccess: () => {
      invalidate();
      addToast('success', 'Plan deleted');
    },
    onError: (err: Error) => addToast('error', err.message),
  });
}

// ── Plan item mutations (standard) ───────────────────────────

export function useAddPlanItem() {
  const invalidate = usePlanInvalidation();
  const { addToast } = useToast();

  return useMutation({
    mutationFn: ({ planId, data }: { planId: string; data: PlanItemAdd }) =>
      plansApi.addItem(planId, data),
    onSuccess: () => {
      invalidate();
      addToast('success', 'Item added to plan');
    },
    onError: (err: Error) => addToast('error', err.message),
  });
}

export function useRemovePlanItem() {
  const invalidate = usePlanInvalidation();
  const { addToast } = useToast();

  return useMutation({
    mutationFn: (itemId: string) => plansApi.removeItem(itemId),
    onSuccess: () => {
      invalidate();
      addToast('success', 'Item removed');
    },
    onError: (err: Error) => addToast('error', err.message),
  });
}

// ── Optimistic: reorder item (drag-and-drop — US-5) ─────────

/**
 * Optimistic reorder — moves the item visually on drag, reverts on error.
 *
 * The cache key is `byDate(date, actor)` because the day-view plan is the
 * active query when the user drags items.
 *
 * N-01 fix: newPosition is 1-based from the UI; splice uses `newPosition - 1`
 * for the 0-based insert index.
 */
export function useReorderPlanItem(date: string, actor: string) {
  const qc = useQueryClient();
  const { addToast } = useToast();
  const planKey = queryKeys.plans.byDate(date, actor);

  return useMutation({
    mutationFn: ({ itemId, newPosition }: { itemId: string; newPosition: number }) =>
      plansApi.reorderItem(itemId, { new_position: newPosition }),

    onMutate: async ({ itemId, newPosition }) => {
      await qc.cancelQueries({ queryKey: planKey });
      const previous = qc.getQueryData<Plan>(planKey);

      qc.setQueryData<Plan | null>(planKey, (old) => {
        if (!old) return old;
        const items = [...old.items];

        // Remove dragged item
        const dragIndex = items.findIndex((i) => i.id === itemId);
        if (dragIndex === -1) return old;
        const dragged = items.splice(dragIndex, 1)[0];
        if (!dragged) return old;

        // Insert at new position (1-based newPosition → 0-based splice index)
        const insertAt = Math.min(newPosition - 1, items.length);
        items.splice(insertAt, 0, dragged);

        // Recompute display_order to match visual order (1-based — see backend F-05)
        const reordered = items.map((item, idx) => ({
          ...item,
          display_order: idx + 1,
        }));

        return { ...old, items: reordered };
      });

      return { previous };
    },

    onError: (_err, _vars, context) => {
      if (context?.previous) qc.setQueryData(planKey, context.previous);
      addToast('error', 'Failed to reorder');
    },

    onSettled: () => {
      qc.invalidateQueries({ queryKey: queryKeys.plans.all() });
    },
  });
}

// ── Optimistic: update item outcome (US-3) ───────────────────

/**
 * Optimistic outcome update — marks item visually before server confirms.
 *
 * Used for the primary interaction: clicking completed / partial / dropped
 * on a plan item in the day view.
 */
export function useUpdatePlanItem(date: string, actor: string) {
  const qc = useQueryClient();
  const { addToast } = useToast();
  const planKey = queryKeys.plans.byDate(date, actor);

  return useMutation({
    mutationFn: ({ itemId, data }: { itemId: string; data: PlanItemUpdate }) =>
      plansApi.updateItem(itemId, data),

    onMutate: async ({ itemId, data }) => {
      await qc.cancelQueries({ queryKey: planKey });
      const previous = qc.getQueryData<Plan>(planKey);

      qc.setQueryData<Plan | null>(planKey, (old) => {
        if (!old) return old;
        return {
          ...old,
          items: old.items.map((item) =>
            item.id === itemId ? { ...item, ...data } : item,
          ),
        };
      });

      return { previous };
    },

    onError: (_err, _vars, context) => {
      if (context?.previous) qc.setQueryData(planKey, context.previous);
      addToast('error', 'Failed to update item');
    },

    onSettled: () => {
      // Broader invalidation — outcome changes affect vsActual & weekly/monthly aggregates
      qc.invalidateQueries({ queryKey: queryKeys.plans.all() });
    },
  });
}

// ── Carry-over mutation (US-11) ──────────────────────────────

export function useCarryOverPlan() {
  const invalidate = usePlanAndDashboardInvalidation();
  const { addToast } = useToast();

  return useMutation({
    mutationFn: ({ planId, data }: { planId: string; data: CarryOverRequest }) =>
      plansApi.carryOver(planId, data),
    onSuccess: (result: CarryOverResult) => {
      invalidate();
      const msg = result.skipped.length > 0
        ? `Carried ${result.carried_count} items (${result.skipped.length} skipped)`
        : `Carried ${result.carried_count} items`;
      addToast('success', msg);
    },
    onError: (err: Error) => addToast('error', err.message),
  });
}
