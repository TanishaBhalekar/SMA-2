"""
Comprehensive Multi-Tenant Database Isolation Test Suite (PRJ-07).
Validates:
1. Workspace and Source models have indexed nullable user_id columns.
2. Auth helper get_current_user decodes HS256 JWTs and extracts sub claim.
3. Strict multi-tenant isolation across all Workspace, Source, Ingest, and Stats endpoints.
4. Legacy records with user_id IS NULL are handled cleanly without NoneType errors.
"""

import uuid
import jwt
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from fastapi import HTTPException

from backend.main import app
from backend.database import SessionLocal
from backend.models import Workspace, Source, AttributeIndex, MasterEntity
from backend.auth import get_current_user
from backend.config import SUPABASE_JWT_SECRET

client = TestClient(app)
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

USER_A = "tenant-user-alpha-uuid"
USER_B = "tenant-user-beta-uuid"


def test_models_have_user_id_column():
    """Verify Workspace and Source models define indexed user_id columns."""
    assert hasattr(Workspace, "user_id")
    assert hasattr(Source, "user_id")
    assert Workspace.user_id.property.columns[0].nullable is True
    assert Source.user_id.property.columns[0].nullable is True


def test_auth_get_current_user_decoding():
    """Verify get_current_user extracts 'sub' claim from HS256 Supabase JWT."""
    from backend.auth import security
    from fastapi.security import HTTPAuthorizationCredentials

    test_sub = "test-auth-user-12345"
    secret = SUPABASE_JWT_SECRET or "test_secret_key_12345678901234567890"

    # Valid token
    token = jwt.encode(
        {"sub": test_sub, "aud": "authenticated", "role": "authenticated"},
        secret,
        algorithm="HS256"
    )
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    import os
    orig_secret = os.environ.get("SUPABASE_JWT_SECRET")
    os.environ["SUPABASE_JWT_SECRET"] = secret
    try:
        user_id = get_current_user(creds)
        assert user_id == test_sub
        assert isinstance(user_id, str)
    finally:
        if orig_secret is not None:
            os.environ["SUPABASE_JWT_SECRET"] = orig_secret

    # Missing sub claim -> 401
    bad_token = jwt.encode(
        {"aud": "authenticated", "role": "authenticated"},
        secret,
        algorithm="HS256"
    )
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(HTTPAuthorizationCredentials(scheme="Bearer", credentials=bad_token))
    assert exc_info.value.status_code == 401


def test_workspace_crud_tenant_isolation():
    """
    Verify User A creates workspace -> user_id is set.
    User B cannot list, retrieve, update, or delete User A's workspace.
    """
    # 1. User A creates workspace
    app.dependency_overrides[get_current_user] = lambda: USER_A
    res_a = client.post("/api/workspaces", json={"name": "Alpha Secret Project"})
    assert res_a.status_code == 201
    data_a = res_a.json()
    ws_id = data_a["id"]
    assert data_a["user_id"] == USER_A

    # In DB, verify user_id is explicitly set
    db = SessionLocal()
    try:
        ws_row = db.query(Workspace).filter_by(id=ws_id).first()
        assert ws_row is not None
        assert ws_row.user_id == USER_A

        # User A lists workspaces -> sees it
        list_a = client.get("/api/workspaces?include_empty=true")
        assert list_a.status_code == 200
        assert any(w["id"] == ws_id for w in list_a.json())

        # User A accesses it -> 200
        get_a = client.get(f"/api/workspaces/{ws_id}")
        assert get_a.status_code == 200

        # 2. Switch to User B
        app.dependency_overrides[get_current_user] = lambda: USER_B

        # User B lists workspaces -> does NOT see User A's workspace
        list_b = client.get("/api/workspaces?include_empty=true")
        assert list_b.status_code == 200
        assert not any(w["id"] == ws_id for w in list_b.json())

        # User B tries GET /api/workspaces/{id} -> 404 "Workspace not found"
        get_b = client.get(f"/api/workspaces/{ws_id}")
        assert get_b.status_code == 404
        assert get_b.json()["detail"] == "Workspace not found"

        # User B tries GET /api/workspaces/{id}/stats -> 404 "Workspace not found"
        stats_b = client.get(f"/api/workspaces/{ws_id}/stats")
        assert stats_b.status_code == 404
        assert stats_b.json()["detail"] == "Workspace not found"

        # User B tries PATCH /api/workspaces/{id} -> 404 "Workspace not found"
        patch_b = client.patch(f"/api/workspaces/{ws_id}", json={"name": "Tampered"})
        assert patch_b.status_code == 404
        assert patch_b.json()["detail"] == "Workspace not found"

        # User B tries DELETE /api/workspaces/{id} -> 404 "Workspace not found"
        del_b = client.delete(f"/api/workspaces/{ws_id}")
        assert del_b.status_code == 404
        assert del_b.json()["detail"] == "Workspace not found"

    finally:
        # Cleanup
        app.dependency_overrides[get_current_user] = lambda: USER_A
        client.delete(f"/api/workspaces/{ws_id}")
        db.close()


