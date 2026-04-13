# Planner UI Frontend Design

Covers US-1 through US-13. Backend (US-14) and data layer (US-15) are prerequisites but designed separately.

---

## 1. URL-Driven State

All view state lives in URL search params so every view is bookmarkable and shareable.

```
/planner?view=day&date=2026-04-12&actor=KH
/planner?view=week&date=2026-04-06&actor=KH    (date = week start, Monday)
/planner?view=month&date=2026-04-01&actor=KH   (date = month start)
```

| Param   | Default          | Constraint                        |
|---------|------------------|-----------------------------------|
| `view`  | `day`            | `day` \| `week` \| `month`       |
| `date`  | today ISO string | ISO date; week/month snap to start|
| `actor` | from AuthContext  | string identifier (KH, VH)       |

**Hook:** `usePlannerParams()` reads/writes `useSearchParams()`, exposes typed getters + setters (`setDate`, `setView`). All child components receive values as props from PlannerPage; they never read URL directly.

---

## 2. PlannerPage Layout

```
PlannerPage
+------------------------------------------------------------+
| PlannerToolbar                                              |
|  [< prev] [date display] [next >] [Today]  [Day|Week|Month]|
+------------------------------------------------------------+
| {view === 'day'   && <DayView   date actor />}             |
| {view === 'week'  && <WeekView  date actor />}             |
| {view === 'month' && <MonthView date actor />}             |
+------------------------------------------------------------+
```

PlannerPage is the router-level component. It owns `usePlannerParams()` and passes resolved `date`, `actor`, `view` down. No data fetching at this level — each view fetches its own data.

---

## 3. PlannerToolbar (organism)

```
PlannerToolbar { date, view, onDateChange, onViewChange }
+----------------------------------------------------------------+
| DateNavigator (molecule)       |  ViewSwitcher (molecule)      |
|  [<] [Apr 12, 2026 (Sun)] [>] |  [Day] [Week] [Month]         |
|  [Today]                       |                               |
+----------------------------------------------------------------+
```

| Sub-component   | Type     | Props                              | Behavior                                                        |
|-----------------|----------|------------------------------------|-----------------------------------------------------------------|
| DateNavigator   | molecule | `date, view, onChange`             | Prev/next step depends on view: +/-1 day, +/-7 days, +/-1 month|
| ViewSwitcher    | molecule | `view, onChange`                   | Three toggle buttons; active state via CSS class                |

DateNavigator label adapts per view:
- Day: `Apr 12, 2026 (Sun)`
- Week: `Apr 6 - 12, 2026`
- Month: `April 2026`

---

## 4. Day View

### 4.1 Component Tree

```
DayView { date, actor }
|
|-- usePlan(date, actor)                    // React Query
|
+-- if loading: <Skeleton />
+-- if no plan:
|     EmptyPlanState (molecule)
|       [Create Plan] button  -----> useCreatePlan mutation
|
+-- if plan exists:
      DayPlanPanel (organism)
      |
      +-- PlanHeader (molecule)
      |     plan.notes (collapsible)
      |     Badge: plan.status (active | completed)
      |     [Complete Plan] button            (US-13)
      |     [Carry Over] button               (US-11)
      |     [Plan vs Actual] toggle           (US-12)
      |
      +-- PlanItemList (organism)             (US-1, US-5)
      |     DnD container (HTML5 native)
      |     |
      |     +-- PlanItemRow (molecule) x N    (ordered by display_order)
      |           DragHandle (atom)
      |           NodeTypeBadge (atom)         existing Badge atom w/ node type
      |           item title (or "(deleted)")
      |           project name (muted text)
      |           PlannedMinutes (atom)        "30m" chip, editable inline
      |           OutcomeControl (molecule)    (US-3)
      |           OutcomeNotes (molecule)      (US-4, expandable inline)
      |           [x] remove button            (US-8)
      |
      +-- AddItemButton (atom)                (US-7)
      |     visible only when plan.status === 'active'
      |     click opens NodePickerModal
      |
      +-- PlanVsActualPanel (organism)        (US-12, collapsible)
      |     usePlanVsActual(date, actor)
      |     |
      |     +-- PlanVsActualSummary (molecule)
      |     |     total planned / actual / unplanned / delta
      |     |
      |     +-- PlanVsActualRow (molecule) x N
      |     |     item title | planned min | actual min | delta
      |     |
      |     +-- UnplannedWorkSection (molecule)
      |           "Unplanned" heading
      |           UnplannedRow x N: title | actual min | project
      |
      +-- CarryOverModal (organism)           (US-11)
            item checklist (pending + partial items pre-checked)
            target date picker (default: tomorrow)
            [Carry Over] button -----> useCarryOverPlan mutation
```

