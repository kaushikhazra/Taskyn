import { useCallback, useMemo, useState } from 'react';
import { PlanHeader } from '@/components/molecules/PlanHeader';
import { PlanItemList } from '@/components/organisms/PlanItemList';
import { PlanVsActualPanel } from '@/components/organisms/PlanVsActualPanel';
import { Button, Icon } from '@/components/atoms';
import {
  useUpdatePlan,
  useUpdatePlanItem,
  useReorderPlanItem,
  useRemovePlanItem,
} from '@/hooks/mutations/usePlanMutations';
import type { Plan, PlanOutcome } from '@/types';

interface DayPlanPanelProps {
  plan: Plan;
  date: string;
  actor: string;
  onCarryOver: () => void;
  onAddItem: () => void;
  onDeletePlan: () => void;
}

export function DayPlanPanel({
  plan,
  date,
  actor,
  onCarryOver,
  onAddItem,
  onDeletePlan,
}: DayPlanPanelProps) {
  const [showVsActual, setShowVsActual] = useState(false);

  const updatePlan = useUpdatePlan();
  const updateItem = useUpdatePlanItem(date, actor);
  const reorderItem = useReorderPlanItem(date, actor);
  const removeItem = useRemovePlanItem();

  const isCompleted = plan.status === 'completed';

  // US-13 AC-2: list pending item titles for completion gate
  const pendingItemTitles = useMemo(
    () =>
      plan.items
        .filter((i) => i.outcome === 'pending')
        .map((i) => i.node_title ?? '(untitled)'),
    [plan.items],
  );

  const handleCompletePlan = useCallback(() => {
    if (pendingItemTitles.length > 0) return;
    updatePlan.mutate({ planId: plan.id, data: { status: 'completed' } });
  }, [plan.id, pendingItemTitles, updatePlan]);

  const handleOutcomeChange = useCallback(
    (itemId: string, outcome: PlanOutcome) => {
      updateItem.mutate({ itemId, data: { outcome } });
    },
    [updateItem],
  );

  const handleNotesChange = useCallback(
    (itemId: string, notes: string) => {
      updateItem.mutate({ itemId, data: { outcome_notes: notes } });
    },
    [updateItem],
  );

  const handleMinutesChange = useCallback(
    (itemId: string, minutes: number | null) => {
      updateItem.mutate({ itemId, data: { planned_minutes: minutes ?? undefined } });
    },
    [updateItem],
  );

  const handleReorder = useCallback(
    (itemId: string, newPosition: number) => {
      reorderItem.mutate({ itemId, newPosition });
    },
    [reorderItem],
  );

  const handleRemove = useCallback(
    (itemId: string) => {
      removeItem.mutate(itemId);
    },
    [removeItem],
  );

  return (
    <div className={`plan-panel ${isCompleted ? 'plan-panel--completed' : ''}`}>
      <PlanHeader
        plan={plan}
        onCompletePlan={handleCompletePlan}
        onCarryOver={onCarryOver}
        onToggleVsActual={() => setShowVsActual((v) => !v)}
        onDeletePlan={onDeletePlan}
        showVsActual={showVsActual}
        pendingItemTitles={pendingItemTitles}
        isCompleting={updatePlan.isPending}
      />

      <PlanItemList
        items={plan.items}
        planStatus={plan.status}
        onOutcomeChange={handleOutcomeChange}
        onNotesChange={handleNotesChange}
        onMinutesChange={handleMinutesChange}
        onRemove={handleRemove}
        onReorder={handleReorder}
      />

      {/* Add item button — visible only when plan is active (US-7) */}
      {!isCompleted && (
        <div className="plan-panel__add-item">
          <Button
            variant="ghost"
            size="sm"
            icon={<Icon name="plus" size={16} />}
            onClick={onAddItem}
          >
            Add Item
          </Button>
        </div>
      )}

      {/* Plan vs Actual panel — toggled from PlanHeader (US-12) */}
      <PlanVsActualPanel date={date} actor={actor} visible={showVsActual} />
    </div>
  );
}
