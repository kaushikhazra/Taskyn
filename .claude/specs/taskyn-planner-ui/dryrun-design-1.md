# Design Dry-Run #1 — Planner UI

**Date**: 2026-04-12
**Reviewer**: Velasari
**Documents reviewed**: requirement.md, design-backend.md, design-frontend.md, design-data.md
**Codebase verification**: Existing routes, API clients, hooks, types, planning core, enums, MCP tools — all cross-referenced.

---

## 1. Coverage Check

Every user story (US-1 through US-15) checked against all three design documents.

| US | Title | Backend | Frontend | Data | Verdict |
|----|-------|---------|----------|------|---------|
| US-1 | View today's plan | `GET /plans/{plan_id}` (date+actor query) | DayView + PlanItemList | `usePlan(date, actor)` + `plansApi.getByDate` | **GAP** — see F-01 |
| US-2 | Navigate between dates | N/A (client-side) | DateNavigator + `usePlannerParams` + URL params | N/A | Covered |
| US-3 | Mark outcomes | `PATCH /plans/items/{item_id}` | OutcomeControl molecule | `useUpdatePlanItem` (optimistic) | Covered |
| US-4 | Outcome notes | PlanItemUpdate.outcome_notes | OutcomeNotes molecule | `useUpdatePlanItem` | Covered |
| US-5 | Reorder items | `POST /plans/items/{item_id}/reorder` | DnD section 9 | `useReorderPlanItem` (optimistic) | **WARNING** — see F-05 |
| US-6 | Create plan | `POST /plans` | EmptyPlanState + button | `useCreatePlan` | Covered |
| US-7 | Add items | `POST /plans/{plan_id}/items` | NodePickerModal | `useAddPlanItem` | **GAP** — see F-04 |
| US-8 | Remove items | `DELETE /plans/items/{item_id}` | Remove button + confirmation | `useRemovePlanItem` | Covered |
| US-9 | Weekly view | `GET /plans/weekly` | WeekView + WeekGrid | `useWeeklyPlan` | **WARNING** — see F-08 |
| US-10 | Monthly view | `GET /plans/monthly` | MonthView + MonthCalendarGrid | `useMonthlyPlan` | **GAP** — see F-02 |
| US-11 | Carry over | `POST /plans/{plan_id}/carry-over` | CarryOverModal | `useCarryOverPlan` | Covered |
| US-12 | Plan vs actual | `GET /plans/vs-actual` | PlanVsActualPanel | `usePlanVsActual` | **GAP** — see F-03 |
| US-13 | Complete plan | `PATCH /plans/{plan_id}` | Completion gate (section 15) | `useUpdatePlan` | Covered |
| US-14 | REST API layer | 13 endpoints defined | N/A | N/A | **GAP** — see F-01 |
| US-15 | Data layer | N/A | N/A | Types + API client + hooks | Covered |

---

## 2. Findings

### F-01: No REST endpoint for "get plan by date + actor" [MUST FIX]

**Severity**: Blocks US-1, US-3, US-5, US-12 (anything using day view)
**Location**: design-backend.md endpoint #3 vs. design-data.md section 2

The **primary day-view fetch** has no working REST path.

The frontend `plansApi.getByDate(date, actor)` calls:
```ts
api.get<Plan | null>(`/plans?date=${date}&actor=${actor}&resolve=true`)
```

This targets `GET /plans` (the list endpoint), but with three problems:
1. The list endpoint takes `date_from` / `date_to`, not a bare `date` param — FastAPI will silently ignore it.
2. There is no `resolve=true` parameter designed anywhere in the backend.
3. The list endpoint returns `Plan[]`, not `Plan | null`.

Meanwhile, `GET /plans/{plan_id}` does support alternative lookup via `plan_date` + `actor` query params, but it **requires a `plan_id` path segment** — you can't call it without one.

The underlying MCP tool (`pm_get_plan`) supports lookup by date+actor with no plan_id, so the capability exists but isn't exposed through REST.

**Fix**: Add a dedicated endpoint **before** the `{plan_id}` routes:
```
GET /plans/by-date?date=2026-04-12&actor=KH  →  pm_get_plan(plan_date=date, actor=actor)
```
Returns `Plan | null` (200 with body or 200 with null / 404). Register it in the static-routes-first block alongside `weekly`, `monthly`, `vs-actual`. Update `plansApi.getByDate` to call `/plans/by-date?date=...&actor=...`.

---

### F-02: MonthlyPlan type missing per-day data [MUST FIX]