def test_sources_and_ingestion_tenant_isolation():
    """
    Verify:
    - User A uploads dataset to User A's workspace -> source.user_id = USER_A.
    - User B cannot upload to User A's workspace (404).
    - User B cannot list User A's sources in GET /api/sources.
    - User B cannot view status in GET /api/sources/{id}/status (404).
    - User B cannot delete User A's source in DELETE /api/sources/{id} (404).
    - User B cannot ingest User A's source in POST /api/ingest (404).
    - GET /api/stats isolates metrics between tenants.
    """
    # 1. User A creates a workspace
    app.dependency_overrides[get_current_user] = lambda: USER_A
    res_ws = client.post("/api/workspaces", json={"name": "Alpha Dataset Workspace"})
    assert res_ws.status_code == 201
    ws_id = res_ws.json()["id"]

    db = SessionLocal()
    source_id = None
    try:
        # User A uploads a source
        test_file = DATA_DIR / "hr_db.csv"
        assert test_file.exists()

        with open(test_file, "rb") as f:
            res_up = client.post(
                "/api/sources/upload",
                files={"file": ("tenant_alpha_hr.csv", f, "text/csv")},
                data={"source_type": "CSV", "workspace_id": ws_id}
            )
        assert res_up.status_code == 201
        source_id = res_up.json()["source_id"]
        assert res_up.json()["user_id"] == USER_A

        # Confirm mapping for User A
        confirm_payload = {
            "mappings": {
                "employee_id": {"canonical_field": "custom", "confidence_score": 0.5, "is_identifier": False},
                "full_name": {"canonical_field": "name", "confidence_score": 0.95, "is_identifier": False},
                "email": {"canonical_field": "email", "confidence_score": 1.0, "is_identifier": True},
                "mobile_number": {"canonical_field": "phone", "confidence_score": 0.95, "is_identifier": True}
            }
        }
        res_conf = client.post(f"/api/sources/{source_id}/confirm-mapping", json=confirm_payload)
        assert res_conf.status_code == 202

        # User A checks global stats -> should count this source
        stats_a = client.get("/api/stats")
        assert stats_a.status_code == 200
        assert stats_a.json()["total_sources"] >= 1

        # 2. Switch to User B
        app.dependency_overrides[get_current_user] = lambda: USER_B

        # User B tries uploading to User A's workspace -> 404 "Workspace not found"
        with open(test_file, "rb") as f:
            hack_up = client.post(
                "/api/sources/upload",
                files={"file": ("hack.csv", f, "text/csv")},
                data={"source_type": "CSV", "workspace_id": ws_id}
            )
        assert hack_up.status_code == 404
        assert hack_up.json()["detail"] == "Workspace not found"

        # User B lists sources with workspace_id=ws_id -> 404 "Workspace not found"
        list_b_ws = client.get(f"/api/sources?workspace_id={ws_id}")
        assert list_b_ws.status_code == 404

        # User B lists sources globally -> does NOT see User A's source
        list_b_all = client.get("/api/sources")
        assert list_b_all.status_code == 200
        assert not any(s["id"] == source_id for s in list_b_all.json())

        # User B checks status of User A's source -> 404
        status_b = client.get(f"/api/sources/{source_id}/status")
        assert status_b.status_code == 404

        # User B attempts to ingest User A's source -> 404
        ingest_b = client.post("/api/ingest", json={"source_id": source_id})
        assert ingest_b.status_code == 404

        # User B attempts to ingest User A's workspace -> 404
        ingest_ws_b = client.post("/api/ingest", json={"workspace_id": ws_id})
        assert ingest_ws_b.status_code == 404

        # User B attempts to delete User A's source -> 404
        del_b = client.delete(f"/api/sources/{source_id}")
        assert del_b.status_code == 404

        # User B checks stats for User A's workspace -> 404
        ws_stats_b = client.get(f"/api/stats?workspace_id={ws_id}")
        assert ws_stats_b.status_code == 404

    finally:
        # Cleanup
        app.dependency_overrides[get_current_user] = lambda: USER_A
        if source_id:
            client.delete(f"/api/sources/{source_id}")
        client.delete(f"/api/workspaces/{ws_id}")
        db.close()


def test_legacy_records_null_user_id_safety():
    """
    Verify that existing legacy records with user_id = NULL
    do not cause unhandled NoneType errors.
    """
    db = SessionLocal()
    legacy_ws_id = f"legacy-ws-{uuid.uuid4().hex[:6]}"
    legacy_src_id = None
    try:
        # Create legacy workspace with user_id = None
        legacy_ws = Workspace(
            id=legacy_ws_id,
            user_id=None,
            name="Legacy Unassigned Session",
            description="Created before multi-tenant migration"
        )
        db.add(legacy_ws)
        db.commit()

        # Create legacy source with user_id = None
        legacy_src = Source(
            workspace_id=legacy_ws_id,
            user_id=None,
            name="legacy_data.csv",
            source_type="CSV",
            file_path="/fake/legacy.csv",
            record_count=10,
            status="INDEXED"
        )
        db.add(legacy_src)
        db.commit()
        db.refresh(legacy_src)
        legacy_src_id = legacy_src.id

        # Query via API with authenticated user
        app.dependency_overrides[get_current_user] = lambda: USER_A

        # GET /api/workspaces should execute cleanly without NoneType errors
        res_list = client.get("/api/workspaces?include_empty=true")
        assert res_list.status_code == 200

        # GET /api/sources should execute cleanly without NoneType errors
        res_sources = client.get("/api/sources")
        assert res_sources.status_code == 200

        # GET /api/stats should execute cleanly without NoneType errors
        res_stats = client.get("/api/stats")
        assert res_stats.status_code == 200

    finally:
        # Direct DB cleanup of legacy records
        if legacy_src_id:
            db.query(Source).filter_by(id=legacy_src_id).delete()
        db.query(Workspace).filter_by(id=legacy_ws_id).delete()
        db.commit()
        db.close()
