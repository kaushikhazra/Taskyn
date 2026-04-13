# Planner UI — Implementation Tasks

## 1. Backend REST API

- [x] **VH** creates Pydantic request/response schemas in `src/taskyn/web/backend/schemas/plans.py` — `PlanCreate`, `PlanItemInline`, `PlanUpdate`, `PlanItemAdd`, `PlanItemUpdate`, `PlanItemReorder`, `CarryOverRequest` with all field constraints (`ge=1` positions, `max_length` strings). _US-14_
- [x] **VH** creates plans router file `src/taskyn/web/backend/routes/plans.py` with `APIRouter(prefix="/plans", tags=["plans"])` and implements Plan CRUD endpoints: `POST /plans` (201), `GET /plans` (list with query filters), `GET /plans/by-date` (date+actor lookup, 200 with null for missing), `GET /plans/{plan_id}`, `PATCH /plans/{plan_id}`, `DELETE /plans/{plan_id}` (204). All call `call_mcp_tool()` and depend on `get_current_user`. Routes ordered per design section — static segments before `{plan_id}` captures. _US-14_
- [x] **VH** implements plan item endpoints in the same router: `POST /plans/{plan_id}/items` (201), `PATCH /plans/items/{item_id}`, `DELETE /plans/items/{item_id}` (204), `POST /plans/items/{item_id}/reorder`. Item routes registered before `{plan_id}` routes to avoid path capture conflicts. _US-14_
- [x] **VH** implements horizon view and analysis endpoints in the same router: `GET /plans/weekly`, `GET /plans/monthly`, `POST /plans/{plan_id}/carry-over`, `GET /plans/vs-actual`. All date params serialized via `.isoformat()` before passing to `call_mcp_tool()`. _US-14_
- [x] **VH** registers the plans router in `src/taskyn/web/backend/main.py` — `app.include_router(plans_router, prefix="/api/v1")` following the existing import pattern. _US-14_

## 2. Frontend Data Layer — Types

- [x] **VH** adds plan enum constants and core model types to `src/taskyn/web/frontend/src/types/index.ts` — `PLAN_STATUSES`, `PlanStatus`, `PLAN_OUTCOMES`, `PlanOutcome`, `Plan`, `PlanItem`, `PlanItemEnriched` (with node/project enrichment fields and `node_deleted` flag). _US-15_
- [x] **VH** adds plan DTO and request types to `src/taskyn/web/frontend/src/types/index.ts` — `PlanCreate`, `PlanItemSeed` (using `display_order` field name), `PlanUpdate`, `PlanItemAdd`, `PlanItemUpdate`, `PlanItemReorder`, `CarryOverRequest`, `CarryOverResult`, `CarryOverSkip`. _US-15_
- [x] **VH** adds aggregated view types to `src/taskyn/web/frontend/src/types/index.ts` — `WeeklyPlan`, `WeeklyDaySummary`, `WeeklyPlanSummary`, `MonthlyPlan`, `MonthlyDaySummary`, `MonthlyActorSummary`, `MonthlyMilestone`, `PlanVsActual`, `PlanVsActualItem`, `UnplannedItem`, `PlanVsActualSummary`, `PlanListFilters`. _US-15_

## 3. Frontend Data Layer — API Client

- [x] **VH** creates `src/taskyn/web/frontend/src/api/plans.ts` with the `plansApi` object — plan CRUD methods (`create`, `list`, `get`, `getByDate`, `update`, `delete`), plan item methods (`addItem`, `updateItem`, `removeItem`, `reorderItem`), aggregated view methods (`weekly`, `monthly`, `vsActual`), and carry-over method (`carryOver`). All methods use `api` from `./client` with proper typing. _US-15_

## 4. Frontend Data Layer — Query Keys & Hooks

- [x] **VH** adds plan query keys to `src/taskyn/web/frontend/src/api/queryKeys.ts` — `plans.all()`, `plans.list(filters)`, `plans.byDate(date, actor)`, `plans.detail(planId)`, `plans.weekly(weekStart, actor)`, `plans.monthly(year, month, actor)`, `plans.vsActual(date, actor)`. _US-15_
- [x] **VH** creates query hooks file `src/taskyn/web/frontend/src/hooks/queries/usePlans.ts` with `usePlan(date, actor)`, `usePlanById(planId)`, `usePlans(filters)`, `useWeeklyPlan(weekStart, actor)`, `useMonthlyPlan(year, month, actor)`, `usePlanVsActual(date, actor)`. Exports added to `hooks/queries/index.ts`. _US-15_
- [x] **VH** creates mutation hooks file `src/taskyn/web/frontend/src/hooks/mutations/usePlanMutations.ts` with standard mutations: `useCreatePlan` (invalidates plans + dashboard; 409 handler auto-refreshes), `useUpdatePlan`, `useDeletePlan`, `useAddPlanItem`, `useRemovePlanItem`, `useCarryOverPlan` (toast with carried/skipped counts). Exports added to `hooks/mutations/index.ts`. _US-15_
- [x] **VH** implements optimistic mutation hooks in the same file: `useReorderPlanItem(date, actor)` with splice + `display_order` recompute (1-based, `newPosition - 1` for splice index — N-01 fix), and `useUpdatePlanItem(date, actor)` with field-spread on matching item. Both use `onMutate`/`onError`/`onSettled` pattern per design. _US-15_

