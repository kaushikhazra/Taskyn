# Design Dry-Run #2 — Planner UI

**Date**: 2026-04-12
**Reviewer**: Velasari
**Documents reviewed**: requirement.md, design-backend.md (patched), design-frontend.md (patched), design-data.md (patched), dryrun-design-1.md
**Purpose**: Re-review after design patches addressing dryrun-1 findings F-01 through F-08 and missing paths M-01 through M-05.

---

## 1. Resolution Check

### F-01: No REST endpoint for "get plan by date + actor" — RESOLVED

**Original**: The primary day-view fetch had no working REST path. `plansApi.getByDate` targeted the list endpoint with wrong params.

**Patch applied**:
- Backend: New `GET /plans/by-date` endpoint (design-backend.md endpoint #3) using `pm_get_plan(plan_date=date, actor=actor)`. Returns `Plan | null` — 200 with dict body or 200 with null body (not 404).
- Frontend API: `plansApi.getByDate(date, actor)` now calls `/plans/by-date?date=${date}&actor=${actor}` (design-data.md section 2).
- Route ordering: `/plans/by-date` registered before `{plan_id}` in the static-routes-first block (design-backend.md route ordering section).
- R-04 also addressed: contract explicitly defined as 200 with null body for missing plans.

**Verification**: Endpoint, API client, query hook (`usePlan` uses `plansApi.getByDate`), and query key (`queryKeys.plans.byDate`) all align. The data flow is complete.

---

### F-02: MonthlyPlan type missing per-day data — RESOLVED

**Original**: `MonthlyPlan` only had aggregate totals. No per-day array for the calendar grid.

**Patch applied**:
- `MonthlyPlan` now includes `days: MonthlyDaySummary[]` (design-data.md, line 168, annotated `// F-02`).
- `MonthlyDaySummary` defined with: `date`, `plan_id`, `status`, `item_count`, `outcomes`, `planned_minutes`, `actual_minutes`.
- Comment clarifies: "one entry per day that has a plan" — days without plans are absent from the array.

**Verification**: `MonthCalendarGrid` renders all calendar cells and populates only those matching a `MonthlyDaySummary` entry. The "No plan" cell state handles absent days. Type shape supports all MonthDayCell visual states.

---

### F-03: Plan-vs-actual query param name mismatch — RESOLVED

**Original**: Backend expected `plan_date`, frontend sent `date`.

**Patch applied**:
- `plansApi.vsActual` now sends `plan_date=${date}` (design-data.md, line 331).
- Matches backend endpoint #14 query param `plan_date: date` (design-backend.md, line 278).

**Verification**: Parameter names align between frontend API client and backend route definition.

---

### F-04: NodePickerModal depends on non-existent `plannable` filter — RESOLVED

**Original**: Design used `useNodes({ plannable: true })` but no such filter exists in the nodes API.

**Patch applied**:
- Client-side filtering approach adopted (design-backend.md section "Plannable Node Filtering (F-04)").
- NodePickerModal fetches `useNodes({ status: [...] })` and `useMethodology(projectId)`, then excludes node types where `can_be_planned === false` (design-frontend.md section 10).
- No upstream changes required to the nodes subsystem — eliminates the R-01 risk from dryrun-1.

**Verification**: Approach is sound. `NodeTypeDefinition.can_be_planned` exists in the codebase. The trade-off (client-side filtering is less efficient but avoids cross-cutting changes) is explicitly documented. The modal has a project filter dropdown, so methodology can be fetched per selected project.

---

### F-05: Position indexing mismatch — 0-based vs 1-based — PARTIALLY RESOLVED

**Original**: Frontend sent 0-based positions; backend enforces 1-based (`ge=1`).

**Patches applied**:
1. Backend: New "Position Indexing Convention (F-05)" section documents 1-based convention. All three schemas (`PlanItemInline.display_order`, `PlanItemAdd.position`, `PlanItemReorder.new_position`) have `ge=1` validators.
2. Frontend DnD: `onDrop` sends `newPosition: targetIndex + 1` (design-frontend.md, line 364, annotated `// +1: backend uses 1-based positions (F-05)`).
3. Optimistic update: `display_order` recomputed as `idx + 1` (design-data.md, line 599, annotated `// 1-based`).

**Still open**: The optimistic splice insertion has an off-by-one. See **N-01** below.

---

### F-06: `display_order` vs `position` field name mismatch — RESOLVED

**Original**: Frontend `PlanItemSeed` used `position` but backend `PlanItemInline` expected `display_order`.

**Patch applied**:
- `PlanItemSeed.display_order` in design-data.md (line 77) now matches backend `PlanItemInline.display_order`. Comment: `// matches backend PlanItemInline field name`.

**Verification**: Field names are aligned. `model_dump(exclude_none=True)` on the backend will correctly receive the `display_order` field.

---

### F-07: Frontend design references wrong query key name — STILL OPEN

**Original**: design-frontend.md section 9 used `planKeys.detail(date, actor)` but the data layer defines `queryKeys.plans.detail(planId)` (by ID) and `queryKeys.plans.byDate(date, actor)` (by date+actor).

**Current state**: design-frontend.md lines 386-401 still reference `planKeys.detail(date, actor)` in the illustrative optimistic reorder example. The authoritative mutation code in design-data.md section 5d correctly uses `queryKeys.plans.byDate(date, actor)`.

**Impact**: Cosmetic — implementors should follow design-data.md for hook code, where the correct key is used. No functional risk since the data layer is the source of truth for hook implementation.

**Recommendation**: Fix during implementation — the design-frontend.md section 9 example is illustrative pseudocode that overlaps with the authoritative code in design-data.md.

---

### F-08: WeeklyPlan.days type uncertain — RESOLVED

**Original**: `WeeklyPlan.days` was typed as `Plan[][]` (arrays of full Plan objects), mismatched with WeekDayCard's expected summary shape.

**Patch applied**:
- `WeeklyPlan.days` is now `WeeklyDaySummary[]` (design-data.md, line 131, annotated `// F-08`).
- `WeeklyDaySummary` defined with: `date`, `plan_id | null`, `status | null`, `item_count`, `outcomes`, `planned_minutes`, `actual_minutes`.
- 7 entries (Mon-Sun) — nullable `plan_id` and `status` for days without plans.

**Verification**: Shape matches `WeekDayCard` prop needs (count, status, outcomes, minutes). Nullability design differs intentionally from `MonthlyDaySummary` (weekly has all 7 entries including empty days; monthly only includes days with plans). Both approaches work for their respective rendering patterns.

---

### M-01: No live update mechanism when V modifies plans — PARTIALLY ADDRESSED

**Original**: `usePlan` had `refetchInterval: false` with no polling. Stale data if V creates plans via MCP.

**Patch applied**: `usePlan` now accepts a configurable `refetchInterval` option (design-data.md, line 399). The mechanism exists.

**Still open**: Neither the frontend design nor the data layer prescribes a specific interval for the day view. No "Refresh" button is designed either.

**Impact**: Low — implementor can set a sensible default (e.g., 30s) when calling `usePlan` in `DayView`. Not a design gap, just an unspecified default.

---

### M-02: Empty state for fully empty week/month — STILL OPEN

**Original**: No empty state designed for a completely empty week or month (all summary values zero).

**Current state**: WeekView and MonthView both render their grid/calendar with zero-value summary bars. Functional but not welcoming for new users.

**Impact**: Low — the views work correctly with zeros. A friendly empty state ("No plans this week — start planning!") would be better UX but is a polish item.

---

### M-03: Carry-over of deleted-node items — RESOLVED

**Patch applied**: CarryOverModal (design-frontend.md section 11) now shows deleted-node items with a warning icon and "(deleted)" label. They are unchecked by default (unlike pending/partial items which are pre-checked). Explicitly documented with `// M-03` annotation.

---

### M-04: Confirmation before plan deletion — RESOLVED

**Patch applied**: design-frontend.md section 12b adds conditional confirmation dialogs:
- Plans with recorded outcomes: detailed warning about permanent data loss.
- Plans with only pending items: simple "Delete plan for {date}?" confirmation.

---

### M-05: Error state when plan already exists (409 on create) — RESOLVED

**Patch applied**: design-frontend.md section 12b specifies `useCreatePlan` onError handling:
- On 409: invalidate `queryKeys.plans.byDate(date, actor)` so the existing plan loads automatically. Info toast.
- On other errors: error toast.

---

## 2. New Findings

### N-01: Optimistic reorder splice uses 1-based position as 0-based splice index [SHOULD FIX]

**Severity**: Off-by-one visual glitch during drag-and-drop (self-corrects on `onSettled` refetch)
**Location**: design-data.md lines 594-596, design-frontend.md lines 391-392

The F-05 fix correctly changed the mutation call to send `newPosition: targetIndex + 1` (1-based). But the optimistic update's `onMutate` receives this 1-based `newPosition` and uses it directly as a splice index:

```ts
// design-data.md line 594-595
// Insert at new position (0-based)        <-- comment says 0-based
const insertAt = Math.min(newPosition, items.length);  // <-- but newPosition is 1-based
items.splice(insertAt, 0, dragged);
```

**Example**: Drag item C to first position (targetIndex = 0):
- `newPosition` = 0 + 1 = **1** (1-based, correct for API)
- Array after removing C: `[A, B, D, E]`
- `items.splice(1, 0, C)` inserts at index 1: `[A, C, B, D, E]` — **wrong**, should be `[C, A, B, D, E]`

The `onSettled` invalidation refetches the correct order from the server within ~1 second, but the user sees the item jump to the wrong position momentarily.

**Fix**: Convert to 0-based for the splice:
```ts
const insertAt = Math.min(newPosition - 1, items.length);
```

The same issue exists in design-frontend.md section 9's illustrative example (line 392: `items.splice(newPosition, 0, moved)`) — also needs `newPosition - 1`.

---

### N-02: NodePickerModal multi-project methodology loading not specified [MINOR]

**Severity**: Implementation ambiguity, not a blocker
**Location**: design-frontend.md section 10, design-backend.md "Plannable Node Filtering (F-04)"

The NodePickerModal shows "a searchable list of nodes from the executor's projects" with a project filter dropdown. The F-04 fix says "fetch methodology info per project and exclude node types where `can_be_planned === false`."

**Ambiguity**: When no project filter is selected (showing all projects), the modal needs methodology info for *every* project to determine plannable types. The design shows `useMethodology(projectId)` — singular. It doesn't specify:
1. Whether to fetch all project methodologies upfront, or
2. Only fetch when a project is selected in the dropdown, or
3. Use a multi-project methodology lookup.

**Suggested approach**: Fetch methodology per project lazily — when the project filter changes, fetch that project's methodology. When showing "all projects," fetch methodologies for all projects the user has access to (typically a small number in a personal PM tool). Cache them via React Query.

**Impact**: Low — implementor can make this decision. The number of projects in Taskyn is small enough that fetching all methodologies is fine.

---

## 3. Carried-Forward Warnings (from dryrun-1, still applicable)

| # | Item | Status | Notes |
|---|------|--------|-------|
| R-02 | Broad invalidation (`plans.all()` on every mutation) | Accepted trade-off | Documented in design-data.md section 6. Fine for v1, single-user. |
| R-03 | HTML5 DnD doesn't work on touch devices | Out of scope | Requirements say no dedicated mobile design. Consistent with KanbanPage. |

---

## 4. Summary Table

### Dryrun-1 Findings

| # | Finding | Severity | Status |
|---|---------|----------|--------|
| F-01 | No REST endpoint for date+actor lookup | MUST FIX | **RESOLVED** |
| F-02 | MonthlyPlan missing per-day data | MUST FIX | **RESOLVED** |
| F-03 | vs-actual param name mismatch | MUST FIX | **RESOLVED** |
| F-04 | Plannable filter doesn't exist | MUST FIX | **RESOLVED** (client-side filtering) |
| F-05 | Position indexing 0-based vs 1-based | SHOULD FIX | **PARTIALLY RESOLVED** (see N-01) |
| F-06 | `display_order` vs `position` field name | SHOULD FIX | **RESOLVED** |
| F-07 | Wrong query key name in frontend example | MINOR | **STILL OPEN** (cosmetic, data layer has correct code) |
| F-08 | WeeklyPlan.days type uncertain | SHOULD VERIFY | **RESOLVED** |

### Dryrun-1 Missing Paths

| # | Item | Status |
|---|------|--------|
| M-01 | No live updates from V | **PARTIALLY ADDRESSED** (mechanism exists, no default set) |
| M-02 | Empty state for empty week/month | **STILL OPEN** (low impact, polish item) |
| M-03 | Carry-over of deleted-node items | **RESOLVED** |
| M-04 | Confirmation before plan deletion | **RESOLVED** |
| M-05 | 409 on create should auto-refresh | **RESOLVED** |

### New Findings (dryrun-2)

| # | Finding | Severity |
|---|---------|----------|
| N-01 | Optimistic splice off-by-one (1-based used as 0-based) | SHOULD FIX |
| N-02 | Multi-project methodology loading unspecified | MINOR |

---

## 5. Verdict

### **PASS WITH WARNINGS**

All four MUST FIX items from dryrun-1 (F-01, F-02, F-03, F-04) are fully resolved. The design is implementable.

**Fix before or during implementation:**

| # | Finding | Risk if deferred |
|---|---------|------------------|
| N-01 | Optimistic splice off-by-one | Momentary visual glitch on drag-drop (self-corrects on refetch). One-line fix: `newPosition - 1` in splice. |
| F-07 | Stale query key name in frontend example | Copy-paste error risk during implementation. Data layer has correct code. |

**Acceptable as-is (implement but polish later):**

| # | Item | Notes |
|---|------|-------|
| M-01 | No prescribed refetchInterval default | Implementor sets a sensible default in DayView. |
| M-02 | No empty state for empty week/month | Functional with zeros. Nice-to-have UX polish. |
| N-02 | Multi-project methodology loading | Implementor decides approach. Small project count makes this trivial. |

---

*The design is ready for task planning and implementation. N-01 should be fixed inline during the drag-and-drop implementation — it's a one-line change in the optimistic update.*
