# Planner UI — Adopt Plan Feature in Web Frontend

## Overview

The Taskyn web UI's PlannerPage currently shows a hierarchical node tree browser with status toggles — essentially a project explorer, not a planner. The planning backend (v0.9.0) shipped 13 MCP tools for managing daily plans, plan items, outcomes, weekly/monthly views, carry-over, and plan-vs-actual analysis. None of this is surfaced in the UI.

This feature redesigns PlannerPage to use the actual plan backend, giving executors a daily-intentions view with day/week/month horizons.

### Key design principles

- **Intentions, not schedules**: Plans are priority-ordered lists of what someone *intends* to work on. No time-blocking, no calendar grid.
- **Outcomes, not deliverables**: A "writing session" is *completed* when the session happened, even if the paper isn't finished. The outcome tracks whether the intention was honored, not whether the larger work item is done.
- **V plans, executors execute**: Velasari (the AI) creates plans via MCP tools. KH and VH are executors who view plans and record outcomes in the UI. The UI should also allow manual plan creation and editing for when the executor wants to self-plan.
- **Three horizons**: Day (primary), week (overview), month (patterns). Day view is the home state.

### Actors

| Actor | Role | Primary actions |
|-------|------|-----------------|
| **Executor** (KH, VH) | Views plans, records outcomes, carries over items | Daily interaction with the planner UI |
| **Velasari** (V) | Creates/manages plans via MCP | Not a UI user — but plans V creates must appear in the UI |

### Backend capabilities (already shipped)

| Capability | Backend function | MCP tool |
|------------|-----------------|----------|
| Create daily plan | `create_plan(date, actor, notes, items)` | `pm_create_plan` |
| Get plan (by id, date, or actor) | `get_plan(plan_id, plan_date, actor)` | `pm_get_plan` |
| Update plan (notes, status) | `update_plan(plan_id, notes, status)` | `pm_update_plan` |
| Delete plan | `delete_plan(plan_id)` | `pm_delete_plan` |
| List plans (with filters) | `list_plans(actor, date_from, date_to, status)` | `pm_list_plans` |
| Add item to plan | `add_plan_item(plan_id, node_id, planned_minutes, position)` | `pm_add_plan_item` |
| Remove item from plan | `remove_plan_item(item_id)` | `pm_remove_plan_item` |
| Reorder item | `reorder_plan_item(item_id, new_position)` | `pm_reorder_plan_item` |
| Update item (outcome, minutes, notes) | `update_plan_item(item_id, ...)` | `pm_update_plan_item` |
| Weekly view | `get_weekly_plan(week_start_date, actor)` | `pm_get_weekly_plan` |
| Monthly view | `get_monthly_plan(year, month, actor)` | `pm_get_monthly_plan` |
| Plan vs actual | `plan_vs_actual(plan_date, actor)` | `pm_plan_vs_actual` |
| Carry over items | `carry_over_plan(source_plan_id, target_date, item_ids)` | `pm_carry_over_plan` |

### What does NOT exist yet

- **No REST API endpoints for plans** — the web backend (`src/taskyn/web/backend/routes/`) has no `plans.py` router. All 13 operations need REST exposure.
- **No frontend API client for plans** — `src/taskyn/web/frontend/src/api/` has no `plans.ts`.
- **No React Query hooks for plans** — no `usePlans.ts` in queries or mutations.
- **No plan-related TypeScript types** — `src/taskyn/web/frontend/src/types/` has no Plan/PlanItem types.

---

## User Stories

### US-1: View today's plan (day view)

**As** an executor,
**I want** to see my daily plan for today when I open the Planner page
**so that** I immediately know what I intend to work on.

**Acceptance criteria:**
1. PlannerPage defaults to today's date and the current actor.
2. If a plan exists for today, display plan items as a priority-ordered list (ordered by `display_order`).
3. Each plan item shows: item title (from linked node), node type badge, project name, outcome status, and planned minutes (if set).
4. Items with `node_deleted: true` show a "(deleted)" indicator instead of a title.
5. If no plan exists for today, show an empty state with a prompt to create one or a message that V hasn't planned yet.
6. Plan-level notes (if any) are visible at the top of the plan.
7. Plan status (active/completed) is visible.

