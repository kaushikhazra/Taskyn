"""Edge routes — CRUD."""

from fastapi import APIRouter, Response

from ..deps import call_mcp_tool
from ..schemas.edges import EdgeCreate

router = APIRouter(prefix="/edges", tags=["edges"])


@router.get("")
async def list_edges(
    project_id: str | None = None,
    source_id: str | None = None,
    target_id: str | None = None,
    edge_type: str | None = None,
):
    """List edges with optional filters."""
    args = {}
    if project_id:
        args["project_id"] = project_id
    if source_id:
        args["source_id"] = source_id
    if target_id:
        args["target_id"] = target_id
    if edge_type:
        args["edge_type"] = edge_type
    return await call_mcp_tool("pm_list_edges", args)


@router.post("", status_code=201)
async def create_edge(data: EdgeCreate):
    """Create a new edge."""
    return await call_mcp_tool("pm_create_edge", data.model_dump())


@router.delete("/{edge_id}", status_code=204)
async def delete_edge(edge_id: str):
    """Delete an edge."""
    await call_mcp_tool("pm_delete_edge", {"edge_id": edge_id})
    return Response(status_code=204)