**Severity**: Blocks US-10 (entire month view)
**Location**: design-data.md section 1 (`MonthlyPlan` interface) vs. design-frontend.md section 6

The frontend MonthCalendarGrid renders 28-31 `MonthDayCell` components, each needing:
- Whether a plan exists for that day
- Plan status (active/completed)
- Outcome distribution (for the mini OutcomeBar)
- Item count

But `MonthlyPlan` only contains aggregate totals:
```ts
export interface MonthlyPlan {
  year: number;
  month: number;
  days_in_month: number;
  days_with_plans: number;       // scalar count — not which days
  total_planned_items: number;   // aggregate — not per-day
  outcomes: Record<...>;         // aggregate — not per-day
  // ... no per-day array
}
```

There is no `days` field with per-day breakdown. The calendar grid **cannot be built** from this type.

**Fix**: Add a per-day array to `MonthlyPlan`:
```ts
export interface MonthlyPlan {
  // ... existing aggregate fields ...
  days: MonthlyDaySummary[];     // one entry per day that has a plan
}

export interface MonthlyDaySummary {
  date: string;
  plan_id: string;
  status: PlanStatus;
  item_count: number;
  outcomes: Record<PlanOutcome, number>;
  planned_minutes: number;
  actual_minutes: number;
}
```
Verify the backend `planning.get_monthly_plan()` actually returns per-day data (it likely does — the MCP tool exists). Shape the TS type to match the actual backend response.

---

### F-03: Plan-vs-actual query param name mismatch [MUST FIX]

**Severity**: Breaks US-12 at HTTP level
**Location**: design-backend.md endpoint #13 vs. design-data.md section 2

Backend expects `plan_date`:
```python
async def get_plan_vs_actual(plan_date: date, actor: str, ...):
```

Frontend sends `date`:
```ts
vsActual: (date: string, actor: string) =>
    api.get<PlanVsActual>(`/plans/vs-actual?date=${date}&actor=${actor}`),
```

FastAPI will reject the request: `plan_date` is a required query param that's missing. The `date` param will be ignored (or cause a 422).

**Fix**: Either rename the backend param to `date`, or update the frontend to send `plan_date`. Backend uses `plan_date` to be explicit and avoid collision with Python's `date` type — recommend updating the frontend:
```ts
api.get<PlanVsActual>(`/plans/vs-actual?plan_date=${date}&actor=${actor}`)
```

---

### F-04: NodePickerModal depends on non-existent `plannable` filter [MUST FIX]

**Severity**: Blocks US-7 AC-3 (filter to plannable node types)
**Location**: design-frontend.md section 10

The design specifies:
```
useNodes({ status: ['backlog','ready','in_progress'], plannable: true })
```

Verified against codebase:
- `NodeTypeDefinition` in `src/taskyn/methodologies/base.py` **does** have `can_be_planned: bool = False`
- In ClassicAgile, only `task` has `can_be_planned=True`
- **Neither** the nodes REST endpoint (`GET /api/v1/nodes`) **nor** the MCP tool (`pm_list_nodes`) supports a `plannable` filter

This requires upstream changes to the nodes subsystem:
1. Add `plannable: bool | None` query param to `GET /api/v1/nodes` route
2. Add `plannable` param to `pm_list_nodes` MCP tool
3. Add filtering logic in `core/reporting.py` (or wherever `list_nodes` lives) that cross-references methodology's `can_be_planned` flag

**Fix**: Document this as a prerequisite change in the task plan. Alternatively, the NodePickerModal can filter client-side: fetch all nodes, then exclude types where `can_be_planned === false` by calling `GET /api/v1/projects/{id}/methodology` for each project. Client-side filtering is simpler but less efficient.

---

### F-05: Position indexing mismatch — 0-based vs 1-based [SHOULD FIX]

**Severity**: Will cause off-by-one bugs in drag-and-drop (US-5)
**Location**: design-backend.md schemas vs. design-data.md section 5d vs. design-frontend.md section 9

Backend schemas enforce 1-based positions:
```python
class PlanItemReorder(BaseModel):
    new_position: int = Field(ge=1)        # minimum 1

class PlanItemAdd(BaseModel):
    position: int | None = Field(default=None, ge=1)  # minimum 1
```

But the frontend DnD code uses 0-based array indices:
```ts
// design-frontend.md section 9
onDrop(e, targetIndex)    // targetIndex comes from array index — 0-based

// design-data.md section 5d
const reordered = items.map((item, idx) => ({
  ...item,
  display_order: idx,     // 0-based: 0, 1, 2, ...
}));
```