### US-2: Navigate between dates

**As** an executor,
**I want** to navigate to any date to view that day's plan
**so that** I can review past plans or look ahead.

**Acceptance criteria:**
1. A date picker or day-navigation control (prev/next arrows + date display) is available in the day view.
2. Clicking prev/next moves by one day.
3. A "Today" button returns to the current date.
4. Navigating to a date fetches and displays that date's plan (or empty state if none).
5. The URL reflects the selected date so it can be bookmarked/shared (e.g., `/planner?date=2026-04-12`).

### US-3: Mark plan item outcomes

**As** an executor,
**I want** to mark plan items as completed, partial, or dropped
**so that** I record what actually happened with each intention.

**Acceptance criteria:**
1. Each plan item has an outcome control that allows setting: completed, partial, dropped.
2. Pending items have a default/neutral visual state.
3. Setting an outcome visually updates the item immediately (optimistic update).
4. Completed items show a checkmark or success indicator.
5. Partial items show a distinct "half-done" indicator.
6. Dropped items show a muted/struck-through style.
7. Outcome changes persist to the backend via `update_plan_item`.
8. Outcome can be changed after initial selection (e.g., partial -> completed).

### US-4: Add outcome notes

**As** an executor,
**I want** to add a short note when marking an outcome
**so that** I capture context about why something was partial or dropped.

**Acceptance criteria:**
1. When setting an outcome to partial or dropped, an optional notes field appears or is accessible.
2. Notes can also be added to completed items (optional, not prompted).
3. Notes are saved via `update_plan_item(outcome_notes=...)`.
4. Existing notes are visible on items that have them.
5. Notes can be edited after initial entry.

### US-5: Reorder plan items by priority

**As** an executor,
**I want** to reorder plan items via drag-and-drop
**so that** the list reflects my current priorities.

**Acceptance criteria:**
1. Plan items support drag-and-drop reordering.
2. Reordering calls `reorder_plan_item(item_id, new_position)` on drop.
3. The list updates optimistically on drag (before server confirms).
4. If the server rejects the reorder, the list reverts to the previous order.
5. Visual drag handle or indicator is present on each item.

### US-6: Create a new plan

**As** an executor,
**I want** to create a plan for a date that doesn't have one yet
**so that** I can self-plan when Velasari hasn't created a plan.

**Acceptance criteria:**
1. When viewing a date with no plan, a "Create Plan" action is available.
2. Creating a plan requires only the date (auto-filled from current view) and actor (auto-filled from auth context).
3. Optional: add notes at creation time.
4. After creation, the empty plan is displayed and items can be added immediately.
5. Plan creation calls `create_plan(date, actor, notes)`.

### US-7: Add items to a plan

**As** an executor,
**I want** to add work items (nodes) to my daily plan
**so that** I can build my list of intentions.

