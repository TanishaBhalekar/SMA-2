"""
Endpoints for managing Master Entities, progressive BFS graph discovery, and repository stats.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.database import get_db
from backend.models import (
    CanonicalEntity,
    RawRecord,
    MasterEntity,
    EntityAttribute,
    EnrichmentHop,
    Source,
    AttributeIndex
)
from backend.schemas import (
    CanonicalEntityCreate,
    CanonicalEntityResponse,
    RawRecordCreate,
    RawRecordResponse
)
from backend.services.enrichment_engine import progressive_enrich

router = APIRouter()


# ============================================================================
# Progressive Graph Search & Discovery Endpoints
# ============================================================================

@router.get("/search")
def search_and_enrich_entity(
    field: str = Query(..., description="Seed attribute field name (e.g. 'full_name', 'email', 'phone', 'name')"),
    value: str = Query(..., description="Seed attribute search value (e.g. 'John Doe', '9876543210')"),
    db: Session = Depends(get_db)
):
    """
    Executes iterative BFS graph discovery starting from an initial anchor seed attribute.
    Traverses cross-silo identifiers and outputs the consolidated 360-degree profile,
    source provenance lineage, and step-by-step discovery timeline.
    """
    if not field.strip() or not value.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query parameters 'field' and 'value' cannot be empty."
        )

    result = progressive_enrich(seed_field=field, seed_value=value, db=db)
    if result.get("status") == "not_found":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result.get("message", f"No matching entity found for {field}='{value}'.")
        )

    return result


@router.get("/stats")
def get_entity_repository_stats(db: Session = Depends(get_db)):
    """
    Returns global repository metrics across all operational silos.
    """
    total_sources = db.query(Source).count()
    indexed_records = db.query(func.coalesce(func.sum(Source.record_count), 0)).scalar() or 0
    total_attributes_indexed = db.query(AttributeIndex).count()
    master_entities = db.query(MasterEntity).count()
    links_discovered = db.query(EnrichmentHop).count()

    return {
        "total_sources": total_sources,
        "indexed_records": int(indexed_records),
        "total_attributes_indexed": total_attributes_indexed,
        "master_entities": master_entities,
        "links_discovered": links_discovered
    }


@router.get("/{entity_id}")
def get_master_entity_details(
    entity_id: str,
    db: Session = Depends(get_db)
):
    """
    Retrieves a consolidated MasterEntity profile with full attribute provenance and discovery hop history.
    """
    entity = db.query(MasterEntity).filter_by(id=entity_id).first()
    if not entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MasterEntity with id='{entity_id}' not found."
        )

    # Format attributes
    attributes_list = [
        {
            "canonical_field": a.canonical_field,
            "original_value": a.original_value,
            "normalized_value": a.normalized_value,
            "source_id": a.source_id,
            "record_index": a.record_index,
            "is_identifier": a.is_identifier
        }
        for a in entity.attributes
    ]

    # Group attributes by field
    consolidated: Dict[str, List[str]] = {}
    for a in attributes_list:
        field = a["canonical_field"]
        val = a["original_value"] or a["normalized_value"]
        if val:
            consolidated.setdefault(field, [])
            if val not in consolidated[field]:
                consolidated[field].append(val)

    # Format discovery hops
    hops_list = [
        {
            "step_order": h.step_order,
            "source_id": h.source_id,
            "matched_field": h.matched_field,
            "matched_value": h.matched_value,
            "discovered_field": h.discovered_field,
            "discovered_value": h.discovered_value
        }
        for h in entity.hops
    ]

    return {
        "id": entity.id,
        "canonical_name": entity.canonical_name,
        "created_at": entity.created_at.isoformat() if entity.created_at else None,
        "updated_at": entity.updated_at.isoformat() if entity.updated_at else None,
        "consolidated_attributes": consolidated,
        "attributes": attributes_list,
        "hops": hops_list,
        "total_attributes": len(attributes_list),
        "total_hops": len(hops_list)
    }


# ============================================================================
# Staging / Legacy Canonical Routes (Preserved for compatibility)
# ============================================================================

@router.get("/canonical", response_model=List[CanonicalEntityResponse])
def list_canonical_entities(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    return db.query(CanonicalEntity).offset(skip).limit(limit).all()


@router.post("/canonical", response_model=CanonicalEntityResponse, status_code=201)
def create_canonical_entity(
    entity: CanonicalEntityCreate,
    db: Session = Depends(get_db)
):
    db_entity = CanonicalEntity(**entity.model_dump())
    db.add(db_entity)
    db.commit()
    db.refresh(db_entity)
    return db_entity


@router.get("/raw", response_model=List[RawRecordResponse])
def list_raw_records(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    return db.query(RawRecord).offset(skip).limit(limit).all()


@router.post("/raw", response_model=RawRecordResponse, status_code=201)
def ingest_raw_record(
    record: RawRecordCreate,
    db: Session = Depends(get_db)
):
    db_record = RawRecord(**record.model_dump())
    db.add(db_record)
    db.commit()
    db.refresh(db_record)
    return db_record
