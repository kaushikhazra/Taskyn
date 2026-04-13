"""Plan routes — CRUD, items, horizon views, carry-over, vs-actual."""

from datetime import date

from fastapi import APIRouter, Response

from ..deps import call_mcp_tool
from ..schemas.plans import (
    CarryOverRequest,
    PlanCreate,
    PlanItemAdd,
    PlanItemReorder,
    PlanItemUpdate,
    PlanUpdate,
)

router = APIRouter(prefix="/plans", tags=["plans"])


# --- Static-segment routes (before {plan_id} to avoid capture) ---


@router.get("/by-date")
async def get_plan_by_date(date: date, actor: str):
    """Get plan for a specific date+actor. Returns null if no plan exists."""
    return await call_mcp_tool("pm_get_plan", {
        "plan_date": date.isoformat(), "actor": actor
    })


@router.get("/for-date")
async def get_plans_for_date(date: date):
    """Get all actors' plans for a date, each enriched with items. Returns Plan[]."""
    plans_raw = await call_mcp_tool("pm_list_plans", {
        "date_from": date.isoformat(), "date_to": date.isoformat()
    })
    if not plans_raw:
        return []
    enriched = []
    for plan in plans_raw:
        full_plan = await call_mcp_tool("pm_get_plan", {"plan_id": plan["id"]})
        if full_plan:
            enriched.append(full_plan)
    return enriched


@router.get("/weekly")
async def get_weekly_plan(week_start_date: date, actor: str | None = None):
    """Get weekly plan summary."""
    args = {"week_start_date": week_start_date.isoformat()}
    if actor:
        args["actor"] = actor
    return await call_mcp_tool("pm_get_weekly_plan", args)


@router.get("/monthly")
async def get_monthly_plan(year: int, month: int, actor: str | None = None):
    """Get monthly plan summary."""
    args = {"year": year, "month": month}
    if actor:
        args["actor"] = actor
    return await call_mcp_tool("pm_get_monthly_plan", args)


@router.get("/vs-actual")
async def get_plan_vs_actual(plan_date: date, actor: str):
    """Get plan vs actual comparison for a date."""
    return await call_mcp_tool("pm_plan_vs_actual", {
        "plan_date": plan_date.isoformat(), "actor": actor
    })


# --- Item routes (static "items" segment before {plan_id}) ---


@router.patch("/items/{item_id}")
async def update_plan_item(item_id: str, data: PlanItemUpdate):
    """Update a plan item (outcome, notes, planned minutes)."""
    args = {"item_id": item_id, **data.model_dump(exclude_unset=True)}
    return await call_mcp_tool("pm_update_plan_item", args)


@router.delete("/items/{item_id}", status_code=204)
async def remove_plan_item(item_id: str):
    """Remove an item from a plan."""
    await call_mcp_tool("pm_remove_plan_item", {"item_id": item_id})
    return Response(status_code=204)


@router.post("/items/{item_id}/reorder")
async def reorder_plan_item(item_id: str, data: PlanItemReorder):
    """Reorder a plan item to a new 1-based position."""
    return await call_mcp_tool("pm_reorder_plan_item", {
        "item_id": item_id, "new_position": data.new_position
    })


# --- Plan CRUD ---


@router.get("")
async def list_plans(
    actor: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
    """List plans with optional filters."""
    args = {}
    if actor:
        args["actor"] = actor
    if date_from:
        args["date_from"] = date_from.isoformat()
    if date_to:
        args["date_to"] = date_to.isoformat()
    if status:
        args["status"] = status
    args["limit"] = limit
    args["offset"] = offset
    return await call_mcp_tool("pm_list_plans", args)


@router.post("", status_code=201)
async def create_plan(data: PlanCreate):
    """Create a new plan."""
    args = data.model_dump(exclude_none=True)
    # MCP tool uses "plan_date", schema uses "date" — rename
    if "date" in args:
        d = args.pop("date")
        args["plan_date"] = d.isoformat() if hasattr(d, "isoformat") else d
    if data.items:
        args["items"] = [i.model_dump(exclude_none=True) for i in data.items]
    return await call_mcp_tool("pm_create_plan", args)


@router.get("/{plan_id}")
async def get_plan(plan_id: str):
    """Get a plan by ID."""
    return await call_mcp_tool("pm_get_plan", {"plan_id": plan_id})


@router.patch("/{plan_id}")
async def update_plan(plan_id: str, data: PlanUpdate):
    """Update a plan."""
    args = {"plan_id": plan_id, **data.model_dump(exclude_unset=True)}
    return await call_mcp_tool("pm_update_plan", args)


@router.delete("/{plan_id}", status_code=204)
async def delete_plan(plan_id: str):
    """Delete a plan."""
    await call_mcp_tool("pm_delete_plan", {"plan_id": plan_id})
    return Response(status_code=204)


# --- Plan item addition and carry-over (under {plan_id}) ---


@router.post("/{plan_id}/items", status_code=201)
async def add_plan_item(plan_id: str, data: PlanItemAdd):
    """Add an item to a plan."""
    args = {"plan_id": plan_id, **data.model_dump(exclude_none=True)}
    return await call_mcp_tool("pm_add_plan_item", args)


@router.post("/{plan_id}/carry-over")
async def carry_over_plan(plan_id: str, data: CarryOverRequest):
    """Carry over pending/partial items to another date."""
    args = {"source_plan_id": plan_id, "target_date": data.target_date.isoformat()}
    if data.item_ids:
        args["item_ids"] = data.item_ids
    return await call_mcp_tool("pm_carry_over_plan", args)
