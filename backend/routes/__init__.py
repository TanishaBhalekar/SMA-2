"""
API Route Handlers for PRJ-07.
"""
from fastapi import APIRouter
from backend.routes.health import router as health_router
from backend.routes.entities import router as entities_router, get_entity_repository_stats
from backend.routes.resolution import router as resolution_router
from backend.routes.sources import router as sources_router
from backend.routes.workspaces import router as workspaces_router

api_router = APIRouter()
api_router.include_router(health_router, prefix="", tags=["Health"])
api_router.include_router(workspaces_router, prefix="/workspaces", tags=["Workspaces"])
api_router.include_router(sources_router, prefix="/sources", tags=["Sources"])
api_router.include_router(entities_router, prefix="/entities", tags=["Entities"])
api_router.include_router(resolution_router, prefix="/resolution", tags=["Resolution"])
api_router.add_api_route("/stats", get_entity_repository_stats, methods=["GET"], tags=["Stats"])