Sending `newPosition: 0` to the backend will cause a Pydantic validation error (ge=1). And even `newPosition: targetIndex` without +1 adjustment puts items one position earlier than intended.

**Fix**: Decide on a convention and enforce it in both docs:
- If the backend is 1-based (which it is per the schema), the frontend must send `targetIndex + 1`
- The optimistic update should set `display_order: idx + 1` to match
- Or change the backend to 0-based (`ge=0`) — but this changes the existing API contract

---

### F-06: `PlanItemInline.display_order` vs `PlanItemSeed.position` field name mismatch [SHOULD FIX]

**Severity**: Inline items at plan creation may silently lose ordering
**Location**: design-backend.md `PlanItemInline` vs. design-data.md `PlanItemSeed`

Backend schema for inline items at creation:
```python
class PlanItemInline(BaseModel):
    node_id: str
    planned_minutes: int | None = None
    display_order: int | None = None        # ← "display_order"
```

Frontend DTO for the same purpose:
```ts
export interface PlanItemSeed {
    node_id: string;
    planned_minutes?: number;
    position?: number;                       // ← "position"
}
```

The frontend will send `{ position: 2 }` but the backend Pydantic model expects `display_order`. With `exclude_none=True`, the backend just won't see the ordering hint, and items get default ordering.

**Fix**: Align field names. The MCP tool `pm_create_plan` passes items through as dicts — check what field name the core function expects and use that in both schemas.

---

### F-07: Frontend design references wrong query key name [MINOR]

**Severity**: Copy-paste confusion during implementation
**Location**: design-frontend.md section 9 vs. design-data.md section 3

Frontend design section 9 (DnD optimistic update example) uses:
```ts
planKeys.detail(date, actor)
```

But the data layer design defines:
- `queryKeys.plans.detail(planId: string)` — takes a plan ID
- `queryKeys.plans.byDate(date: string, actor: string)` — takes date + actor

The correct key for the day-view plan is `queryKeys.plans.byDate(date, actor)`, which is what the data layer's actual mutation code uses. The frontend design example just has a stale name.

**Fix**: Update design-frontend.md section 9 to reference `queryKeys.plans.byDate(date, actor)`.

---

### F-08: WeeklyPlan.days type may not match backend response [SHOULD VERIFY]

**Severity**: Potential type mismatch blocking US-9
**Location**: design-data.md section 1 (`WeeklyPlan` interface)

The type defines:
```ts
export interface WeeklyPlan {
  days: Plan[][];    // 7 slots (Mon-Sun), each a list of plans
}
```

But the frontend WeekDayCard expects **summary data** per day (item count, outcome distribution, planned/actual minutes) — not full `Plan` objects with all their `PlanItemEnriched[]` arrays. Two concerns:

1. **Payload size**: Returning 7 full Plan objects (each with all enriched items) is heavy for an overview that only shows counts and bars.
2. **Type mismatch**: WeekDayCard's props suggest a day-summary shape, not `Plan[]`. The `Plan[][]` (array of arrays) is also odd — each actor has at most one plan per day, and the view is already filtered by actor.

**Fix**: Verify what `planning.get_weekly_plan()` actually returns. If it returns per-day summaries (likely), define a `WeeklyDaySummary` type similar to the suggested `MonthlyDaySummary` and use `days: WeeklyDaySummary[]`. If it returns full Plan objects, consider whether a summary endpoint would be better.

---

## 3. Missing Paths

### M-01: No live update mechanism when V modifies plans

The `usePlan` hook has `refetchInterval: false` (no polling). If Velasari creates or modifies today's plan via MCP while the executor has PlannerPage open, the executor sees stale data until they navigate away and back.

**Suggested mitigation**: Add a configurable `refetchInterval` (e.g., 30 seconds) for the day-view plan query only, since that's the active working view. Or add a manual "Refresh" button in the toolbar. Week/month views are fine without polling.

### M-02: Empty state for fully empty week/month

WeekView and MonthView handle "no plan" individual days, but don't design an empty state for a completely empty week (new user, first week) or month. The summary bars would show all zeros, which is functional but not welcoming.

**Suggested fix**: Add an empty state check: if `summary.total_planned_items === 0`, show a friendly prompt similar to DayView's EmptyPlanState.

### M-03: Carry-over of deleted-node items

US-11 AC-2 says pending + partial items are eligible for carry-over. But what if an eligible item has `node_deleted: true`? Carrying it over preserves a broken reference. The CarryOverModal doesn't visually distinguish deleted-node items or warn about them.

