"""Project routes — CRUD + methodology + stats."""

from fastapi import APIRouter, Response

from ..deps import call_mcp_tool
from ..schemas.projects import ProjectCreate, ProjectUpdate

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("")
async def list_projects(
    company_id: str | None = None,
    status: str | None = None,
    include_stats: bool = False,
):
    """List projects with optional filters."""
    args = {"include_stats": include_stats}
    if company_id:
        args["company_id"] = company_id
    if status:
        args["status"] = status
    return await call_mcp_tool("pm_list_projects", args)


@router.get("/{project_id}")
async def get_project(project_id: str):
    """Get a project by ID."""
    return await call_mcp_tool("pm_get_project", {"project_id": project_id})


@router.post("", status_code=201)
async def create_project(data: ProjectCreate):
    """Create a new project."""
    args = data.model_dump(exclude_none=True)
    if "type" in args:
        args["type"] = args["type"].value
    return await call_mcp_tool("pm_create_project", args)


@router.patch("/{project_id}")
async def update_project(project_id: str, data: ProjectUpdate):
    """Update a project."""
    args = {"project_id": project_id, **data.model_dump(exclude_unset=True)}
    if "type" in args and args["type"] is not None:
        args["type"] = args["type"].value
    if "methodology" in args and args["methodology"] is not None:
        args["methodology"] = args["methodology"].value
    return await call_mcp_tool("pm_update_project", args)


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: str):
    """Delete a project."""
    await call_mcp_tool("pm_delete_project", {"project_id": project_id})
    return Response(status_code=204)


@router.get("/{project_id}/methodology")
async def get_methodology(project_id: str):
    """Get methodology info for a project."""
    return await call_mcp_tool("pm_get_methodology_info", {"project_id": project_id})


@router.get("/{project_id}/stats")
async def get_project_stats(project_id: str):
    """Get project stats."""
    return await call_mcp_tool("pm_get_project_stats", {"project_id": project_id})
