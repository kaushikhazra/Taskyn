# Planner UI — Data Layer Design (US-14, US-15)

Covers: TypeScript types, API client, query keys, query hooks, mutation hooks.  
Pattern source: existing `nodes`, `timer`, `milestones` modules.

---

## 1. TypeScript Types (`src/taskyn/web/frontend/src/types/index.ts`)

```ts
// ============================================================
// Plans — Enums
// ============================================================

export const PLAN_STATUSES = ['active', 'completed'] as const;
export type PlanStatus = typeof PLAN_STATUSES[number];

export const PLAN_OUTCOMES = ['pending', 'completed', 'partial', 'carried_over', 'dropped'] as const;
export type PlanOutcome = typeof PLAN_OUTCOMES[number];

// ============================================================
// Plans — Core Models
// ============================================================

/** A single day's plan for one actor. */
export interface Plan {
  id: string;
  date: string;                          // "YYYY-MM-DD"
  actor: string;
  status: PlanStatus;
  notes: string | null;
  created_at: string;
  updated_at: string;
  items: PlanItemEnriched[];             // always present on get/create responses
}

/** Plan item as stored — no node enrichment. */
export interface PlanItem {
  id: string;
  plan_id: string;
  node_id: string | null;
  planned_minutes: number | null;
  display_order: number;
  outcome: PlanOutcome;
  outcome_notes: string | null;
  carried_to_plan_id: string | null;
  created_at: string;
  updated_at: string;
}

/** Plan item enriched with joined node/project data (returned by get_plan). */
export interface PlanItemEnriched extends PlanItem {
  node_title: string | null;
  node_status: string | null;
  node_type: string | null;
  project_id: string | null;
  project_name: string | null;
  estimated_minutes: number | null;
  actual_time: number | null;
  node_deleted: boolean;
}

// ============================================================
// Plans — Create / Update DTOs
// ============================================================

export interface PlanCreate {
  date: string;                          // "YYYY-MM-DD"
  actor: string;
  notes?: string;
  items?: PlanItemSeed[];
}

export interface PlanItemSeed {
  node_id: string;
  planned_minutes?: number;
  display_order?: number;           // matches backend PlanItemInline field name
}

export interface PlanUpdate {
  notes?: string;
  status?: PlanStatus;
}

export interface PlanItemAdd {
  node_id: string;
  planned_minutes?: number;
  position?: number;
}

export interface PlanItemUpdate {
  outcome?: PlanOutcome;
  outcome_notes?: string;
  planned_minutes?: number;
}

export interface PlanItemReorder {
  new_position: number;
}

// ============================================================
// Plans — Carry-Over
// ============================================================

export interface CarryOverRequest {
  target_date: string;                   // "YYYY-MM-DD"
  item_ids?: string[];                   // null = carry all eligible
}

export interface CarryOverResult {
  source_plan_id: string;
  target_plan: Plan;
  carried_count: number;
  skipped: CarryOverSkip[];
}

export interface CarryOverSkip {
  item_id: string;
  node_id: string | null;
  reason: string;
}

// ============================================================
// Plans — Weekly View
// ============================================================

export interface WeeklyPlan {
  week_start: string;                    // "YYYY-MM-DD" (Monday)
  week_end: string;                      // "YYYY-MM-DD" (Sunday)
  days: WeeklyDaySummary[];              // F-08: 7 entries (Mon–Sun), per-day summary
  summary: WeeklyPlanSummary;
}

/** Per-day summary for WeekGrid — lightweight, no full Plan/item payloads. */
export interface WeeklyDaySummary {
  date: string;                          // "YYYY-MM-DD"
  plan_id: string | null;               // null if no plan for this day
  status: PlanStatus | null;
  item_count: number;
  outcomes: Record<PlanOutcome, number>;
  planned_minutes: number;
  actual_minutes: number;
}

export interface WeeklyPlanSummary {
  total_planned_items: number;
  total_planned_minutes: number;
  outcomes: Record<PlanOutcome, number>;
  actual_minutes: number;
}

// ============================================================
// Plans — Monthly View
// ============================================================

export interface MonthlyPlan {
  year: number;
  month: number;
  days_in_month: number;
  days_with_plans: number;
  total_planned_items: number;
  total_planned_minutes: number;
  outcomes: Record<PlanOutcome, number>;
  actual_minutes: number;
  days: MonthlyDaySummary[];            // F-02: per-day breakdown for calendar grid
  per_actor: MonthlyActorSummary[];
  milestones: MonthlyMilestone[];
}

/** Per-day summary for MonthCalendarGrid — one entry per day that has a plan. */
export interface MonthlyDaySummary {
  date: string;                          // "YYYY-MM-DD"
  plan_id: string;
  status: PlanStatus;
  item_count: number;
  outcomes: Record<PlanOutcome, number>;
  planned_minutes: number;
  actual_minutes: number;
}

export interface MonthlyActorSummary {
  actor: string;
  days_with_plans: number;
  total_planned_items: number;
  total_planned_minutes: number;
  outcomes: Record<PlanOutcome, number>;
  actual_minutes: number;
}

export interface MonthlyMilestone {
  id: string;
  name: string;
  project_id: string;
  project_name: string;
  target_date: string | null;
  status: string;
}

// ============================================================
// Plans — Plan vs Actual
// ============================================================

export interface PlanVsActual {
  date: string;
  actor: string;
  planned_items: PlanVsActualItem[];
  unplanned_items: UnplannedItem[];
  summary: PlanVsActualSummary;
}

export interface PlanVsActualItem {
  node_id: string | null;
  title: string | null;
  planned_minutes: number | null;
  display_order: number;
  actual_minutes: number;
  current_status: string | null;
  is_terminal: boolean;
  delta_minutes: number | null;
  outcome: PlanOutcome;
  outcome_notes: string | null;
}

export interface UnplannedItem {
  node_id: string;
  title: string;
  actual_minutes: number;
  current_status: string;
  project_id: string;
  project_name: string;
}

export interface PlanVsActualSummary {
  total_planned_minutes: number;
  total_actual_minutes: number;
  total_unplanned_minutes: number;
  planned_item_count: number;
  completed_count: number;
  unplanned_item_count: number;
  overall_delta: number | null;
}

// ============================================================
// Plans — Filter types (for list/query params)
// ============================================================

export interface PlanListFilters {
  actor?: string;
  date_from?: string;
  date_to?: string;
  status?: PlanStatus;
  limit?: number;
  offset?: number;
}
```

