"""Node routes — CRUD, transitions, traversal, tags."""

from fastapi import APIRouter, Response

from ..deps import call_mcp_tool
from ..schemas.nodes import BlockRequest, NodeCreate, NodeUpdate, TagRequest

router = APIRouter(prefix="/nodes", tags=["nodes"])


@router.get("")
async def list_nodes(
    project_id: str | None = None,
    node_type: str | None = None,
    status: str | None = None,
    assignee: str | None = None,
):
    """List nodes with optional filters."""
    args = {}
    if project_id:
        args["project_id"] = project_id
    if node_type:
        args["node_type"] = node_type
    if status:
        args["status"] = status
    if assignee:
        args["assignee"] = assignee
    return await call_mcp_tool("pm_list_nodes", args)


@router.get("/{node_id}")
async def get_node(node_id: str):
    """Get a node by ID (includes edges, time entries, rollup)."""
    return await call_mcp_tool("pm_get_node", {"node_id": node_id})


@router.post("", status_code=201)
async def create_node(data: NodeCreate):
    """Create a new node."""
    return await call_mcp_tool("pm_create_node", data.model_dump(exclude_none=True))


@router.patch("/{node_id}")
async def update_node(node_id: str, data: NodeUpdate):
    """Update a node."""
    args = {"node_id": node_id, **data.model_dump(exclude_unset=True)}
    return await call_mcp_tool("pm_update_node", args)


@router.delete("/{node_id}", status_code=204)
async def delete_node(node_id: str):
    """Delete a node."""
    await call_mcp_tool("pm_delete_node", {"node_id": node_id})
    return Response(status_code=204)


# --- Status transitions ---


@router.post("/{node_id}/start")
async def start_node(node_id: str):
    """Transition node to in_progress."""
    return await call_mcp_tool("pm_start_node", {"node_id": node_id})


@router.post("/{node_id}/complete")
async def complete_node(node_id: str):
    """Transition node to done."""
    return await call_mcp_tool("pm_complete_node", {"node_id": node_id})


@router.post("/{node_id}/block")
async def block_node(node_id: str, data: BlockRequest):
    """Mark node as blocked."""
    return await call_mcp_tool("pm_block_node", {"node_id": node_id, "reason": data.reason})


# --- Traversal ---


@router.get("/{node_id}/ancestors")
async def get_ancestors(node_id: str, edge_type: str | None = None):
    """Get ancestor chain for a node."""
    args = {"node_id": node_id}
    if edge_type:
        args["edge_type"] = edge_type
    return await call_mcp_tool("pm_get_ancestors", args)


@router.get("/{node_id}/descendants")
async def get_descendants(node_id: str, edge_type: str | None = None):
    """Get descendant tree for a node."""
    args = {"node_id": node_id}
    if edge_type:
        args["edge_type"] = edge_type
    return await call_mcp_tool("pm_get_descendants", args)


@router.get("/{node_id}/rollup")
async def get_rollup(node_id: str):
    """Get aggregated rollup stats for a node."""
    return await call_mcp_tool("pm_get_rollup", {"node_id": node_id})


# --- Tags ---


@router.post("/{node_id}/tags")
async def tag_node(node_id: str, data: TagRequest):
    """Tag a node."""
    return await call_mcp_tool("pm_tag_node", {"node_id": node_id, "tag_name": data.tag_name})


@router.delete("/{node_id}/tags/{tag_name}")
async def untag_node(node_id: str, tag_name: str):
    """Remove a tag from a node."""
    return await call_mcp_tool("pm_untag_node", {"node_id": node_id, "tag_name": tag_name})
