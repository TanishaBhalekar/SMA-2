"""
Tests for Workspaces & Ingestion Sessions API (PRJ-07).
Validates session creation, browsing history, telemetry aggregation, renaming,
cascading deletion, and multi-tenant BFS graph isolation between sessions.
"""

import uuid
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.database import SessionLocal
from backend.models import Workspace, Source, AttributeIndex, MasterEntity, EntityAttribute, EnrichmentHop
from backend.services.enrichment_engine import progressive_enrich

client = TestClient(app)


def test_create_workspace():
    """Verify POST /api/workspaces creates a new session."""
    res = client.post("/api/workspaces", json={"name": "Alpha Research Session", "description": "Testing session"})
    assert res.status_code == 201
    data = res.json()
    assert data["id"].startswith("ws-")
    assert data["name"] == "Alpha Research Session"
    assert data["description"] == "Testing session"
    assert data["total_sources"] == 0

    # Test auto-generated name when name is empty
    res2 = client.post("/api/workspaces", json={})
    assert res2.status_code == 201
    assert res2.json()["name"].startswith("Session - ")


def test_list_and_get_workspaces():
    """Verify GET /api/workspaces and GET /api/workspaces/{id}."""
    # Create workspace
    create_res = client.post("/api/workspaces", json={"name": "Beta Workspace"})
    ws_id = create_res.json()["id"]

    # List
    list_res = client.get("/api/workspaces")
    assert list_res.status_code == 200
    workspaces = list_res.json()
    assert any(w["id"] == ws_id for w in workspaces)

    # Get details
    detail_res = client.get(f"/api/workspaces/{ws_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["id"] == ws_id
    assert detail["name"] == "Beta Workspace"
    assert "sources" in detail
    assert "stats" in detail


def test_update_and_rename_workspace():
    """Verify PATCH /api/workspaces/{id} renames session."""
    create_res = client.post("/api/workspaces", json={"name": "Old Name"})
    ws_id = create_res.json()["id"]

    patch_res = client.patch(f"/api/workspaces/{ws_id}", json={"name": "New Renamed Session"})
    assert patch_res.status_code == 200
    assert patch_res.json()["name"] == "New Renamed Session"


def test_workspace_isolation_and_cascade_delete():
    """
    Verify that two independent workspaces isolate their EAV search indexes,
    and deleting a workspace cleans up all associated sources and attributes.
    """
    db = SessionLocal()
    ws1_id = f"ws-test-isolation-1-{uuid.uuid4().hex[:6]}"
    ws2_id = f"ws-test-isolation-2-{uuid.uuid4().hex[:6]}"

    try:
        # Create 2 workspaces
        ws1 = Workspace(id=ws1_id, name="Session 1")
        ws2 = Workspace(id=ws2_id, name="Session 2")
        db.add_all([ws1, ws2])
        db.commit()

        # Ingest a source in Session 1
        s1 = Source(workspace_id=ws1_id, name="s1.csv", source_type="CSV", file_path="/fake/s1.csv", record_count=1, status="INDEXED")
        s2 = Source(workspace_id=ws2_id, name="s2.csv", source_type="CSV", file_path="/fake/s2.csv", record_count=1, status="INDEXED")
        db.add_all([s1, s2])
        db.commit()
        db.refresh(s1)
        db.refresh(s2)

        # Add index records: John Doe in Session 1, Jane Smith in Session 2
        a1 = AttributeIndex(workspace_id=ws1_id, source_id=s1.id, record_index=0, canonical_field="name", original_value="John Doe", normalized_value="john doe", is_identifier=False)
        a2 = AttributeIndex(workspace_id=ws1_id, source_id=s1.id, record_index=0, canonical_field="email", original_value="john@test.com", normalized_value="john@test.com", is_identifier=True)
        a3 = AttributeIndex(workspace_id=ws2_id, source_id=s2.id, record_index=0, canonical_field="name", original_value="Jane Smith", normalized_value="jane smith", is_identifier=False)
        a4 = AttributeIndex(workspace_id=ws2_id, source_id=s2.id, record_index=0, canonical_field="email", original_value="jane@test.com", normalized_value="jane@test.com", is_identifier=True)
        db.add_all([a1, a2, a3, a4])
        db.commit()

        # Search for john@test.com in Session 1 -> should succeed
        res1 = progressive_enrich(seed_field="email", seed_value="john@test.com", db=db, workspace_id=ws1_id)
        assert res1["status"] == "success"
        assert res1["entity"]["canonical_name"] == "John Doe"

        # Search for john@test.com in Session 2 -> should return not_found because isolated to Session 2!
        res2 = progressive_enrich(seed_field="email", seed_value="john@test.com", db=db, workspace_id=ws2_id)
        assert res2["status"] == "not_found"

        # Search for jane@test.com in Session 2 -> should succeed
        res3 = progressive_enrich(seed_field="email", seed_value="jane@test.com", db=db, workspace_id=ws2_id)
        assert res3["status"] == "success"
        assert res3["entity"]["canonical_name"] == "Jane Smith"

        # Verify API /api/entities/search with workspace_id query param
        api_res1 = client.get(f"/api/entities/search?field=email&value=john@test.com&workspace_id={ws1_id}")
        assert api_res1.status_code == 200

        api_res2 = client.get(f"/api/entities/search?field=email&value=john@test.com&workspace_id={ws2_id}")
        assert api_res2.status_code == 404

        # Verify cascading deletion via DELETE /api/workspaces/{id}
        del_res = client.delete(f"/api/workspaces/{ws1_id}")
        assert del_res.status_code == 200

        # Verify ws1 and its sources/attributes are deleted
        assert db.query(Workspace).filter_by(id=ws1_id).first() is None
        assert db.query(Source).filter_by(workspace_id=ws1_id).count() == 0
        assert db.query(AttributeIndex).filter_by(workspace_id=ws1_id).count() == 0

        # Verify ws2 remains untouched
        assert db.query(Workspace).filter_by(id=ws2_id).first() is not None
        assert db.query(Source).filter_by(workspace_id=ws2_id).count() == 1

    finally:
        # Cleanup both ws1 and ws2
        client.delete(f"/api/workspaces/{ws1_id}")
        client.delete(f"/api/workspaces/{ws2_id}")
        db.close()