---

## 2. API Client (`src/taskyn/web/frontend/src/api/plans.ts`)

```ts
import { api } from './client';
import type {
  Plan, PlanCreate, PlanUpdate, PlanListFilters,
  PlanItemEnriched, PlanItemAdd, PlanItemUpdate, PlanItemReorder,
  CarryOverRequest, CarryOverResult,
  WeeklyPlan, MonthlyPlan, PlanVsActual,
} from '@/types';

export const plansApi = {
  // ── Plan CRUD ──────────────────────────────────────────────

  create: (data: PlanCreate) =>
    api.post<Plan>('/plans', data),

  list: (filters?: PlanListFilters) => {
    const params = new URLSearchParams();
    if (filters?.actor)     params.set('actor', filters.actor);
    if (filters?.date_from) params.set('date_from', filters.date_from);
    if (filters?.date_to)   params.set('date_to', filters.date_to);
    if (filters?.status)    params.set('status', filters.status);
    if (filters?.limit)     params.set('limit', String(filters.limit));
    if (filters?.offset)    params.set('offset', String(filters.offset));
    return api.get<Plan[]>(`/plans?${params}`);
  },

  get: (planId: string) =>
    api.get<Plan>(`/plans/${planId}`),

  /** Fetch plan by date + actor — dedicated endpoint, returns Plan or null. */
  getByDate: (date: string, actor: string) =>
    api.get<Plan | null>(`/plans/by-date?date=${date}&actor=${actor}`),

  update: (planId: string, data: PlanUpdate) =>
    api.patch<Plan>(`/plans/${planId}`, data),

  delete: (planId: string) =>
    api.delete(`/plans/${planId}`),

  // ── Plan Items ─────────────────────────────────────────────

  addItem: (planId: string, data: PlanItemAdd) =>
    api.post<PlanItemEnriched>(`/plans/${planId}/items`, data),

  updateItem: (itemId: string, data: PlanItemUpdate) =>
    api.patch<PlanItemEnriched>(`/plans/items/${itemId}`, data),

  removeItem: (itemId: string) =>
    api.delete(`/plans/items/${itemId}`),

  reorderItem: (itemId: string, data: PlanItemReorder) =>
    api.post<Plan>(`/plans/items/${itemId}/reorder`, data),

  // ── Aggregated Views ───────────────────────────────────────

  weekly: (weekStart: string, actor?: string) => {
    const params = new URLSearchParams({ week_start_date: weekStart });
    if (actor) params.set('actor', actor);
    return api.get<WeeklyPlan>(`/plans/weekly?${params}`);
  },

  monthly: (year: number, month: number, actor?: string) => {
    const params = new URLSearchParams({
      year: String(year),
      month: String(month),
    });
    if (actor) params.set('actor', actor);
    return api.get<MonthlyPlan>(`/plans/monthly?${params}`);
  },

  vsActual: (date: string, actor: string) =>
    api.get<PlanVsActual>(`/plans/vs-actual?plan_date=${date}&actor=${actor}`),

  // ── Carry-Over ─────────────────────────────────────────────

  carryOver: (planId: string, data: CarryOverRequest) =>
    api.post<CarryOverResult>(`/plans/${planId}/carry-over`, data),
};
```

