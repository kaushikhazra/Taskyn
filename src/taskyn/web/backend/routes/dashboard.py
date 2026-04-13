"""Dashboard route — aggregated stats."""

from fastapi import APIRouter

from ..deps import call_mcp_tool

router = APIRouter(tags=["reporting"])


@router.get("/dashboard")
async def get_dashboard():
    """Get dashboard aggregates."""
    return await call_mcp_tool("pm_get_dashboard", {})
