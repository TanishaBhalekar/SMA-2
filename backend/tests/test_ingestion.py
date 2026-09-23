"""
Integration tests for batch ingestion pipeline and source API endpoints (PRJ-07).
Tests chunked CSV & SQL parsing, upload endpoint, mapping confirmation, and EAV indexing.
"""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.database import SessionLocal
from backend.models import Source, SourceColumn, AttributeIndex
from backend.services.ingestion import (
    inspect_file_schema,
    stream_csv_records,
    stream_sql_records,
    ingest_source
)

client = TestClient(app)
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


def test_inspect_csv_schema():
    """Verify inspection of hr_db.csv extracts correct columns and sample rows."""
    hr_csv = DATA_DIR / "hr_db.csv"
    assert hr_csv.exists()

    name, columns, sample_rows = inspect_file_schema(str(hr_csv), source_type="CSV")
    assert "hr_db.csv" in name
    assert columns == ["employee_id", "full_name", "email", "mobile_number"]
    assert len(sample_rows) == 5
    assert "email" in sample_rows[0]


def test_inspect_sql_schema():
    """Verify inspection of crm_db.sql extracts correct table name and columns."""
    crm_sql = DATA_DIR / "crm_db.sql"
    assert crm_sql.exists()

    name, columns, sample_rows = inspect_file_schema(str(crm_sql), source_type="SQL")
    assert name == "crm_db"
    assert columns == ["client_id", "name", "email_id", "contact_no", "address"]
    assert len(sample_rows) > 0


def test_stream_csv_records_chunks():
    """Verify CSV streaming in small chunk sizes."""
    hr_csv = DATA_DIR / "hr_db.csv"
    chunks = list(stream_csv_records(str(hr_csv), chunksize=300))
    # 1200 records / 300 = 4 chunks
    assert len(chunks) == 4
    total_recs = sum(len(c) for c in chunks)
    assert total_recs == 1200


def test_stream_sql_records_chunks():
    """Verify SQL streaming in small chunk sizes."""
    crm_sql = DATA_DIR / "crm_db.sql"
    columns = ["client_id", "name", "email_id", "contact_no", "address"]
    chunks = list(stream_sql_records(str(crm_sql), columns=columns, chunksize=400))
    # 1200 records / 400 = 3 chunks
    assert len(chunks) == 3
    total_recs = sum(len(c) for c in chunks)
    assert total_recs == 1200


def test_api_upload_and_confirm_workflow_csv():
    """Verify end-to-end API upload, mapping confirmation, and indexing of CSV."""
    hr_csv = DATA_DIR / "hr_db.csv"
    with open(hr_csv, "rb") as f:
        response = client.post(
            "/api/sources/upload",
            files={"file": ("hr_db_test.csv", f, "text/csv")},
            data={"source_type": "CSV"}
        )

    assert response.status_code == 201
    data = response.json()
    source_id = data["source_id"]
    assert data["status"] == "UPLOADED"
    assert "full_name" in data["suggested_mappings"]
    assert data["suggested_mappings"]["full_name"]["canonical_field"] == "name"

    # Confirm mappings
    confirm_payload = {
        "mappings": {
            "employee_id": {"canonical_field": "custom", "confidence_score": 0.5, "is_identifier": False},
            "full_name": {"canonical_field": "name", "confidence_score": 0.95, "is_identifier": False},
            "email": {"canonical_field": "email", "confidence_score": 1.0, "is_identifier": True},
            "mobile_number": {"canonical_field": "phone", "confidence_score": 0.95, "is_identifier": True}
        }
    }

    confirm_res = client.post(f"/api/sources/{source_id}/confirm-mapping", json=confirm_payload)
    assert confirm_res.status_code == 202

    # Run ingestion synchronously to verify database state immediately
    db = SessionLocal()
    try:
        res = ingest_source(source_id=source_id, db=db, chunksize=500)
        assert res["status"] == "INDEXED"
        assert res["record_count"] == 1200

        # Poll status endpoint
        status_res = client.get(f"/api/sources/{source_id}/status")
        assert status_res.status_code == 200
        status_data = status_res.json()
        assert status_data["status"] == "INDEXED"
        assert status_data["record_count"] == 1200

        # Check EAV AttributeIndex
        phone_attrs = db.query(AttributeIndex).filter_by(
            source_id=source_id,
            canonical_field="phone"
        ).count()
        assert phone_attrs == 1200

        # Check normalized John Doe phone
        john_phone = db.query(AttributeIndex).filter_by(
            source_id=source_id,
            canonical_field="phone",
            normalized_value="9876543210"
        ).first()
        assert john_phone is not None

    finally:
        # Cleanup test source and indices
        db.query(AttributeIndex).filter_by(source_id=source_id).delete()
        db.query(SourceColumn).filter_by(source_id=source_id).delete()
        db.query(Source).filter_by(id=source_id).delete()
        db.commit()
        db.close()


def test_api_list_sources():
    """Verify GET /api/sources returns list of sources."""
    res = client.get("/api/sources")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_api_upload_and_confirm_workflow_sql():
    """Verify end-to-end API upload and confirmation of SQL dump."""
    crm_sql = DATA_DIR / "crm_db.sql"
    with open(crm_sql, "rb") as f:
        response = client.post(
            "/api/sources/upload",
            files={"file": ("crm_db_test.sql", f, "application/sql")},
            data={"source_type": "SQL"}
        )

    assert response.status_code == 201
    data = response.json()
    source_id = data["source_id"]
    assert data["source_type"] == "SQL"
    assert "contact_no" in data["suggested_mappings"]
    assert data["suggested_mappings"]["contact_no"]["canonical_field"] == "phone"

    confirm_payload = {
        "mappings": {
            "client_id": {"canonical_field": "custom", "confidence_score": 0.5, "is_identifier": False},
            "name": {"canonical_field": "name", "confidence_score": 1.0, "is_identifier": False},
            "email_id": {"canonical_field": "email", "confidence_score": 0.95, "is_identifier": True},
            "contact_no": {"canonical_field": "phone", "confidence_score": 0.95, "is_identifier": True},
            "address": {"canonical_field": "address", "confidence_score": 1.0, "is_identifier": False}
        }
    }

    confirm_res = client.post(f"/api/sources/{source_id}/confirm-mapping", json=confirm_payload)
    assert confirm_res.status_code == 202

    # Verify background execution status
    db = SessionLocal()
    try:
        status_res = client.get(f"/api/sources/{source_id}/status")
        assert status_res.status_code == 200
        status_data = status_res.json()
        assert status_data["status"] == "INDEXED"
        assert status_data["record_count"] == 1200
    finally:
        db.query(AttributeIndex).filter_by(source_id=source_id).delete()
        db.query(SourceColumn).filter_by(source_id=source_id).delete()
        db.query(Source).filter_by(id=source_id).delete()
        db.commit()
        db.close()