### 4.2 PlanItemRow Detail

```
PlanItemRow { item, planStatus, onReorder, onRemove }
+-------------------------------------------------------------------+
| [::] | [spec] | Design the auth flow | taskyn | 30m | [v] | [...] |
|  ^       ^           ^                   ^      ^     ^      ^    |
|  |       |           |                   |      |     |      |    |
|  drag  type        title              project  mins outcome notes |
|  handle badge                          name   chip  ctrl   menu  |
+-------------------------------------------------------------------+
```

- Drag handle hidden when `planStatus === 'completed'` (US-13: read-only).
- Remove button shows confirmation dialog if outcome !== 'pending' (US-8 AC-3).
- Title shows node title from `item.node_title`, or `"(deleted)"` when `item.node_deleted === true` (US-1 AC-4).

### 4.3 OutcomeControl (molecule)

```
OutcomeControl { value, onChange, disabled }
+---------------------------------------------+
| ( ) pending  | (v) completed | (~) partial | (x) dropped |
+---------------------------------------------+

Visual encoding:
  pending    -> neutral/empty circle
  completed  -> green checkmark
  partial    -> amber half-circle
  dropped    -> muted, line-through on parent row
  carried_over -> gray arrow icon (display-only, not selectable)
```

Clicking a state calls `useUpdatePlanItem({ outcome })`. Optimistic update via React Query `onMutate`.

`disabled` = true when plan is completed (US-13 AC-5: read-only except notes).

---

## 5. Week View

### 5.1 Component Tree

```
WeekView { date, actor }
|
|-- useWeeklyPlan(date, actor)              // React Query
|
+-- if loading: <Skeleton />
+-- if data:
      WeekPanel (organism)
      |
      +-- WeekSummaryBar (molecule)
      |     total items | total planned min | total actual min
      |     outcome breakdown: [=== completed ][== partial][= dropped][ pending]
      |
      +-- WeekGrid (organism)
            7 x WeekDayCard (molecule)       Mon through Sun
            |
            +-- WeekDayCard { daySummary, onClick }
                  +-------------------------------+
                  | Mon, Apr 6                    |
                  | 5 items           [active]    |
                  |                               |
                  | [=== 3 ][= 1 ][  1  ]        |  <- OutcomeBar (atom)
                  | planned: 180m  actual: 150m   |
                  +-------------------------------+
                  click -> onDateChange(day, 'day')   navigates to day view
```

### 5.2 WeekDayCard States

| State      | Visual                                      |
|------------|---------------------------------------------|
| No plan    | Muted card, dashed border, "No plan" text   |
| Active     | Normal card, solid border                   |
| Completed  | Subtle success tint, checkmark badge        |

---

## 6. Month View

### 6.1 Component Tree

```
MonthView { date, actor }
|
|-- useMonthlyPlan(year, month, actor)       // React Query
|
+-- if loading: <Skeleton />
+-- if data:
      MonthPanel (organism)
      |
      +-- MonthSummarySection (molecule)
      |     days with plans: 18/30  |  total items: 87  |  total planned: 2400m
      |     outcome breakdown bar
      |     actual minutes | active milestones
      |
      +-- MonthCalendarGrid (organism)
            header row: Mon Tue Wed Thu Fri Sat Sun
            5-6 rows of MonthDayCell (molecule)
            |
            +-- MonthDayCell { day, daySummary, isCurrentMonth, onClick }
                  +------------------+
                  | 12               |
                  | [====][==][ ]    |  <- OutcomeBar (atom), mini variant
                  | 5 items          |
                  +------------------+
                  click -> onDateChange(day, 'day')
```