## 5. Frontend — URL State & Page Shell

- [x] **VH** creates `src/taskyn/web/frontend/src/hooks/usePlannerParams.ts` — reads/writes `useSearchParams()` for `view` (day|week|month, default: day), `date` (ISO string, default: today), `actor` (default: from AuthContext). Exposes typed getters and setters (`setDate`, `setView` with date-snapping logic per design section 13). _US-2_
- [x] **VH** replaces the existing `PlannerPage.tsx` content with the new layout: imports `usePlannerParams`, renders `PlannerToolbar` and conditionally renders `DayView` / `WeekView` / `MonthView` based on `view` param. URL reflects selected date for bookmarkability. _US-1, US-2_

## 6. Frontend — Shared Atoms

- [x] **VH** creates `src/taskyn/web/frontend/src/components/atoms/DragHandle.tsx` — grip icon, hidden when `disabled` prop is true. CSS class `.plan-item` drag handle styling. _US-5_
- [x] **VH** creates `src/taskyn/web/frontend/src/components/atoms/OutcomeIcon.tsx` — renders per-outcome icon/color (pending: muted circle, completed: green checkmark, partial: amber half-circle, dropped: muted, carried_over: gray arrow). _US-3_
- [x] **VH** creates `src/taskyn/web/frontend/src/components/atoms/OutcomeBar.tsx` — horizontal stacked bar from `Record<PlanOutcome, number>` counts, supports `size` prop (normal for week, mini for month). CSS classes `.outcome-bar` and `.outcome-bar__segment--*`. _US-9, US-10_
- [x] **VH** creates `src/taskyn/web/frontend/src/components/atoms/PlannedMinutes.tsx` — displays minutes as chip ("30m"), supports `editable` prop with inline edit and `onChange` callback. _US-1, US-7_

## 7. Frontend — Toolbar Molecules

- [x] **VH** creates `src/taskyn/web/frontend/src/components/molecules/DateNavigator.tsx` — prev/next buttons + formatted date label (adapts per view: day shows "Apr 12, 2026 (Sun)", week shows date range, month shows "April 2026") + "Today"/"This Week" button. Step size adapts per view (+/-1 day, +/-7 days, +/-1 month). _US-2_
- [x] **VH** creates `src/taskyn/web/frontend/src/components/molecules/ViewSwitcher.tsx` — three toggle buttons (Day|Week|Month) with active state CSS. Calls `onViewChange` prop. _US-9, US-10_
- [x] **VH** creates `src/taskyn/web/frontend/src/components/organisms/PlannerToolbar.tsx` — composes `DateNavigator` + `ViewSwitcher`, receives `date`, `view`, `onDateChange`, `onViewChange` props. CSS class `.planner-toolbar`. _US-2_

## 8. Frontend — Day View Core (Plan Display)