**Acceptance criteria:**
1. An "Add Item" action is available on active plans.
2. Adding an item opens a node picker — a searchable list of nodes from the executor's projects.
3. The picker filters to plannable node types only (as defined by each project's methodology).
4. Selected node is added to the plan via `add_plan_item(plan_id, node_id)`.
5. Optionally set planned minutes at add time.
6. New items appear at the bottom of the list (or at a specified position).
7. Items cannot be added to a completed plan.

### US-8: Remove items from a plan

**As** an executor,
**I want** to remove an item from my plan
**so that** I can adjust my intentions before or during the day.

**Acceptance criteria:**
1. Each plan item has a remove/delete action (e.g., swipe, icon button, or context menu).
2. Removal calls `remove_plan_item(item_id)`.
3. Removal requires confirmation if the item has a non-pending outcome (to prevent accidental loss of outcome data).
4. The item disappears from the list immediately (optimistic update).
5. Remaining items recompact their display order automatically (backend handles this).

### US-9: Weekly plan view

**As** an executor,
**I want** to see a weekly overview of my plans
**so that** I understand the shape of my week at a glance.

**Acceptance criteria:**
1. A "Week" view tab/toggle is available alongside the "Day" view.
2. Weekly view shows 7 day columns (Mon-Sun) for the selected week.
3. Each day column shows: number of planned items, plan status (active/completed/no plan), and outcome distribution (how many completed/partial/dropped/pending).
4. Clicking a day column navigates to that day's plan in day view.
5. Week navigation (prev/next week + "This Week" button) is available.
6. A summary bar shows: total planned items, total planned minutes, outcome breakdown, and actual minutes worked.
7. Data comes from `get_weekly_plan(week_start_date, actor)`.

### US-10: Monthly plan view

**As** an executor,
**I want** to see a monthly overview of my planning
**so that** I can spot patterns in consistency and completion.

**Acceptance criteria:**
1. A "Month" view tab/toggle is available alongside Day and Week views.
2. Monthly view shows a calendar grid for the selected month.
3. Each day cell shows a visual indicator: has-plan (with outcome summary) vs. no-plan.
4. Days with plans show a small outcome pie/bar (completed vs partial vs pending vs dropped).
5. Clicking a day cell navigates to that day's plan in day view.
6. Month navigation (prev/next month) is available.
7. A summary section shows: days with plans, total planned items, total planned minutes, outcome breakdown, actual minutes, and active milestones for the month.
8. Data comes from `get_monthly_plan(year, month, actor)`.

### US-11: Carry over incomplete items

**As** an executor,
**I want** to carry over unfinished items from a past day to a future date
**so that** incomplete intentions aren't lost and automatically appear in a new plan.

**Acceptance criteria:**
1. On a plan that has pending or partial items, a "Carry Over" action is available.
2. Carry-over shows which items are eligible (pending + partial) and lets the executor select which to carry.
3. The executor picks a target date (defaults to tomorrow or the next working day).
4. Carry-over calls `carry_over_plan(source_plan_id, target_date, item_ids)`.
5. Source items are marked as `carried_over` in the UI with a visual link indicator.
6. If the target plan already exists, items are appended to it.
7. If the target plan doesn't exist, it's created automatically.
8. The response shows how many items were carried and how many were skipped (with reasons).

### US-12: Plan vs actual comparison

**As** an executor,
**I want** to compare my planned intentions against actual work
**so that** I can reflect on how my day went versus what I intended.

**Acceptance criteria:**
1. A "Plan vs Actual" view or overlay is available on any day's plan.
2. For each planned item, show: planned minutes (if set), actual minutes (from time entries), and delta.
3. Show unplanned work: items that received time entries but weren't in the plan, with actual minutes and project name.
4. A summary section shows: total planned minutes, total actual minutes, total unplanned minutes, planned item count, completed count, and overall delta.
5. Data comes from `plan_vs_actual(plan_date, actor)`.
6. Clear visual distinction between planned items and unplanned work.

### US-13: Complete a plan

**As** an executor,
**I want** to mark a day's plan as completed
**so that** I signal that the day is done and no more changes are expected.

**Acceptance criteria:**
1. An active plan shows a "Complete Plan" action.
2. Completing a plan requires all items to have non-pending outcomes. If any are still pending, the UI shows which items need resolution before completing.
3. Completing calls `update_plan(plan_id, status="completed")`.
4. A completed plan is visually distinct (e.g., muted, with a "completed" badge).
5. Completed plans are read-only — no reordering, adding, or removing items. Outcome notes can still be edited.

### US-14: REST API layer for plans

**As** the frontend application,
**I need** REST API endpoints that expose all plan operations
**so that** the React UI can communicate with the plan backend.

**Acceptance criteria:**
1. A new `plans.py` router is created in `src/taskyn/web/backend/routes/` following the existing pattern (FastAPI router with typed request/response models).
2. Endpoints cover all 13 plan operations with appropriate HTTP methods:
   - `POST /api/v1/plans` — create plan
   - `GET /api/v1/plans` — list plans (with query filters: actor, date_from, date_to, status)
   - `GET /api/v1/plans/{plan_id}` — get plan (also supports query params: date, actor)
   - `PATCH /api/v1/plans/{plan_id}` — update plan
   - `DELETE /api/v1/plans/{plan_id}` — delete plan
   - `POST /api/v1/plans/{plan_id}/items` — add plan item
   - `PATCH /api/v1/plans/items/{item_id}` — update plan item
   - `DELETE /api/v1/plans/items/{item_id}` — remove plan item
   - `POST /api/v1/plans/items/{item_id}/reorder` — reorder plan item
   - `GET /api/v1/plans/weekly` — weekly plan view
   - `GET /api/v1/plans/monthly` — monthly plan view
   - `POST /api/v1/plans/{plan_id}/carry-over` — carry over items
   - `GET /api/v1/plans/vs-actual` — plan vs actual
3. All endpoints call the corresponding `core.planning` functions.
4. Request/response models use Pydantic with proper validation.
5. Error responses follow the existing pattern (HTTP 400/404/422 with structured error bodies).
6. The router is registered in `main.py` under the `/api/v1/plans` prefix.

### US-15: Frontend data layer for plans

**As** the frontend application,
**I need** TypeScript types, API client functions, and React Query hooks for plans
**so that** PlannerPage can fetch and mutate plan data using the established frontend patterns.

**Acceptance criteria:**
1. TypeScript types for `Plan`, `PlanItem`, `WeeklyPlan`, `MonthlyPlan`, `PlanVsActual` are defined in the types layer, matching the backend response shapes.
2. A `plans.ts` API client module is created in `src/taskyn/web/frontend/src/api/` following the existing pattern (`plansApi` object with typed methods).
3. Query keys for plans are added to the centralized `queryKeys` factory.
4. Query hooks are created: `usePlan(date, actor)`, `usePlans(filters)`, `useWeeklyPlan(weekStart, actor)`, `useMonthlyPlan(year, month, actor)`, `usePlanVsActual(date, actor)`.
5. Mutation hooks are created: `useCreatePlan`, `useUpdatePlan`, `useDeletePlan`, `useAddPlanItem`, `useRemovePlanItem`, `useReorderPlanItem`, `useUpdatePlanItem`, `useCarryOverPlan`.
6. Mutations invalidate relevant plan query keys on success.
7. Optimistic updates are used for reorder and outcome mutations.

---

## Out of scope

- **Actor management UI**: The current actor is derived from auth context. No UI for managing the actor list.
- **Plan templates**: No recurring plan templates or plan copying (beyond carry-over).
- **Multi-actor view**: The UI shows one actor's plans at a time. Cross-actor views are a future consideration.
- **Time blocking / calendar integration**: Plans are priority lists, not time-blocked schedules.
- **Mobile-specific layout**: Responsive is fine, but no dedicated mobile design.
- **Notifications / reminders**: No push notifications for plan completion or carry-over prompts.

---

## Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| Planning backend (`core.planning`) | Shipped (v0.9.0) | All 13 operations available |
| Plan MCP tools | Shipped (v0.9.0) | V can create plans via MCP |
| Plan database schema | Shipped | `plans` + `plan_items` tables with constraints |
| Plan enums (`PlanStatus`, `PlanOutcome`) | Shipped | In `db/enums.py` |
| REST API for plans | **Not started** | Blocks frontend work (US-14) |
| Frontend data layer | **Not started** | Types, API client, hooks (US-15) |
| Existing frontend patterns | Available | API client, query hooks, mutation hooks patterns established |

---

## Glossary

| Term | Meaning |
|------|---------|
| **Plan** | One actor's intended work for one day. Contains an ordered list of plan items. |
| **Plan item** | A single node linked to a daily plan, with a display order, optional planned minutes, and an outcome. |
| **Outcome** | What happened with an intention: pending, completed, partial, carried_over, dropped. |
| **Intention** | What the executor plans to *work on* (not what they plan to *finish*). A completed writing session is a completed intention even if the paper isn't done. |
| **Actor** | The person executing the plan (KH, VH). Plans are per-actor per-day. |
| **Carry-over** | Moving unfinished items from one plan to a future plan. Source items are marked carried_over with a link to the target plan. |
| **Horizon** | The time scope: day (single plan), week (7-day overview), month (calendar overview). |
| **Plannable** | A node type that the project's methodology allows in plans (defined by `can_be_planned` flag). |
