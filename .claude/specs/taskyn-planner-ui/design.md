# Planner UI — Design

This design covers three layers of the Planner UI feature. The **Backend REST API** (US-14) defines the FastAPI router, Pydantic schemas, and 14 endpoints that proxy to MCP tools. The **Frontend Component Architecture** (US-1 through US-13) specifies the full component tree — from URL-driven state through day/week/month views, drag-and-drop, modals, and CSS classes. The **Frontend Data Layer** (US-15) provides TypeScript types, the API client, React Query keys, query hooks, and mutation hooks (including optimistic updates for reorder and outcome changes).

Section design files (`design-backend.md`, `design-frontend.md`, `design-data.md`) are retained alongside this document for reference.

---

# Part 1 — Backend REST API

## Router Setup

**File**: `src/taskyn/web/backend/routes/plans.py`
**Schemas**: `src/taskyn/web/backend/schemas/plans.py`
**Registration**: `app.include_router(plans_router, prefix="/api/v1")` in `main.py`

Router follows the established pattern: routes call `call_mcp_tool()` (not core functions directly), depend on `get_current_user` for auth, and use Pydantic request models from `schemas/`.

```python
router = APIRouter(prefix="/plans", tags=["plans"])
```

---

## Pydantic Request/Response Models

`src/taskyn/web/backend/schemas/plans.py`:

```python
class PlanCreate(BaseModel):
    date: date                                          # required
    actor: str = Field(max_length=100)                  # required
    notes: str | None = Field(default=None, max_length=5000)
    items: list[PlanItemInline] | None = None           # optional inline items

class PlanItemInline(BaseModel):
    node_id: str = Field(max_length=64)
    planned_minutes: int | None = Field(default=None, ge=0)
    display_order: int | None = Field(default=None, ge=1)

class PlanUpdate(BaseModel):
    notes: str | None = None
    status: str | None = Field(default=None, max_length=32)  # "active" | "completed"

class PlanItemAdd(BaseModel):
    node_id: str = Field(max_length=64)
    planned_minutes: int | None = Field(default=None, ge=0)
    position: int | None = Field(default=None, ge=1)

class PlanItemUpdate(BaseModel):
    planned_minutes: int | None = None                  # None clears
    outcome: str | None = Field(default=None, max_length=32)  # PlanOutcome value
    outcome_notes: str | None = Field(default=None, max_length=5000)

class PlanItemReorder(BaseModel):
    new_position: int = Field(ge=1)         # 1-based (see Position Indexing note below)

class CarryOverRequest(BaseModel):
    target_date: date                                   # required
    item_ids: list[str] | None = None                   # None = auto-select pending+partial
```

No response models needed — routes return the raw dict/list from `call_mcp_tool()`, matching the existing pattern (nodes, timer, etc. all return `Any`).

---

## Endpoint Definitions (14 endpoints)

### Plan CRUD (6)

| # | Method | Path | Handler | MCP Tool | Args Mapping |
|---|--------|------|---------|----------|--------------|
| 1 | `POST` | `/plans` | `create_plan` | `pm_create_plan` | `body.model_dump(exclude_none=True)` |
| 2 | `GET` | `/plans` | `list_plans` | `pm_list_plans` | query: `actor, date_from, date_to, status, limit, offset` |
| 3 | `GET` | `/plans/by-date` | `get_plan_by_date` | `pm_get_plan` | query: `date` (date, required), `actor` (str, required). Returns Plan or 200 with `null` body if no plan exists. |
| 4 | `GET` | `/plans/{plan_id}` | `get_plan` | `pm_get_plan` | path: `plan_id` |
| 5 | `PATCH` | `/plans/{plan_id}` | `update_plan` | `pm_update_plan` | path: `plan_id`, body: `PlanUpdate` |
| 6 | `DELETE` | `/plans/{plan_id}` | `delete_plan` | `pm_delete_plan` | path: `plan_id` → 204 No Content |

### Plan Items (4)

