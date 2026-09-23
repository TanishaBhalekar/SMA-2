"""
Unit and integration tests for iterative graph-discovery engine (PRJ-07).
Validates BFS progressive enrichment, cross-silo discovery hops, MasterEntity persistence,
and FastAPI search/entity/stats endpoints.
"""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.database import SessionLocal
from backend.models import (
    Source,
    SourceColumn,
    AttributeIndex,
    MasterEntity,
    EntityAttribute,
    EnrichmentHop
)
from backend.services.enrichment_engine import progressive_enrich
from backend.services.ingestion import ingest_source

client = TestClient(app)
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


@pytest.fixture(scope="module")
def setup_ingested_silos():
    """
    Ingests all 4 operational silos (HR, CRM, Platform, Membership)
    to enable true 4-hop progressive graph traversal testing.
    """
    db = SessionLocal()
    source_ids = []

    silos = [
        ("hr_db.csv", "CSV", {
            "employee_id": ("custom", False),
            "full_name": ("name", False),
            "email": ("email", True),
            "mobile_number": ("phone", True)
        }),
        ("crm_db.csv", "CSV", {
            "client_id": ("custom", False),
            "name": ("name", False),
            "email_id": ("email", True),
            "contact_no": ("phone", True),
            "address": ("address", False)
        }),
        ("platform_db.csv", "CSV", {
            "username": ("username", True),
            "phone": ("phone", True),
            "company": ("company", False),
            "registered_ip": ("custom", False)
        }),
        ("membership_db.csv", "CSV", {
            "member_id": ("member_id", True),
            "email": ("email", True),
            "username": ("username", True),
            "loyalty_tier": ("loyalty_tier", False)
        })
    ]

    try:
        for filename, stype, col_map in silos:
            file_path = DATA_DIR / filename
            assert file_path.exists(), f"Missing dataset: {filename}"

            src = Source(
                name=filename,
                source_type=stype,
                file_path=str(file_path),
                record_count=0,
                status="MAPPED"
            )
            db.add(src)
            db.commit()
            db.refresh(src)
            source_ids.append(src.id)

            for orig_col, (canon_field, is_id) in col_map.items():
                db.add(SourceColumn(
                    source_id=src.id,
                    original_name=orig_col,
                    canonical_field=canon_field,
                    confidence_score=1.0,
                    is_identifier=is_id
                ))
            db.commit()

            # Execute ingestion
            ingest_source(source_id=src.id, db=db, chunksize=1000)

        yield source_ids

    finally:
        # Cleanup: delete hops and entity attributes first to respect foreign key constraints
        db.query(EnrichmentHop).delete()
        db.query(EntityAttribute).delete()
        db.query(MasterEntity).delete()
        for sid in source_ids:
            db.query(AttributeIndex).filter_by(source_id=sid).delete()
            db.query(SourceColumn).filter_by(source_id=sid).delete()
            db.query(Source).filter_by(id=sid).delete()
        db.commit()
        db.close()



def test_progressive_enrich_john_doe(setup_ingested_silos):
    """
    Verify BFS graph discovery completes the full 4-database discovery path for John Doe.
    """
    db = SessionLocal()
    try:
        result = progressive_enrich(seed_field="full_name", seed_value="John Doe", db=db)

        assert result["status"] == "success"
        entity = result["entity"]
        assert entity is not None
        assert entity["canonical_name"] == "John Doe"

        # Check consolidated attributes
        attrs = entity["consolidated_attributes"]
        assert "name" in attrs
        assert "phone" in attrs
        assert "9876543210" in attrs["phone"]
        assert "address" in attrs
        assert "Mumbai" in attrs["address"]
        assert "company" in attrs
        assert "ABC Pvt Ltd" in attrs["company"]
        assert "username" in attrs
        assert "johndoe" in attrs["username"]
        assert "member_id" in attrs
        assert "M1042" in attrs["member_id"]
        assert "loyalty_tier" in attrs
        assert "Platinum" in attrs["loyalty_tier"]

        # Check hops and lineage
        assert result["total_sources_linked"] >= 4
        assert len(result["hops"]) >= 4

        # Check database persistence
        master_in_db = db.query(MasterEntity).filter_by(id=entity["id"]).first()
        assert master_in_db is not None
        assert len(master_in_db.attributes) > 0
        assert len(master_in_db.hops) > 0

    finally:
        db.close()


def test_api_entities_search(setup_ingested_silos):
    """Verify GET /api/entities/search returns 360-degree profile."""
    res = client.get("/api/entities/search?field=name&value=John Doe")
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "success"
    assert data["entity"]["canonical_name"] == "John Doe"
    assert "Mumbai" in data["entity"]["consolidated_attributes"]["address"]
    assert "johndoe" in data["entity"]["consolidated_attributes"]["username"]
    assert "M1042" in data["entity"]["consolidated_attributes"]["member_id"]
    assert len(data["hops"]) > 0


def test_api_entities_search_not_found(setup_ingested_silos):
    """Verify GET /api/entities/search returns 404 for non-existent entities."""
    res = client.get("/api/entities/search?field=name&value=NonExistentPersonX999")
    assert res.status_code == 404


def test_api_get_master_entity_details(setup_ingested_silos):
    """Verify GET /api/entities/{entity_id} retrieves master entity with hop history."""
    # First search to ensure entity exists
    search_res = client.get("/api/entities/search?field=phone&value=9876543210")
    assert search_res.status_code == 200
    ent_id = search_res.json()["entity"]["id"]

    # Retrieve details
    res = client.get(f"/api/entities/{ent_id}")
    assert res.status_code == 200
    details = res.json()

    assert details["id"] == ent_id
    assert details["canonical_name"] == "John Doe"
    assert len(details["attributes"]) > 0
    assert len(details["hops"]) > 0


def test_api_stats_endpoint(setup_ingested_silos):
    """Verify GET /api/stats and GET /api/entities/stats return repository metrics."""
    res1 = client.get("/api/stats")
    assert res1.status_code == 200
    stats1 = res1.json()

    assert stats1["total_sources"] >= 4
    assert stats1["indexed_records"] >= 4800
    assert stats1["total_attributes_indexed"] > 0
    assert stats1["master_entities"] >= 1
    assert stats1["links_discovered"] > 0

    res2 = client.get("/api/entities/stats")
    assert res2.status_code == 200
    assert res2.json() == stats1