### 6.2 MonthDayCell States

| State              | Visual                                   |
|--------------------|------------------------------------------|
| No plan            | Empty cell, no outcome bar               |
| Has plan (active)  | Outcome bar + item count                 |
| Has plan (done)    | Green dot indicator + outcome bar        |
| Outside month      | Dimmed background, non-interactive       |
| Today              | Highlighted border ring                  |

---

## 7. Shared Components (new atoms/molecules)

### 7.1 New Atoms

| Atom            | Props                          | Used in                       |
|-----------------|--------------------------------|-------------------------------|
| DragHandle      | `disabled?: boolean`           | PlanItemRow                   |
| OutcomeBar      | `counts: OutcomeCounts, size`  | WeekDayCard, MonthDayCell     |
| PlannedMinutes  | `minutes, editable, onChange`  | PlanItemRow                   |
| OutcomeIcon     | `outcome: PlanOutcome`         | OutcomeControl, PlanItemRow   |

### 7.2 New Molecules

| Molecule           | Composition                           | Used in                   |
|--------------------|---------------------------------------|---------------------------|
| DateNavigator      | Button + text display + Button        | PlannerToolbar            |
| ViewSwitcher       | 3 x Button (toggle group)            | PlannerToolbar            |
| PlanHeader         | Badge + text + Button actions         | DayPlanPanel              |
| PlanItemRow        | DragHandle + Badge + text + controls  | PlanItemList              |
| OutcomeControl     | 4 x OutcomeIcon (radio-like)         | PlanItemRow               |
| OutcomeNotes       | inline text + edit toggle             | PlanItemRow               |
| EmptyPlanState     | Icon + text + Button                  | DayView                   |
| WeekDayCard        | text + Badge + OutcomeBar             | WeekGrid                  |
| MonthDayCell       | day number + OutcomeBar + count       | MonthCalendarGrid         |
| WeekSummaryBar     | StatCard-like + OutcomeBar            | WeekPanel                 |
| MonthSummarySection| StatCards + OutcomeBar + milestones   | MonthPanel                |
| PlanVsActualRow    | text + 3 number columns               | PlanVsActualPanel         |
| PlanVsActualSummary| 4 x StatCard                          | PlanVsActualPanel         |

### 7.3 New Organisms

| Organism            | Composition                          | Used in       |
|---------------------|--------------------------------------|---------------|
| PlannerToolbar      | DateNavigator + ViewSwitcher         | PlannerPage   |
| DayPlanPanel        | PlanHeader + PlanItemList + actions  | DayView       |
| PlanItemList        | N x PlanItemRow (DnD container)      | DayPlanPanel  |
| PlanVsActualPanel   | Summary + rows + unplanned section   | DayPlanPanel  |
| CarryOverModal      | extends Modal + item checklist       | DayView       |
| NodePickerModal     | extends Modal + SearchBar + list     | DayView       |
| WeekGrid            | 7 x WeekDayCard                     | WeekView      |
| WeekPanel           | WeekSummaryBar + WeekGrid            | WeekView      |
| MonthCalendarGrid   | header + 5-6 rows x MonthDayCell     | MonthView     |
| MonthPanel          | MonthSummarySection + MonthCalGrid   | MonthView     |

---

## 8. State Management Summary