| # | Method | Path | Handler | MCP Tool | Args Mapping |
|---|--------|------|---------|----------|--------------|
| 7 | `POST` | `/plans/{plan_id}/items` | `add_plan_item` | `pm_add_plan_item` | path: `plan_id`, body: `PlanItemAdd` |
| 8 | `PATCH` | `/plans/items/{item_id}` | `update_plan_item` | `pm_update_plan_item` | path: `item_id`, body: `PlanItemUpdate` |
| 9 | `DELETE` | `/plans/items/{item_id}` | `remove_plan_item` | `pm_remove_plan_item` | path: `item_id` → 204 No Content |
| 10 | `POST` | `/plans/items/{item_id}/reorder` | `reorder_plan_item` | `pm_reorder_plan_item` | path: `item_id`, body: `PlanItemReorder` |

### Horizon Views & Analysis (4)

| # | Method | Path | Handler | MCP Tool | Args Mapping |
|---|--------|------|---------|----------|--------------|
| 11 | `GET` | `/plans/weekly` | `get_weekly_plan` | `pm_get_weekly_plan` | query: `week_start_date` (date, required), `actor` (optional) |
| 12 | `GET` | `/plans/monthly` | `get_monthly_plan` | `pm_get_monthly_plan` | query: `year` (int, required), `month` (int, required), `actor` (optional) |
| 13 | `POST` | `/plans/{plan_id}/carry-over` | `carry_over_plan` | `pm_carry_over_plan` | path: `plan_id`, body: `CarryOverRequest` |
| 14 | `GET` | `/plans/vs-actual` | `get_plan_vs_actual` | `pm_plan_vs_actual` | query: `plan_date` (date, required), `actor` (str, required) |

---

## Route Ordering (critical)

FastAPI matches routes top-to-bottom. Static segments must be registered **before** `{plan_id}` to avoid `"weekly"` / `"monthly"` / `"vs-actual"` being captured as a plan_id.

```
# Register in this order:
GET  /plans/by-date         # static — before {plan_id} (F-01: date+actor lookup)
GET  /plans/weekly          # static — before {plan_id}
GET  /plans/monthly         # static — before {plan_id}
GET  /plans/vs-actual       # static — before {plan_id}
PATCH /plans/items/{item_id}   # static "items" — before {plan_id}
DELETE /plans/items/{item_id}  # static "items" — before {plan_id}
POST /plans/items/{item_id}/reorder  # static "items" — before {plan_id}
GET  /plans                 # list
POST /plans                 # create
GET  /plans/{plan_id}       # get by id
PATCH /plans/{plan_id}      # update
DELETE /plans/{plan_id}     # delete
POST /plans/{plan_id}/items       # add item
POST /plans/{plan_id}/carry-over  # carry over
```

---

## Endpoint Pseudocode

### 1. POST /plans (201)

```python
@router.post("", status_code=201)
async def create_plan(data: PlanCreate, current_user = Depends(get_current_user)):
    args = data.model_dump(exclude_none=True)
    if data.items:
        args["items"] = [i.model_dump(exclude_none=True) for i in data.items]
    return await call_mcp_tool("pm_create_plan", args)
```

### 2. GET /plans

```python
@router.get("")
async def list_plans(
    actor: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    current_user = Depends(get_current_user),
):
    args = {}
    if actor: args["actor"] = actor
    if date_from: args["date_from"] = date_from.isoformat()
    if date_to: args["date_to"] = date_to.isoformat()
    if status: args["status"] = status
    args["limit"] = limit
    args["offset"] = offset
    return await call_mcp_tool("pm_list_plans", args)
```

### 3. GET /plans/by-date (F-01)

Primary day-view fetch. Returns the plan for a specific date+actor, or `null` if no plan exists (200 with null body — **not** 404, so the frontend can distinguish "no plan" from "request failed").

```python
@router.get("/by-date")
async def get_plan_by_date(
    date: date,
    actor: str,
    current_user = Depends(get_current_user),
):
    result = await call_mcp_tool("pm_get_plan", {
        "plan_date": date.isoformat(), "actor": actor
    })
    return result  # dict (Plan + items) or None — both return 200
```

