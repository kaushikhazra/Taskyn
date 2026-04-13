# Backend Design — Plans REST API (US-14)

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