```
State Layer Diagram
====================

URL (useSearchParams)          React Query (server cache)         Local (useState)
-----------------------        ----------------------------       -----------------
view: day|week|month           usePlan(date, actor)               dragItemId
date: ISO string               useWeeklyPlan(weekStart, actor)    dropIndex
actor: string                  useMonthlyPlan(year, month, actor) expandedNotes: Set
                               usePlanVsActual(date, actor)       showVsActual: bool
                                                                  carryOverModalOpen
                                                                  nodePickerModalOpen
                                                                  selectedCarryItems

Mutations (optimistic)         Mutations (invalidate-on-success)
-----------------------        ---------------------------------
useReorderPlanItem             useCreatePlan
useUpdatePlanItem (outcome)    useDeletePlan
                               useAddPlanItem
                               useRemovePlanItem
                               useCarryOverPlan
                               useUpdatePlan (complete)
```

### Why this split

| Category          | Rationale                                                        |
|-------------------|------------------------------------------------------------------|
| URL params        | View, date, actor define *what* the user is looking at. Bookmark/share/back-button must work. |
| React Query       | All plan data is server-owned. Standard query/mutation pattern already established in codebase. |
| Local state       | Transient UI state (which item is being dragged, which notes are expanded). No persistence needed. |

No new Context providers. The existing AuthContext supplies the default `actor`. The existing ToastProvider handles mutation feedback. No new global state.

---

## 9. Drag-and-Drop Approach

Consistent with KanbanPage: **HTML5 native Drag and Drop API**, no library.

### State

```typescript
// in PlanItemList
const [dragItemId, setDragItemId] = useState<string | null>(null);
const [dropIndex, setDropIndex] = useState<number | null>(null);
```

### Event Flow

```
onDragStart(item.id)
  -> setDragItemId(item.id)
  -> e.dataTransfer.effectAllowed = 'move'

onDragOver(e, index)
  -> e.preventDefault()
  -> setDropIndex(index)        // visual drop indicator

onDragLeave()
  -> setDropIndex(null)

onDrop(e, targetIndex)
  -> if dragItemId === null return
  -> optimistic reorder: splice items in query cache
  -> call reorderPlanItem.mutate({ itemId: dragItemId, newPosition: targetIndex + 1 })
     // +1: backend uses 1-based positions (F-05)
  -> onError: rollback from onMutate snapshot
  -> setDragItemId(null), setDropIndex(null)

onDragEnd()
  -> setDragItemId(null), setDropIndex(null)    // cleanup if dropped outside
```

### Visual Feedback

| State              | CSS class on PlanItemRow       | Effect                           |
|--------------------|-------------------------------|----------------------------------|
| Being dragged      | `.plan-item--dragging`         | Reduced opacity (0.4)           |
| Valid drop target  | `.plan-item--drop-above`       | 2px blue top-border indicator   |
| Completed plan     | DragHandle hidden, no draggable| Drag disabled entirely          |

### Optimistic Reorder

```typescript
// useReorderPlanItem mutation
onMutate: async ({ itemId, newPosition }) => {
  await queryClient.cancelQueries({ queryKey: planKeys.detail(date, actor) });
  const previous = queryClient.getQueryData(planKeys.detail(date, actor));
  queryClient.setQueryData(planKeys.detail(date, actor), (old) => {
    const items = [...old.items];
    const fromIdx = items.findIndex(i => i.id === itemId);
    const [moved] = items.splice(fromIdx, 1);
    items.splice(newPosition, 0, moved);
    return { ...old, items };
  });
  return { previous };
},
onError: (_err, _vars, context) => {
  queryClient.setQueryData(planKeys.detail(date, actor), context.previous);
},
onSettled: () => {
  queryClient.invalidateQueries({ queryKey: planKeys.detail(date, actor) });
}
```

---

## 10. NodePickerModal (US-7)

```
NodePickerModal { planId, onClose }
|
|-- useNodes({ status: ['backlog','ready','in_progress'] })
|-- useMethodology(projectId)             // for can_be_planned filtering (F-04: client-side)
|
+-- SearchBar (existing molecule)         filter by title
+-- project filter dropdown               filter by project
+-- NodePickerList
      NodePickerRow x N
        [spec] | Design the auth flow | taskyn | [+ Add]
        click [+ Add] -> useAddPlanItem.mutate({ planId, nodeId })
        optional: planned minutes input on add
```