---

## 3. Query Keys (`src/taskyn/web/frontend/src/api/queryKeys.ts`)

Add to the existing `queryKeys` object:

```ts
plans: {
  all: () => ['plans'] as const,

  list: (filters?: PlanListFilters) =>
    [...queryKeys.plans.all(), 'list', filters] as const,

  /** Primary daily lookup — keyed by date + actor. */
  byDate: (date: string, actor: string) =>
    [...queryKeys.plans.all(), 'byDate', date, actor] as const,

  detail: (planId: string) =>
    [...queryKeys.plans.all(), 'detail', planId] as const,

  weekly: (weekStart: string, actor?: string) =>
    [...queryKeys.plans.all(), 'weekly', weekStart, actor] as const,

  monthly: (year: number, month: number, actor?: string) =>
    [...queryKeys.plans.all(), 'monthly', year, month, actor] as const,

  vsActual: (date: string, actor: string) =>
    [...queryKeys.plans.all(), 'vsActual', date, actor] as const,
},
```

**Key design notes:**
- `plans.all()` is the root — invalidating it clears every plan query.
- `byDate` is the most-used key (day view primary fetch).
- `detail` exists for when we navigate to a plan by ID (e.g., carry-over target).
- Aggregate views (`weekly`, `monthly`, `vsActual`) are separate cache entries.

---

## 4. Query Hooks (`src/taskyn/web/frontend/src/hooks/queries/usePlans.ts`)

```ts
import { useQuery } from '@tanstack/react-query';
import { plansApi } from '@/api/plans';
import { queryKeys } from '@/api/queryKeys';
import type { PlanListFilters } from '@/types';

interface QueryOptions {
  refetchInterval?: number | false;
}

/** Fetch a single day's plan by date + actor (primary day-view hook). */
export function usePlan(date: string, actor: string, options?: QueryOptions) {
  return useQuery({
    queryKey: queryKeys.plans.byDate(date, actor),
    queryFn: () => plansApi.getByDate(date, actor),
    enabled: !!date && !!actor,
    refetchInterval: options?.refetchInterval ?? false,   // plans are user-driven, no polling
  });
}

/** Fetch a plan by ID (used after carry-over to show target plan). */
export function usePlanById(planId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.plans.detail(planId!),
    queryFn: () => plansApi.get(planId!),
    enabled: !!planId,
  });
}

/** List plans with optional filters (plan history / date range). */
export function usePlans(filters?: PlanListFilters) {
  return useQuery({
    queryKey: queryKeys.plans.list(filters),
    queryFn: () => plansApi.list(filters),
  });
}

/** Weekly aggregate view — 7-day overview for one actor. */
export function useWeeklyPlan(weekStart: string, actor?: string, options?: QueryOptions) {
  return useQuery({
    queryKey: queryKeys.plans.weekly(weekStart, actor),
    queryFn: () => plansApi.weekly(weekStart, actor),
    enabled: !!weekStart,
    refetchInterval: options?.refetchInterval ?? false,
  });
}

/** Monthly aggregate view — calendar overview for one actor. */
export function useMonthlyPlan(year: number, month: number, actor?: string, options?: QueryOptions) {
  return useQuery({
    queryKey: queryKeys.plans.monthly(year, month, actor),
    queryFn: () => plansApi.monthly(year, month, actor),
    enabled: !!year && !!month,
    refetchInterval: options?.refetchInterval ?? false,
  });
}

/** Plan vs actual comparison for one day. */
export function usePlanVsActual(date: string, actor: string) {
  return useQuery({
    queryKey: queryKeys.plans.vsActual(date, actor),
    queryFn: () => plansApi.vsActual(date, actor),
    enabled: !!date && !!actor,
  });
}
```

