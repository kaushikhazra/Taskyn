"""FastAPI application — thin REST bridge to MCP tools via FastMCP Client."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from .deps import close_mcp_client, get_mcp_client, init_mcp_client
from .routes.activity import router as activity_router
from .routes.companies import router as companies_router
from .routes.health import router as health_router
from .routes.dashboard import router as dashboard_router
from .routes.edges import router as edges_router
from .routes.milestones import router as milestones_router
from .routes.nodes import router as nodes_router
from .routes.plans import router as plans_router
from .routes.projects import router as projects_router
from .routes.search import router as search_router
from .routes.tags import router as tags_router
from .routes.time_entries import router as time_entries_router
from .routes.timer import router as timer_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle — MCP client connection."""
    await init_mcp_client()
    yield
    await close_mcp_client()


app = FastAPI(
    title="Taskyn API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    redirect_slashes=False,
    lifespan=lifespan,
)

# CORS — configurable origins via env var
_cors_origins = os.getenv("TASKYN_CORS_ORIGINS", "http://localhost:3020").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type"],
)

# Health check at root level for load balancers
app.include_router(health_router)

# Register routers under /api/v1
app.include_router(companies_router, prefix="/api/v1")
app.include_router(projects_router, prefix="/api/v1")
app.include_router(nodes_router, prefix="/api/v1")
app.include_router(plans_router, prefix="/api/v1")
app.include_router(edges_router, prefix="/api/v1")
app.include_router(milestones_router, prefix="/api/v1")
app.include_router(tags_router, prefix="/api/v1")
app.include_router(timer_router, prefix="/api/v1")
app.include_router(time_entries_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(activity_router, prefix="/api/v1")
app.include_router(search_router, prefix="/api/v1")

# Serve frontend static files
_frontend_dir = Path(__file__).parent.parent / "frontend" / "dist"

if _frontend_dir.exists():
    # Serve static assets (JS, CSS, etc.)
    app.mount("/assets", StaticFiles(directory=_frontend_dir / "assets"), name="assets")

    # Read index.html once at startup for SPA routing
    _index_html = (_frontend_dir / "index.html").read_text()

    # Serve index.html for all other routes (SPA routing)
    @app.get("/{path:path}")
    async def serve_spa(path: str):
        """Serve the SPA index.html for client-side routing."""
        return HTMLResponse(
            content=_index_html,
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
        )