Reuses existing `useNodes` hook with status filters. Plannable filtering is done **client-side** (F-04): the modal fetches methodology info per project and excludes node types where `can_be_planned === false`. This avoids upstream changes to the nodes API.

---

## 11. CarryOverModal (US-11)

```
CarryOverModal { plan, onClose }
|
+-- heading: "Carry over from {date}"
+-- item checklist (pre-checked: pending + partial items)
|     [ ] item title (outcome badge)     <- Checkbox (existing atom)
|     [x] item title (outcome badge)
|     [x] ⚠ item title (deleted) (badge) <- deleted-node items show warning icon (M-03)
|     ...
+-- target date picker (default: tomorrow)
+-- summary: "4 of 6 items selected"
+-- [Cancel] [Carry Over] buttons
      click -> useCarryOverPlan.mutate({ sourcePlanId, targetDate, itemIds })
      on success: toast + navigate to target date in day view

**Deleted-node warning (M-03):** Items where `node_deleted === true` are shown with a warning icon and "(deleted)" label in the checklist, matching US-1 AC-4 styling. They are unchecked by default (unlike pending/partial items). This lets the user consciously decide to carry over broken references.
```

---

## 12. File Structure

```
src/taskyn/web/frontend/src/
|
+-- pages/
|     PlannerPage.tsx              (router entry, usePlannerParams, view dispatch)
|
+-- components/
|     +-- atoms/
|     |     DragHandle.tsx
|     |     OutcomeBar.tsx
|     |     OutcomeIcon.tsx
|     |     PlannedMinutes.tsx
|     |
|     +-- molecules/
|     |     DateNavigator.tsx
|     |     ViewSwitcher.tsx
|     |     PlanHeader.tsx
|     |     PlanItemRow.tsx
|     |     OutcomeControl.tsx
|     |     OutcomeNotes.tsx
|     |     EmptyPlanState.tsx
|     |     WeekDayCard.tsx
|     |     MonthDayCell.tsx
|     |     WeekSummaryBar.tsx
|     |     MonthSummarySection.tsx
|     |     PlanVsActualRow.tsx
|     |     PlanVsActualSummary.tsx
|     |     NodePickerRow.tsx
|     |
|     +-- organisms/
|           PlannerToolbar.tsx
|           DayPlanPanel.tsx
|           PlanItemList.tsx
|           PlanVsActualPanel.tsx
|           CarryOverModal.tsx
|           NodePickerModal.tsx
|           WeekGrid.tsx
|           WeekPanel.tsx
|           MonthCalendarGrid.tsx
|           MonthPanel.tsx
|
+-- hooks/
|     usePlannerParams.ts          (URL search params wrapper)
|
+-- (existing query/mutation hooks defined by US-15 design)
```

No new templates — PlannerPage renders inside the existing AppShell via ProtectedRoute, same as KanbanPage and DashboardPage.

---

## 12b. Edge Case Handling (from dryrun M-04, M-05)

### Plan Deletion Confirmation (M-04)

Deleting a plan is destructive — all item history (outcomes, notes) is lost. Before calling `useDeletePlan`:

```
if plan has items with outcome !== 'pending':
  show ConfirmDialog:
    "This plan has {N} items with recorded outcomes. Deleting it will permanently
     remove all outcome data. This cannot be undone."
    [Cancel] [Delete Plan]
else:
  show simple ConfirmDialog:
    "Delete plan for {date}?"
    [Cancel] [Delete]
```

### 409 Conflict on Plan Create (M-05)

When `useCreatePlan` receives a 409 (plan already exists for that date+actor — e.g., Velasari created one via MCP between page load and button click):

```ts
// In useCreatePlan's onError callback:
if (error.status === 409) {
  // Invalidate so the existing plan loads automatically
  queryClient.invalidateQueries({ queryKey: queryKeys.plans.byDate(date, actor) });
  addToast('info', 'A plan already exists for this date');
} else {
  addToast('error', error.message);
}
```