- [x] **VH** creates `src/taskyn/web/frontend/src/components/molecules/EmptyPlanState.tsx` — icon + message ("No plan for this date") + "Create Plan" button that calls `useCreatePlan` with current date and actor. _US-6_
- [x] **VH** creates `src/taskyn/web/frontend/src/components/molecules/PlanHeader.tsx` — displays plan notes (collapsible), status badge (active/completed), action buttons: "Complete Plan" (US-13), "Carry Over" (US-11), "Plan vs Actual" toggle (US-12). Completed plans show "Completed" badge, no Complete/CarryOver buttons. _US-1, US-13_
- [x] **VH** creates `src/taskyn/web/frontend/src/components/molecules/OutcomeControl.tsx` — four clickable OutcomeIcon buttons (pending/completed/partial/dropped) in radio-group pattern. `carried_over` shown as display-only icon. Calls `onChange` with selected outcome. `disabled` prop for completed plans. _US-3_
- [x] **VH** creates `src/taskyn/web/frontend/src/components/molecules/OutcomeNotes.tsx` — inline expandable text field for outcome notes. Shows existing notes, supports edit. Saves via parent's `onNotesChange` callback. Editable even on completed plans (US-13 AC-5). _US-4_
- [x] **VH** creates `src/taskyn/web/frontend/src/components/molecules/PlanItemRow.tsx` — composes DragHandle + NodeTypeBadge (existing) + item title (or "(deleted)" for `node_deleted`) + project name + PlannedMinutes + OutcomeControl + OutcomeNotes + remove button. Remove shows confirmation if outcome !== pending (US-8 AC-3). Drag handle hidden and remove button hidden when plan is completed. CSS classes `.plan-item`, `.plan-item--dropped` (line-through), `.plan-item--carried` (muted). _US-1, US-3, US-4, US-5, US-8_
- [x] **VH** creates `src/taskyn/web/frontend/src/components/organisms/PlanItemList.tsx` — renders N x PlanItemRow in a DnD container using HTML5 native drag-and-drop. Manages `dragItemId`/`dropIndex` local state. `onDragStart` sets effect, `onDragOver` shows drop indicator (`.plan-item--drop-above`), `onDrop` calls `useReorderPlanItem` with `targetIndex + 1` (1-based). `.plan-item--dragging` opacity on dragged item. DnD disabled when plan is completed. _US-1, US-5_
- [x] **VH** creates `src/taskyn/web/frontend/src/components/organisms/DayPlanPanel.tsx` — composes PlanHeader + PlanItemList + AddItemButton + PlanVsActualPanel (collapsible) + CarryOverModal trigger. Receives `plan` and `date`/`actor` props. Wires outcome/reorder/remove mutations from hooks. CSS class `.plan-panel`, `.plan-panel--completed` for completed plans. _US-1_

## 9. Frontend — Day View (Remaining Features)

- [x] **VH** creates `src/taskyn/web/frontend/src/components/molecules/NodePickerRow.tsx` — displays node type badge + title + project name + "[+ Add]" button. Used inside NodePickerModal. _US-7_
- [x] **VH** creates `src/taskyn/web/frontend/src/components/organisms/NodePickerModal.tsx` — extends existing Modal pattern. Contains SearchBar (existing) + project filter dropdown + NodePickerList. Fetches nodes via `useNodes({ status: ['backlog','ready','in_progress'] })` and methodology via `useMethodology(projectId)` for client-side plannable filtering (F-04). "[+ Add]" calls `useAddPlanItem`. Optional planned minutes input on add. Hidden when plan is completed. Methodology loaded lazily per project filter selection (N-02). _US-7_
- [x] **VH** creates `src/taskyn/web/frontend/src/components/organisms/CarryOverModal.tsx` — extends Modal. Shows checklist of pending + partial items (pre-checked), deleted-node items with warning icon unchecked by default (M-03). Target date picker (default: tomorrow). Summary line ("4 of 6 items selected"). Calls `useCarryOverPlan` on confirm. On success: toast + navigate to target date in day view. _US-11_
- [x] **VH** creates `src/taskyn/web/frontend/src/components/molecules/PlanVsActualSummary.tsx` — four stat cards: total planned minutes, total actual minutes, total unplanned minutes, overall delta. _US-12_
- [x] **VH** creates `src/taskyn/web/frontend/src/components/molecules/PlanVsActualRow.tsx` — item title + planned minutes + actual minutes + delta (colored: green positive, red negative). CSS class `.pva-row`. _US-12_
- [x] **VH** creates `src/taskyn/web/frontend/src/components/organisms/PlanVsActualPanel.tsx` — collapsible panel with `usePlanVsActual(date, actor)`. Renders PlanVsActualSummary + N x PlanVsActualRow for planned items + UnplannedWorkSection (heading + unplanned rows with `.pva-row--unplanned` border). Toggled by "Plan vs Actual" button in PlanHeader. _US-12_
- [x] **VH** implements plan completion gate in DayPlanPanel — "Complete Plan" button disabled + inline warning listing pending item titles when any items have `outcome === 'pending'` (US-13 AC-2). Enabled state calls `useUpdatePlan({ status: 'completed' })`. _US-13_
- [x] **VH** implements plan deletion with conditional confirmation dialog in DayView — if plan has items with outcome !== pending, shows detailed warning ("N items with recorded outcomes, cannot be undone"); otherwise shows simple "Delete plan for {date}?" dialog (M-04). Calls `useDeletePlan`. _US-13_

## 10. Frontend — Day View Assembly

- [x] **VH** creates the `DayView` component (can be in `src/taskyn/web/frontend/src/pages/PlannerPage.tsx` or a separate file) — calls `usePlan(date, actor)`, renders loading skeleton / EmptyPlanState / DayPlanPanel based on query state. Wires create-plan 409 conflict handler (M-05: invalidate query + info toast when plan already exists). _US-1, US-6_

## 11. Frontend — Week View

