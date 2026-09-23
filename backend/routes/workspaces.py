"""
API Route Handlers for Workspaces & Ingestion Sessions (PRJ-07).
Provides creation, listing with aggregated telemetry, retrieval, renaming, and cascading deletion.
"""

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.database import get_db
from backend.models import (
    Workspace,
    Source,
    AttributeIndex,
    MasterEntity,
    EnrichmentHop,
    EntityAttribute
)
from backend.schemas import (
    WorkspaceCreate,
    WorkspaceUpdate,
    WorkspaceResponse,
    WorkspaceDetailResponse,
    SourceResponse
)

router = APIRouter()


def _get_workspace_stats(db: Session, workspace_id: str) -> dict:
    """Helper to aggregate stats for a specific workspace."""
    total_sources = db.query(Source).filter_by(workspace_id=workspace_id).count()
    total_records = db.query(
        func.coalesce(func.sum(Source.record_count), 0)
    ).filter(Source.workspace_id == workspace_id).scalar() or 0
    total_attributes = db.query(AttributeIndex).filter_by(workspace_id=workspace_id).count()
    master_entities = db.query(MasterEntity).filter_by(workspace_id=workspace_id).count()

    if total_attributes > 0 and master_entities == 0:
        from backend.services.enrichment_engine import resolve_workspace_entities
        resolve_workspace_entities(workspace_id=workspace_id, db=db)
        master_entities = db.query(MasterEntity).filter_by(workspace_id=workspace_id).count()

    # Query hops for master entities belonging to this workspace
    links_discovered = db.query(EnrichmentHop).join(
        MasterEntity, EnrichmentHop.entity_id == MasterEntity.id
    ).filter(MasterEntity.workspace_id == workspace_id).count()

    return {
        "total_sources": total_sources,
        "total_records": int(total_records),
        "total_attributes_indexed": total_attributes,
        "master_entities": master_entities,
        "links_discovered": links_discovered,
        "multi_hop_links": links_discovered,
    }


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
def create_workspace(
    req: WorkspaceCreate,
    db: Session = Depends(get_db)
):
    """
    Creates a new dynamic ingestion workspace / session.
    Defaults name to 'Session - <Current Date/Time>' if omitted.
    """
    now_utc = datetime.now(timezone.utc)
    now_local_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    session_name = req.name.strip() if (req.name and req.name.strip()) else f"Session - {now_local_str}"

    ws_id = f"ws-{uuid.uuid4().hex[:8]}"

    workspace = Workspace(
        id=ws_id,
        name=session_name,
        description=req.description,
        created_at=now_utc,
        updated_at=now_utc
    )
    db.add(workspace)
    db.commit()
    db.refresh(workspace)

    return WorkspaceResponse(
        id=workspace.id,
        name=workspace.name,
        description=workspace.description,
        created_at=workspace.created_at,
        updated_at=workspace.updated_at,
        total_sources=0,
        total_records=0,
        total_attributes_indexed=0,
        master_entities=0,
        links_discovered=0
    )


@router.get("", response_model=List[WorkspaceResponse])
def list_workspaces(
    db: Session = Depends(get_db)
):
    """
    Lists all saved past sessions along with aggregated statistics
    (total sources count, total records ingested, discovered entities, etc.).
    """
    workspaces = db.query(Workspace).order_by(Workspace.created_at.desc()).all()
    results = []

    for ws in workspaces:
        stats = _get_workspace_stats(db, ws.id)
        results.append(
            WorkspaceResponse(
                id=ws.id,
                name=ws.name,
                description=ws.description,
                created_at=ws.created_at,
                updated_at=ws.updated_at,
                total_sources=stats["total_sources"],
                total_records=stats["total_records"],
                total_attributes_indexed=stats["total_attributes_indexed"],
                master_entities=stats["master_entities"],
                links_discovered=stats["links_discovered"]
            )
        )

    return results


