"""Company routes — CRUD + stats."""

from fastapi import APIRouter, Response

from ..deps import call_mcp_tool
from ..schemas.companies import CompanyCreate, CompanyUpdate

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("")
async def list_companies(include_stats: bool = False):
    """List all companies."""
    return await call_mcp_tool("pm_list_companies", {"include_stats": include_stats})


@router.get("/{company_id}")
async def get_company(company_id: str):
    """Get a company by ID."""
    return await call_mcp_tool("pm_get_company", {"company_id": company_id})


@router.post("", status_code=201)
async def create_company(data: CompanyCreate):
    """Create a new company."""
    args = data.model_dump(exclude_none=True)
    if "type" in args:
        args["type"] = args["type"].value
    return await call_mcp_tool("pm_create_company", args)


@router.patch("/{company_id}")
async def update_company(company_id: str, data: CompanyUpdate):
    """Update a company."""
    args = {"company_id": company_id, **data.model_dump(exclude_unset=True)}
    if "type" in args and args["type"] is not None:
        args["type"] = args["type"].value
    return await call_mcp_tool("pm_update_company", args)


@router.delete("/{company_id}", status_code=204)
async def delete_company(company_id: str):
    """Delete a company."""
    await call_mcp_tool("pm_delete_company", {"company_id": company_id})
    return Response(status_code=204)


@router.get("/{company_id}/stats")
async def get_company_stats(company_id: str):
    """Get aggregated stats for a company."""
    return await call_mcp_tool("pm_get_company_stats", {"company_id": company_id})
