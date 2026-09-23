"""
API Route Handlers for Operational Sources and Ingestion (PRJ-07).
Manages file uploads, AI-driven schema suggestion, mapping confirmation, and background batch ingestion.
"""

import os
import shutil
import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import (
    APIRouter, Depends, HTTPException, UploadFile, File, Form, Header, Query,
    BackgroundTasks, status
)
from sqlalchemy.orm import Session

from backend.database import get_db, SessionLocal
from backend.models import Source, SourceColumn
from backend.services.field_mapper import suggest_mappings
from backend.services.ingestion import inspect_file_schema, extract_column_samples, ingest_source
from backend.services.enrichment_engine import resolve_workspace_entities
from backend.schemas import (
    SourceResponse,
    SourceStatusResponse,
    UploadResponse,
    MappingConfirmationRequest
)

router = APIRouter()

# Directory for persisting uploaded source datasets
BASE_DIR = Path(__file__).resolve().parent.parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _run_ingestion_background(source_id: int):
    """
    Background worker task executing chunked batch ingestion.
    Upon completion, automatically runs session-wide connected component graph resolution.
    """
    db = SessionLocal()
    try:
        ingest_source(source_id=source_id, db=db, chunksize=5000)
        source = db.query(Source).filter_by(id=source_id).first()
        if source and source.workspace_id:
            resolve_workspace_entities(workspace_id=source.workspace_id, db=db)
    finally:
        db.close()


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_source(
    file: UploadFile = File(...),
    source_type: Optional[str] = Form(None),
    workspace_id: Optional[str] = Form(None),
    x_workspace_id: Optional[str] = Header(None, alias="X-Workspace-Id"),
    db: Session = Depends(get_db)
):
    """
    Upload an operational silo dataset (.csv or .sql).
    Saves file to disk, inspects schema, and executes AI-assisted column mapping suggestions.
    Associates the dataset to the specified active workspace session.
    """
    target_workspace_id = workspace_id or x_workspace_id

    filename = file.filename or "unknown_source"
    ext = Path(filename).suffix.lower()

    # Detect or validate source_type
    detected_type = source_type.upper() if source_type else ("CSV" if ext == ".csv" else ("SQL" if ext == ".sql" else None))
    if detected_type not in ["CSV", "SQL"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Only .csv and .sql files are accepted."
        )

    # Save uploaded file safely
    unique_filename = f"{uuid.uuid4().hex[:8]}_{filename}"
    saved_path = UPLOAD_DIR / unique_filename

    try:
        with open(saved_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to persist uploaded file: {str(e)}"
        )

    # Inspect schema and sample rows dynamically without hardcoding
    try:
        table_name, columns, sample_rows = inspect_file_schema(str(saved_path), source_type=detected_type)
        if not columns:
            raise ValueError("No columns could be detected from the uploaded file.")
    except Exception as e:
        if saved_path.exists():
            saved_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error inspecting file schema: {str(e)}"
        )

    # Extract up to 3 real non-null sample values for each column
    column_samples = extract_column_samples(str(saved_path), columns=columns, source_type=detected_type, max_samples=3)

    # Generate mapping suggestions using canonical rules and real samples
    suggested_mappings = suggest_mappings(columns=columns, sample_rows=sample_rows, column_samples=column_samples)

    # Persist Source metadata in UPLOADED state
    source = Source(
        workspace_id=target_workspace_id,
        name=filename,
        source_type=detected_type,
        file_path=str(saved_path),
        record_count=0,
        status="UPLOADED"
    )
    db.add(source)
    db.commit()
    db.refresh(source)

    return UploadResponse(
        source_id=source.id,
        workspace_id=source.workspace_id,
        name=source.name,
        source_type=source.source_type,
        file_path=source.file_path,
        status=source.status,
        columns=columns,
        sample_rows=sample_rows,
        suggested_mappings=suggested_mappings,
        column_samples=column_samples
    )


@router.post("/{source_id}/confirm-mapping", status_code=status.HTTP_202_ACCEPTED)
def confirm_mapping(
    source_id: int,
    req: MappingConfirmationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Confirms user-verified column mappings and triggers asynchronous chunked batch ingestion.
    Transitions Source status from UPLOADED -> MAPPED -> INDEXED.
    """
    source = db.query(Source).filter_by(id=source_id).first()
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source with id={source_id} not found."
        )

    # Remove existing mappings if re-confirming
    db.query(SourceColumn).filter_by(source_id=source.id).delete()

    # Save confirmed SourceColumn definitions
    for orig_name, mapping in req.mappings.items():
        col = SourceColumn(
            source_id=source.id,
            original_name=orig_name,
            canonical_field=mapping.canonical_field,
            confidence_score=mapping.confidence_score,
            is_identifier=mapping.is_identifier
        )
        db.add(col)

    source.status = "MAPPED"
    db.commit()
    db.refresh(source)

    # Launch ingestion pipeline in background
    background_tasks.add_task(_run_ingestion_background, source.id)

    return {
        "source_id": source.id,
        "workspace_id": source.workspace_id,
        "status": "MAPPED",
        "message": "Column mappings confirmed. Batch ingestion initiated in background."
    }


@router.get("", response_model=List[SourceResponse])
def list_sources(
    workspace_id: Optional[str] = Query(None, description="Filter sources by active workspace session"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Lists operational sources, source types, statuses, and record counts.
    Optionally filters by workspace_id.
    """
    query = db.query(Source)
    if workspace_id:
        query = query.filter(Source.workspace_id == workspace_id)
    return query.order_by(Source.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/{source_id}/status", response_model=SourceStatusResponse)
def get_source_status(
    source_id: int,
    db: Session = Depends(get_db)
):
    """
    Polling endpoint for source ingestion status and indexed record counts.
    """
    source = db.query(Source).filter_by(id=source_id).first()
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source with id={source_id} not found."
        )

    return SourceStatusResponse(
        source_id=source.id,
        workspace_id=source.workspace_id,
        name=source.name,
        source_type=source.source_type,
        status=source.status,
        record_count=source.record_count,
        created_at=source.created_at
    )


@router.delete("/{source_id}", status_code=status.HTTP_200_OK)
def delete_source(
    source_id: int,
    db: Session = Depends(get_db)
):
    """
    Deletes an individual operational source, unlinks its stored file,
    and removes its indexed attributes from the repository.
    """
    source = db.query(Source).filter_by(id=source_id).first()
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source with id={source_id} not found."
        )

    # 1. Remove physical file
    try:
        if source.file_path and os.path.exists(source.file_path):
            os.remove(source.file_path)
    except Exception:
        pass

    # 2. Delete source record (cascades to source_columns and attribute_indices)
    db.delete(source)
    db.commit()

    return {
        "status": "deleted",
        "source_id": source_id,
        "message": f"Source '{source.name}' successfully removed."
    }