@router.get("/{workspace_id}", response_model=WorkspaceDetailResponse)
def get_workspace(
    workspace_id: str,
    db: Session = Depends(get_db)
):
    """
    Retrieves workspace metadata, its uploaded sources, and isolated telemetry.
    """
    workspace = db.query(Workspace).filter_by(id=workspace_id).first()
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace with id='{workspace_id}' not found."
        )

    sources = db.query(Source).filter_by(workspace_id=workspace_id).order_by(Source.created_at.asc()).all()
    stats = _get_workspace_stats(db, workspace_id)

    return WorkspaceDetailResponse(
        id=workspace.id,
        name=workspace.name,
        description=workspace.description,
        created_at=workspace.created_at,
        updated_at=workspace.updated_at,
        sources=[SourceResponse.model_validate(s) for s in sources],
        stats=stats
    )


@router.get("/{workspace_id}/stats")
def get_workspace_stats_endpoint(
    workspace_id: str,
    db: Session = Depends(get_db)
):
    """
    Returns isolated telemetry for the specified workspace session:
    master entities discovered, cross-silo links formed, indexed records, and attributes.
    """
    workspace = db.query(Workspace).filter_by(id=workspace_id).first()
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace with id='{workspace_id}' not found."
        )

    return _get_workspace_stats(db, workspace_id)


@router.post("/{workspace_id}/resolve")
def run_workspace_resolution(
    workspace_id: str,
    db: Session = Depends(get_db)
):
    """
    Executes a session-wide connected component graph resolution pass over all
    indexed records in this workspace, discovering disjoint identity clusters
    and persisting master entities, attributes, and discovery hops.
    """
    workspace = db.query(Workspace).filter_by(id=workspace_id).first()
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace with id='{workspace_id}' not found."
        )

    from backend.services.enrichment_engine import resolve_workspace_entities
    res = resolve_workspace_entities(workspace_id=workspace_id, db=db)
    stats = _get_workspace_stats(db, workspace_id)

    return {
        "status": "success",
        "workspace_id": workspace_id,
        "resolution": res,
        "stats": stats
    }


@router.patch("/{workspace_id}", response_model=WorkspaceResponse)
def update_workspace(
    workspace_id: str,
    req: WorkspaceUpdate,
    db: Session = Depends(get_db)
):
    """
    Renames or updates the description of a workspace session.
    """
    workspace = db.query(Workspace).filter_by(id=workspace_id).first()
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace with id='{workspace_id}' not found."
        )

    if req.name is not None and req.name.strip():
        workspace.name = req.name.strip()
    if req.description is not None:
        workspace.description = req.description.strip()

    workspace.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(workspace)

    stats = _get_workspace_stats(db, workspace_id)

    return WorkspaceResponse(
        id=workspace.id,
        name=workspace.name,
        description=workspace.description,
        created_at=workspace.created_at,
        updated_at=workspace.updated_at,
        total_sources=stats["total_sources"],
        total_records=stats["total_records"],
        total_attributes_indexed=stats["total_attributes_indexed"],
        master_entities=stats["master_entities"],
        links_discovered=stats["links_discovered"]
    )


@router.delete("/{workspace_id}", status_code=status.HTTP_200_OK)
def delete_workspace(
    workspace_id: str,
    db: Session = Depends(get_db)
):
    """
    Cascade-deletes a workspace, its uploaded files, and all associated EAV and entity records.
    """
    workspace = db.query(Workspace).filter_by(id=workspace_id).first()
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace with id='{workspace_id}' not found."
        )

    # 1. Unlink/delete any physical files from uploads/
    sources = db.query(Source).filter_by(workspace_id=workspace_id).all()
    for s in sources:
        try:
            if s.file_path and os.path.exists(s.file_path):
                os.remove(s.file_path)
        except Exception:
            pass

    # 2. Delete workspace (cascades via SQLAlchemy / SQLite FK)
    db.delete(workspace)
    db.commit()

    return {
        "status": "deleted",
        "id": workspace_id,
        "message": f"Workspace '{workspace.name}' and all associated sources and indices removed."
    }