This replaces the EmptyPlanState with the existing plan without requiring a manual refresh.

---

## 13. View Switching Behavior

| From     | To     | State preserved    | State reset               |
|----------|--------|--------------------|---------------------------|
| Day      | Week   | actor              | date snaps to week start containing current date |
| Day      | Month  | actor              | date snaps to month start containing current date |
| Week     | Day    | actor              | date = clicked day, or Monday of current week if no click |
| Week     | Month  | actor              | date snaps to month containing week start |
| Month    | Day    | actor              | date = clicked day, or 1st of month if no click |
| Month    | Week   | actor              | date snaps to week containing 1st of month |

The `setView` function in `usePlannerParams` handles date snapping. Clicking a day in week/month view calls `onDateChange(day, 'day')` which sets both date and view simultaneously.

---

## 14. Completed Plan Behavior (US-13)

When `plan.status === 'completed'`:

| Component        | Change                                              |
|------------------|-----------------------------------------------------|
| PlanHeader       | "Completed" badge, no Complete/CarryOver buttons    |
| PlanItemList     | `draggable` removed, DragHandle hidden              |
| PlanItemRow      | OutcomeControl disabled, remove button hidden       |
| OutcomeNotes     | Still editable (US-13 AC-5)                         |
| AddItemButton    | Hidden                                              |
| Overall panel    | Muted background (`plan-panel--completed` CSS class)|

---

## 15. Completion Gate (US-13 AC-2)

Before allowing "Complete Plan":

```
if plan.items.some(item => item.outcome === 'pending'):
  show inline warning listing pending items by title
  disable Complete button
else:
  enable Complete button
```

No modal confirmation — the gate is the pending-items check itself.

---

## 16. CSS Classes (new)

```css
/* Planner layout */
.planner-toolbar { }
.planner-view { }

/* Day view */
.plan-panel { }
.plan-panel--completed { opacity: 0.85; }
.plan-header { }
.plan-item-list { }
.plan-item { }
.plan-item--dragging { opacity: 0.4; }
.plan-item--drop-above { border-top: 2px solid var(--color-primary); }
.plan-item--completed { }
.plan-item--partial { }
.plan-item--dropped { opacity: 0.6; text-decoration: line-through; }
.plan-item--carried { opacity: 0.6; }
.plan-empty-state { }

/* Outcome */
.outcome-control { }
.outcome-icon { }
.outcome-icon--pending { color: var(--text-muted); }
.outcome-icon--completed { color: var(--status-done); }
.outcome-icon--partial { color: var(--status-progress); }
.outcome-icon--dropped { color: var(--text-muted); }

/* Week view */
.week-grid { display: grid; grid-template-columns: repeat(7, 1fr); }
.week-day-card { }
.week-day-card--no-plan { border-style: dashed; opacity: 0.6; }
.week-day-card--completed { }
.week-summary-bar { }

/* Month view */
.month-calendar-grid { display: grid; grid-template-columns: repeat(7, 1fr); }
.month-day-cell { }
.month-day-cell--today { box-shadow: inset 0 0 0 2px var(--color-primary); }
.month-day-cell--outside { opacity: 0.3; pointer-events: none; }
.month-day-cell--has-plan { }
.month-summary { }

/* Shared */
.outcome-bar { display: flex; height: 4px; border-radius: 2px; overflow: hidden; }
.outcome-bar__segment--completed { background: var(--status-done); }
.outcome-bar__segment--partial { background: var(--status-progress); }
.outcome-bar__segment--dropped { background: var(--text-muted); }
.outcome-bar__segment--pending { background: var(--border-subtle); }

/* Plan vs Actual */
.pva-panel { }
.pva-summary { }
.pva-row { }
.pva-row--unplanned { border-left: 3px solid var(--status-progress); }
.pva-delta--positive { color: var(--status-done); }
.pva-delta--negative { color: var(--color-danger); }
```