### 4. GET /plans/{plan_id}

```python
@router.get("/{plan_id}")
async def get_plan(
    plan_id: str,
    current_user = Depends(get_current_user),
):
    return await call_mcp_tool("pm_get_plan", {"plan_id": plan_id})
```

### 5. PATCH /plans/{plan_id}

```python
@router.patch("/{plan_id}")
async def update_plan(plan_id: str, data: PlanUpdate, current_user = ...):
    args = {"plan_id": plan_id, **data.model_dump(exclude_unset=True)}
    return await call_mcp_tool("pm_update_plan", args)
```

### 6. DELETE /plans/{plan_id} (204)

```python
@router.delete("/{plan_id}", status_code=204)
async def delete_plan(plan_id: str, current_user = ...):
    await call_mcp_tool("pm_delete_plan", {"plan_id": plan_id})
    return Response(status_code=204)
```

### 7. POST /plans/{plan_id}/items (201)

```python
@router.post("/{plan_id}/items", status_code=201)
async def add_plan_item(plan_id: str, data: PlanItemAdd, current_user = ...):
    args = {"plan_id": plan_id, **data.model_dump(exclude_none=True)}
    return await call_mcp_tool("pm_add_plan_item", args)
```

### 8. PATCH /plans/items/{item_id}

```python
@router.patch("/items/{item_id}")
async def update_plan_item(item_id: str, data: PlanItemUpdate, current_user = ...):
    args = {"item_id": item_id, **data.model_dump(exclude_unset=True)}
    return await call_mcp_tool("pm_update_plan_item", args)
```

### 9. DELETE /plans/items/{item_id} (204)

```python
@router.delete("/items/{item_id}", status_code=204)
async def remove_plan_item(item_id: str, current_user = ...):
    await call_mcp_tool("pm_remove_plan_item", {"item_id": item_id})
    return Response(status_code=204)
```

### 10. POST /plans/items/{item_id}/reorder

```python
@router.post("/items/{item_id}/reorder")
async def reorder_plan_item(item_id: str, data: PlanItemReorder, current_user = ...):
    return await call_mcp_tool("pm_reorder_plan_item", {
        "item_id": item_id, "new_position": data.new_position
    })
```

### 11. GET /plans/weekly

```python
@router.get("/weekly")
async def get_weekly_plan(
    week_start_date: date,
    actor: str | None = None,
    current_user = ...,
):
    args = {"week_start_date": week_start_date.isoformat()}
    if actor: args["actor"] = actor
    return await call_mcp_tool("pm_get_weekly_plan", args)
```

### 12. GET /plans/monthly

```python
@router.get("/monthly")
async def get_monthly_plan(
    year: int, month: int,
    actor: str | None = None,
    current_user = ...,
):
    args = {"year": year, "month": month}
    if actor: args["actor"] = actor
    return await call_mcp_tool("pm_get_monthly_plan", args)
```

### 13. POST /plans/{plan_id}/carry-over

```python
@router.post("/{plan_id}/carry-over")
async def carry_over_plan(plan_id: str, data: CarryOverRequest, current_user = ...):
    args = {"source_plan_id": plan_id, "target_date": data.target_date.isoformat()}
    if data.item_ids: args["item_ids"] = data.item_ids
    return await call_mcp_tool("pm_carry_over_plan", args)
```

### 14. GET /plans/vs-actual

```python
@router.get("/vs-actual")
async def get_plan_vs_actual(
    plan_date: date, actor: str,
    current_user = ...,
):
    return await call_mcp_tool("pm_plan_vs_actual", {
        "plan_date": plan_date.isoformat(), "actor": actor
    })
```

---

## Error Handling

Follows the existing pattern — **no try/except in routes**. `call_mcp_tool()` in `deps.py` maps MCP error responses to HTTP exceptions:

