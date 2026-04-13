"""Timer routes — start, stop, current."""

from fastapi import APIRouter

from ..deps import call_mcp_tool
from ..schemas.timer import TimerStart, TimerStop

router = APIRouter(prefix="/timer", tags=["timer"])


@router.post("/start")
async def start_timer(data: TimerStart):
    """Start a timer on a node."""
    return await call_mcp_tool("pm_start_timer", data.model_dump(exclude_none=True))


@router.post("/stop")
async def stop_timer(data: TimerStop = TimerStop()):
    """Stop the active timer (or a specific timer by entry_id)."""
    return await call_mcp_tool("pm_stop_timer", data.model_dump(exclude_none=True))


@router.get("/current")
async def get_active_timer():
    """Get the currently active timer for this actor."""
    return await call_mcp_tool("pm_get_active_timer", {})


@router.get("/active")
async def get_active_timers():
    """Get all active timers across all actors."""
    return await call_mcp_tool("pm_get_active_timers", {})
