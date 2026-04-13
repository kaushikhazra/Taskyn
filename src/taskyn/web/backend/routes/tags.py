"""Tag routes — list and create."""

from fastapi import APIRouter

from ..deps import call_mcp_tool
from ..schemas.tags import TagCreate

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("")
async def list_tags():
    """List all tags."""
    return await call_mcp_tool("pm_list_tags", {})


@router.post("", status_code=201)
async def create_tag(data: TagCreate):
    """Create a new tag."""
    return await call_mcp_tool("pm_create_tag", data.model_dump(exclude_none=True))


@router.get("/{tag_name}/usage")
async def get_tag_usage(tag_name: str):
    """Get usage count for a tag."""
    return await call_mcp_tool("pm_get_tag_usage", {"tag_name": tag_name})


@router.delete("/{tag_name}", status_code=200)
async def delete_tag(tag_name: str):
    """Delete a tag. Returns info about how many nodes had this tag."""
    return await call_mcp_tool("pm_delete_tag", {"tag_name": tag_name})