---

## 5. Mutation Hooks (`src/taskyn/web/frontend/src/hooks/mutations/usePlanMutations.ts`)

### 5a. Invalidation helpers

```ts
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { plansApi } from '@/api/plans';
import { queryKeys } from '@/api/queryKeys';
import { useToast } from '@/hooks/useToast';
import type {
  Plan, PlanCreate, PlanUpdate,
  PlanItemAdd, PlanItemUpdate, PlanItemReorder, PlanItemEnriched,
  CarryOverRequest, CarryOverResult,
} from '@/types';

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
```

### 5b. Plan CRUD mutations

```ts
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
```

### 5c. Plan item mutations (standard)

```ts
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
```

### 5d. Optimistic: reorder item (drag-and-drop — US-5)

```ts
/**
 * Optimistic reorder — moves the item visually on drag, reverts on error.
 *
 * The cache key is `byDate(date, actor)` because the day-view plan is the
 * active query when the user drags items.
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
        const [dragged] = items.splice(dragIndex, 1);

        // Insert at new position (0-based)
        const insertAt = Math.min(newPosition, items.length);
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
```

### 5e. Optimistic: update item outcome (US-3)

```ts
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
```

### 5f. Carry-over mutation (US-11)

```ts
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
```

---

## 6. Invalidation Matrix

Which mutations invalidate which keys:

| Mutation | Invalidates |
|----------|-------------|
| `useCreatePlan` | `plans.all()` + `dashboard.all()` |
| `useUpdatePlan` | `plans.all()` |
| `useDeletePlan` | `plans.all()` + `dashboard.all()` |
| `useAddPlanItem` | `plans.all()` |
| `useRemovePlanItem` | `plans.all()` |
| `useReorderPlanItem` | `plans.all()` (via `onSettled`, after optimistic) |
| `useUpdatePlanItem` | `plans.all()` (via `onSettled`, after optimistic) |
| `useCarryOverPlan` | `plans.all()` + `dashboard.all()` |

**Why `plans.all()` everywhere**: Changing a plan item's outcome on Monday affects the weekly view, monthly aggregates, and vsActual for that date. Since plan data is user-driven (not polled), broad invalidation on mutation is safe and correct — no thundering herd risk.

---

## 7. Optimistic Update Strategy

Only two mutations use optimistic updates:

| Hook | What's optimistic | Cache key | Rollback |
|------|-------------------|-----------|----------|
| `useReorderPlanItem` | Reorder items array in-place, recompute `display_order` | `plans.byDate(date, actor)` | Restore previous `Plan` snapshot |
| `useUpdatePlanItem` | Spread `PlanItemUpdate` fields onto matching item | `plans.byDate(date, actor)` | Restore previous `Plan` snapshot |

**Why only these two**: Reorder and outcome are high-frequency, latency-sensitive interactions (drag-and-drop, checkbox clicks). All other mutations (create plan, add item, remove item, carry-over) are infrequent enough that waiting for server confirmation is fine and avoids complex rollback logic.

**Pattern**: Both follow the established `useOptimisticUpdateNode` pattern:
1. `onMutate`: cancel in-flight queries, snapshot previous, apply optimistic change
2. `onError`: restore snapshot from context
3. `onSettled`: invalidate `plans.all()` to refetch authoritative state

---

## 8. Hook Exports

### `src/taskyn/web/frontend/src/hooks/queries/index.ts`

```ts
export * from './usePlans';
```

### `src/taskyn/web/frontend/src/hooks/mutations/index.ts`

```ts
export * from './usePlanMutations';
```