- [x] **VH** creates `src/taskyn/web/frontend/src/components/molecules/WeekDayCard.tsx` — displays day label + item count + status badge + OutcomeBar + planned/actual minutes. Three visual states: no plan (dashed border, muted), active (solid), completed (success tint + checkmark). Click navigates to day view for that date. _US-9_
- [x] **VH** creates `src/taskyn/web/frontend/src/components/molecules/WeekSummaryBar.tsx` — total items + total planned minutes + total actual minutes + outcome breakdown OutcomeBar (full width). _US-9_
- [x] **VH** creates `src/taskyn/web/frontend/src/components/organisms/WeekGrid.tsx` — 7-column CSS grid (`.week-grid`) rendering Mon-Sun WeekDayCards from `WeeklyDaySummary[]`. _US-9_
- [x] **VH** creates `src/taskyn/web/frontend/src/components/organisms/WeekPanel.tsx` — composes WeekSummaryBar + WeekGrid. _US-9_
- [x] **VH** creates `WeekView` component — calls `useWeeklyPlan(weekStart, actor)`, renders loading skeleton or WeekPanel. Clicking a day card calls `onDateChange(day, 'day')` to switch to day view. _US-9_

## 12. Frontend — Month View

- [x] **VH** creates `src/taskyn/web/frontend/src/components/molecules/MonthDayCell.tsx` — displays day number + mini OutcomeBar + item count. States: no plan (empty), has plan active (bar + count), completed (green dot), outside month (dimmed, non-interactive), today (highlighted border ring `.month-day-cell--today`). Click navigates to day view. _US-10_
- [x] **VH** creates `src/taskyn/web/frontend/src/components/molecules/MonthSummarySection.tsx` — days with plans count + total items + total planned minutes + outcome breakdown bar + actual minutes + active milestones list. _US-10_
- [x] **VH** creates `src/taskyn/web/frontend/src/components/organisms/MonthCalendarGrid.tsx` — header row (Mon-Sun) + 5-6 rows of MonthDayCells. CSS class `.month-calendar-grid` (7-column grid). Fills in days from previous/next month as outside-month cells. _US-10_
- [x] **VH** creates `src/taskyn/web/frontend/src/components/organisms/MonthPanel.tsx` — composes MonthSummarySection + MonthCalendarGrid. _US-10_
- [x] **VH** creates `MonthView` component — calls `useMonthlyPlan(year, month, actor)`, renders loading skeleton or MonthPanel. Clicking a day cell calls `onDateChange(day, 'day')` to switch to day view. _US-10_

## 13. Frontend — CSS

- [x] **VH** adds all planner CSS classes to the appropriate stylesheet — planner layout (`.planner-toolbar`, `.planner-view`), day view (`.plan-panel`, `.plan-panel--completed`, `.plan-item`, `.plan-item--dragging`, `.plan-item--drop-above`, `.plan-item--completed`, `.plan-item--partial`, `.plan-item--dropped`, `.plan-item--carried`, `.plan-empty-state`), outcome (`.outcome-control`, `.outcome-icon--*`), week view (`.week-grid`, `.week-day-card`, `.week-day-card--no-plan`, `.week-day-card--completed`, `.week-summary-bar`), month view (`.month-calendar-grid`, `.month-day-cell`, `.month-day-cell--today`, `.month-day-cell--outside`, `.month-day-cell--has-plan`, `.month-summary`), shared (`.outcome-bar`, `.outcome-bar__segment--*`), plan-vs-actual (`.pva-panel`, `.pva-summary`, `.pva-row`, `.pva-row--unplanned`, `.pva-delta--positive`, `.pva-delta--negative`). _US-1 through US-13_

## 14. Integration Testing

- [ ] **VH** writes backend integration tests for plan CRUD endpoints in `tests/web/test_plans_routes.py` — test create plan (201), get by date (200 with data, 200 with null), get by id, list with filters, update plan, delete plan (204). Verify route ordering doesn't capture "weekly"/"monthly"/"vs-actual" as plan_id. _US-14_
- [ ] **VH** writes backend integration tests for plan item endpoints — test add item (201), update item outcome/notes, remove item (204), reorder item (1-based position validation). _US-14_
- [ ] **VH** writes backend integration tests for horizon and analysis endpoints — test weekly view, monthly view, carry-over (with and without item_ids), plan-vs-actual. _US-14_
- [ ] **VH** writes end-to-end smoke test via Puppeteer MCP against `http://localhost:3020` — navigate to Planner page, verify day view loads (or empty state), create a plan, add an item via node picker, mark outcome, switch to week view, switch to month view, navigate between dates. _US-1, US-2, US-3, US-6, US-7, US-9, US-10_