**Suggested fix**: In CarryOverModal's item checklist, show deleted-node items with a warning icon and "(deleted)" label, matching US-1 AC-4 style. Let the user uncheck them.

### M-04: Confirmation before plan deletion

The design covers removing items (with confirmation for non-pending outcomes) and completing plans (with pending-items gate). But there's no confirmation dialog for deleting an entire plan. `useDeletePlan` just fires. Accidental plan deletion loses all item history.

**Suggested fix**: Add a confirmation dialog, especially for plans with items that have outcomes recorded.

### M-05: Error state when plan already exists

US-6: If the executor clicks "Create Plan" but a plan already exists (e.g., V created one between page load and click), the backend returns 409 Conflict. The `useCreatePlan` mutation shows an error toast, but the UI stays on EmptyPlanState — the user needs to know to refresh.

**Suggested fix**: On 409 error, invalidate the plan query so the existing plan loads automatically.

---

## 4. Architectural Risks

### R-01: Upstream dependency on nodes plannable filter

F-04 requires changes to the nodes subsystem (`routes/nodes.py`, MCP tool `pm_list_nodes`, and node listing logic). This is outside the Planner UI feature scope and could block US-7 implementation. Assess effort early and decide: upstream change vs. client-side filtering.

### R-02: Broad invalidation strategy

Every mutation invalidates `queryKeys.plans.all()`, which re-fetches the day plan, weekly view, monthly view, and vs-actual — even when only one view is active. For a single user this is fine (no thundering herd). But it means:
- Marking an outcome on Monday re-fetches the entire monthly calendar
- Reordering an item triggers 4+ queries

This is a known trade-off documented in the design. Acceptable for v1 but worth noting: if the plan grows complex, targeted invalidation (`plans.byDate` + `plans.vsActual` for outcome changes) would be more efficient.

### R-03: HTML5 Drag and Drop on touch devices

The DnD approach matches KanbanPage (HTML5 native), which is consistent. But HTML5 DnD doesn't work on mobile touch devices. The requirements say "no dedicated mobile design" which is fine, but "responsive is fine" implies it should work on tablets. Touch-based reorder would need a library (e.g., dnd-kit) or an alternative (up/down arrow buttons).

**Risk level**: Low — out of scope per requirements, but worth noting for future.

### R-04: `getByDate` returning `null` vs `undefined` vs 404

The `plansApi.getByDate` is typed to return `Plan | null`. But if the backend returns 404 (no plan for that date), the api client might throw rather than returning null. The `usePlan` hook doesn't have explicit 404 handling to distinguish "no plan" from "request failed."

**Suggested clarification**: Define the contract — should the backend return 200 with `null` body, or 404? The frontend's empty-state logic (`if no plan: EmptyPlanState`) depends on this. If 404, the hook's `error` state needs to be checked, not just `data === null`.

---

## 5. Verdict

### **FAIL** — Must fix 4 items before implementing

| # | Finding | Why it blocks |
|---|---------|---------------|
| F-01 | No REST endpoint for date+actor plan lookup | Day view cannot fetch data. Every day-view feature (US-1, US-3, US-4, US-5, US-8, US-12, US-13) is broken. |
| F-02 | MonthlyPlan type missing per-day data | Month view calendar grid (US-10) cannot render. |
| F-03 | vs-actual query param name mismatch (`date` vs `plan_date`) | Plan vs actual (US-12) will 422 on every request. |
| F-04 | Plannable filter doesn't exist in nodes API | Node picker (US-7) cannot filter to valid node types. Requires decision: upstream change or client-side workaround. |

### Additionally fix before or during implementation

| # | Finding | Risk if deferred |
|---|---------|-----------------|
| F-05 | Position indexing 0-based vs 1-based | DnD sends invalid position (0), causing 422 errors or off-by-one placement. |
| F-06 | `display_order` vs `position` field name | Inline items at plan creation silently lose ordering. |
| F-08 | WeeklyPlan.days type uncertain | May need type revision once backend response shape is verified. |

### Warnings (implement but watch)

| # | Item | Mitigation |
|---|------|------------|
| F-07 | Query key name in frontend design example | Cosmetic — data layer design has the correct code |
| M-01 | No live updates from V | Add refetchInterval or refresh button |
| M-05 | 409 on create should auto-refresh | Handle in mutation onError |
| R-02 | Broad invalidation | Acceptable for v1, optimize later if needed |
| R-04 | null vs 404 contract for missing plans | Define explicitly in backend design |

---

*Next step: Fix F-01 through F-04 in the design documents, clarify F-05/F-06, then re-run as dryrun-design-2.*