| MCP Error Pattern | HTTP Status |
|-------------------|-------------|
| `"not found"` | 404 |
| `"already exists"`, `"cycle"` | 409 |
| `"validation"`, `"invalid"` | 422 |
| Connection / timeout | 503 / 504 |
| Unknown | 500 |

Pydantic validation failures (invalid body) automatically return **422** via FastAPI.

---

## Registration in main.py

```python
from .routes.plans import router as plans_router
# ...
app.include_router(plans_router, prefix="/api/v1")
```

---

## MCP Tool → Core Function Mapping (reference)

| MCP Tool | Core Function | Returns |
|----------|--------------|---------|
| `pm_create_plan` | `planning.create_plan(plan_date, actor, notes, items)` | dict (plan + items) |
| `pm_get_plan` | `planning.get_plan(plan_id, plan_date, actor)` | dict \| None |
| `pm_update_plan` | `planning.update_plan(plan_id, notes, status, actor)` | dict |
| `pm_delete_plan` | `planning.delete_plan(plan_id, actor)` | bool |
| `pm_list_plans` | `planning.list_plans(actor, date_from, date_to, status, limit, offset)` | list[Plan] |
| `pm_add_plan_item` | `planning.add_plan_item(plan_id, node_id, planned_minutes, position, actor)` | PlanItem |
| `pm_remove_plan_item` | `planning.remove_plan_item(item_id, actor)` | bool |
| `pm_reorder_plan_item` | `planning.reorder_plan_item(item_id, new_position, actor)` | PlanItem |
| `pm_update_plan_item` | `planning.update_plan_item(item_id, planned_minutes, outcome, outcome_notes, actor)` | PlanItem |
| `pm_get_weekly_plan` | `planning.get_weekly_plan(week_start_date, actor)` | dict |
| `pm_get_monthly_plan` | `planning.get_monthly_plan(year, month, actor)` | dict |
| `pm_plan_vs_actual` | `planning.plan_vs_actual(plan_date, actor)` | dict |
| `pm_carry_over_plan` | `planning.carry_over_plan(source_plan_id, target_date, item_ids, actor)` | dict |

---

## Position Indexing Convention (F-05)

All positions are **1-based**. The first item in a plan has `display_order: 1`.

- `PlanItemInline.display_order`: `ge=1`
- `PlanItemAdd.position`: `ge=1`
- `PlanItemReorder.new_position`: `ge=1`

The frontend must convert 0-based array indices to 1-based before sending: `newPosition = arrayIndex + 1`. Optimistic cache updates should also store `display_order` as 1-based values.

---

## Plannable Node Filtering (F-04)

The `NodePickerModal` (US-7) needs to show only node types that are plannable (where the methodology's `NodeTypeDefinition.can_be_planned === True`).

**Approach: client-side filtering.** The plans API does not add a `plannable` filter to the nodes endpoint (avoids cross-cutting changes to the nodes subsystem). Instead:
1. The frontend calls `GET /api/v1/projects/{project_id}/methodology` to get the methodology info, which includes `node_types` with each type's `can_be_planned` flag.
2. `NodePickerModal` fetches nodes with `useNodes({ status: ['backlog', 'ready', 'in_progress'] })` and filters out node types where `can_be_planned === false` using the methodology data.
3. If a future upstream change adds `plannable` as a query param to `GET /api/v1/nodes`, the frontend can switch to server-side filtering.

---

## Date serialization note

MCP tools receive all dates as ISO strings (`date.isoformat()`). The core layer parses them back. Routes must call `.isoformat()` on any `date` query/body params before passing to `call_mcp_tool()`.

---

# Part 2 — Frontend Component Architecture

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

---

# Part 3 — Frontend Data Layer

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

---

# Design Review Notes

Two design dry-runs were conducted before this design was finalized. The section files already incorporate all fixes. This summary tracks what was found and resolved.

## Dryrun #1 — Findings and Resolutions

Dryrun #1 (`dryrun-design-1.md`) identified 8 findings and 5 missing paths. All critical blockers were fixed in the design documents before dryrun #2.

### MUST FIX (all resolved)

| # | Finding | Resolution |
|---|---------|------------|
| F-01 | No REST endpoint for date+actor plan lookup — day view could not fetch data | Added `GET /plans/by-date` endpoint (backend endpoint #3). Updated `plansApi.getByDate` to call the new path. Defined 200-with-null contract for missing plans (also resolves R-04). |
| F-02 | `MonthlyPlan` type missing per-day data — month calendar grid could not render | Added `days: MonthlyDaySummary[]` to `MonthlyPlan` with per-day breakdown (date, plan_id, status, outcomes, minutes). |
| F-03 | Plan-vs-actual query param name mismatch (`date` vs `plan_date`) — would 422 on every request | Updated `plansApi.vsActual` to send `plan_date` matching the backend route definition. |
| F-04 | Plannable filter doesn't exist in nodes API — node picker could not filter to valid types | Adopted client-side filtering: `NodePickerModal` fetches methodology info per project and excludes non-plannable types. No upstream changes needed (also eliminates R-01 risk). |

### SHOULD FIX (all resolved)

| # | Finding | Resolution |
|---|---------|------------|
| F-05 | Position indexing 0-based vs 1-based — would cause DnD validation errors | Documented 1-based convention in backend. Frontend DnD sends `targetIndex + 1`. Optimistic update stores `display_order: idx + 1`. |
| F-06 | `display_order` vs `position` field name mismatch on inline items | Aligned `PlanItemSeed.display_order` to match backend `PlanItemInline.display_order`. |
| F-08 | `WeeklyPlan.days` typed as `Plan[][]` — wrong shape for summary cards | Changed to `WeeklyDaySummary[]` with 7 entries (Mon–Sun), each containing count/status/outcomes/minutes. |

### MINOR (accepted as-is)

| # | Finding | Status |
|---|---------|--------|
| F-07 | Frontend DnD example uses `planKeys.detail(date, actor)` instead of `queryKeys.plans.byDate(date, actor)` | Cosmetic — the authoritative mutation code in the data layer uses the correct key. Fix inline during implementation. |

### Missing Paths (all addressed)

| # | Item | Resolution |
|---|------|------------|
| M-01 | No live update mechanism when Velasari modifies plans | Added configurable `refetchInterval` option to `usePlan` hook. Implementor sets a sensible default in DayView. |
| M-02 | Empty state for fully empty week/month | Acknowledged as low-impact polish. Views render correctly with zero values. |
| M-03 | Carry-over of deleted-node items | CarryOverModal now shows deleted-node items with warning icon + "(deleted)" label, unchecked by default. |
| M-04 | No confirmation before plan deletion | Added conditional confirmation dialogs in section 12b — detailed warning for plans with recorded outcomes. |
| M-05 | 409 on create should auto-refresh | Added 409 handler in `useCreatePlan` onError: invalidates plan query so existing plan loads automatically. |

## Dryrun #2 — Final Verification

Dryrun #2 (`dryrun-design-2.md`) verified all dryrun-1 fixes and found two minor new items:

| # | Finding | Severity | Status |
|---|---------|----------|--------|
| N-01 | Optimistic splice off-by-one: `newPosition` is 1-based but used as 0-based splice index | SHOULD FIX | Fix inline during implementation: `splice(newPosition - 1, ...)` |
| N-02 | Multi-project methodology loading in NodePickerModal unspecified | MINOR | Implementor decides: fetch lazily per project filter selection |

### Carried-Forward Accepted Trade-offs

| # | Item | Notes |
|---|------|-------|
| R-02 | Broad `plans.all()` invalidation on every mutation | Acceptable for v1 single-user. Targeted invalidation is a future optimization. |
| R-03 | HTML5 DnD doesn't work on touch devices | Out of scope per requirements ("no dedicated mobile design"). Consistent with KanbanPage. |

**Verdict from dryrun #2: PASS WITH WARNINGS.** The design is ready for task planning and implementation.
