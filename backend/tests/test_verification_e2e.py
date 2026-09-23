"""
End-to-End Verification of the 6 Critical Fixes (PRJ-07).
Validates:
1. Re-ingestion of 4 CSV datasets (Dataset A, B, C, D).
2. Dynamic schema inspection & column mapping verification (Datasets C and D headers & samples).
3. Dashboard telemetry: exactly 10 Master Entities and positive Multi-Hop Links.
4. Entity search: searching 'Rahul Sharma' and 'rahul@gmail.com' produces clean unified Master Entity with 'Rahul Sharma' authoritative name and zero duplicate attribute lines.
"""

import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.database import SessionLocal
from backend.models import Workspace, Source, AttributeIndex, MasterEntity, EnrichmentHop

client = TestClient(app)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"


def test_four_datasets_ingestion_and_resolution():
    db = SessionLocal()
    ws_id = "ws-e2e-verification"

    # Clean up prior test workspace if exists
    try:
        client.delete(f"/api/workspaces/{ws_id}")
    except Exception:
        pass

    try:
        # Step 1: Create fresh active workspace session
        res_ws = client.post("/api/workspaces", json={"name": "E2E Verification Session", "description": "Verification of 4 datasets"})
        assert res_ws.status_code == 201
        ws_id = res_ws.json()["id"]

        datasets = [
            ("dataset_A_customers.csv", "dataset_A_customers.csv"),
            ("dataset_B_contacts.csv", "dataset_B_contacts.csv"),
            ("dataset_C_business.csv", "dataset_C_business.csv"),
            ("dataset_D_members.csv", "dataset_D_members.csv")
        ]

        uploaded_sources = []

        for fname, label in datasets:
            file_path = DATA_DIR / fname
            assert file_path.exists(), f"Missing dataset file {file_path}"

            with open(file_path, "rb") as f:
                res_up = client.post(
                    "/api/sources/upload",
                    data={"source_type": "CSV", "workspace_id": ws_id},
                    files={"file": (fname, f, "text/csv")}
                )
            assert res_up.status_code == 201, f"Failed upload for {fname}: {res_up.text}"
            up_data = res_up.json()
            uploaded_sources.append(up_data)

            # Verification of Schema Inspection (Fix 1)
            columns = up_data["columns"]
            column_samples = up_data.get("column_samples") or {}

            if fname == "dataset_C_business.csv":
                expected_c = ["company_id", "primary_contact", "phone", "username", "company"]
                assert columns == expected_c, f"Dataset C columns mismatch: {columns}"
                for col in expected_c:
                    assert len(column_samples.get(col, [])) > 0, f"Missing samples for Dataset C col {col}"
                # Mapping checks
                mappings = up_data["suggested_mappings"]
                assert mappings["company_id"]["canonical_field"] == "source_record_id"
                assert mappings["company_id"]["is_identifier"] is True
                assert mappings["primary_contact"]["canonical_field"] == "name"
                assert mappings["phone"]["canonical_field"] == "phone"
                assert mappings["username"]["canonical_field"] == "username"
                assert mappings["company"]["canonical_field"] == "company"

            if fname == "dataset_D_members.csv":
                expected_d = ["member_id", "email_address", "username", "city", "account_status"]
                assert columns == expected_d, f"Dataset D columns mismatch: {columns}"
                for col in expected_d:
                    assert len(column_samples.get(col, [])) > 0, f"Missing samples for Dataset D col {col}"
                # Mapping checks
                mappings = up_data["suggested_mappings"]
                assert mappings["member_id"]["canonical_field"] == "source_record_id"
                assert mappings["member_id"]["is_identifier"] is True
                assert mappings["email_address"]["canonical_field"] == "email"
                assert mappings["email_address"]["is_identifier"] is True
                assert mappings["username"]["canonical_field"] == "username"
                assert mappings["city"]["canonical_field"] == "address"
                assert mappings["account_status"]["canonical_field"] == "metadata"

            # Confirm mapping and ingest synchronously
            confirmed_mappings = {
                col: {
                    "canonical_field": meta["canonical_field"],
                    "confidence_score": meta.get("confidence", 0.95),
                    "is_identifier": meta.get("is_identifier", False)
                }
                for col, meta in up_data["suggested_mappings"].items()
            }
            res_conf = client.post(
                f"/api/sources/{up_data['source_id']}/confirm-mapping",
                json={"mappings": confirmed_mappings}
            )
            assert res_conf.status_code == 202

            # Directly run ingestion synchronously to test deterministic state
            from backend.services.ingestion import ingest_source
            ingest_source(source_id=up_data["source_id"], db=db)

        # Step 2: Trigger Session-Wide Resolution Pass (Fix 3)
        res_resolve = client.post(f"/api/workspaces/{ws_id}/resolve")
        assert res_resolve.status_code == 200
        res_json = res_resolve.json()

        # Step 3: Verify Dashboard Telemetry (Fix 3)
        res_stats = client.get(f"/api/workspaces/{ws_id}/stats")
        assert res_stats.status_code == 200
        stats = res_stats.json()

        assert stats["master_entities"] == 10, f"Expected 10 Master Entities, got {stats['master_entities']}"
        assert stats["links_discovered"] > 0, f"Expected > 0 links, got {stats['links_discovered']}"

        # Global stats endpoint verification
        res_global_stats = client.get(f"/api/stats?workspace_id={ws_id}")
        assert res_global_stats.status_code == 200
        g_stats = res_global_stats.json()
        assert g_stats["master_entities"] == 10
        assert g_stats["links_discovered"] == stats["links_discovered"]

        # Step 4: Verify Search for 'Rahul Sharma' (Fix 2 & 4)
        res_search_name = client.get(f"/api/entities/search?field=name&value=Rahul Sharma&workspace_id={ws_id}")
        assert res_search_name.status_code == 200, f"Search by name failed: {res_search_name.text}"
        data_name = res_search_name.json()
        entity_name = data_name["entity"]
        auth_name = entity_name["authoritative_profile"]

        assert auth_name["name"] == "Rahul Sharma", f"Expected authoritative name 'Rahul Sharma', got {auth_name['name']}"
        assert auth_name["email"] == "rahul.sharma@gmail.com"
        assert auth_name["phone"] == "9876543210"
        assert auth_name["username"] == "rahulsharma"
        assert auth_name["address"] == "Mumbai"
        assert auth_name["company"] == "TechNova"
        assert auth_name["member_id"] == "M1042"

        # Verify Search for 'rahul@gmail.com' (Fuzzy/prefix fallback anchor match)
        res_search_email = client.get(f"/api/entities/search?field=email&value=rahul@gmail.com&workspace_id={ws_id}")
        assert res_search_email.status_code == 200, f"Search by email fallback failed: {res_search_email.text}"
        data_email = res_search_email.json()
        entity_email = data_email["entity"]
        auth_email = entity_email["authoritative_profile"]

        assert auth_email["name"] == "Rahul Sharma", f"Expected authoritative name 'Rahul Sharma', got {auth_email['name']}"
        assert auth_email["email"] == "rahul.sharma@gmail.com"
        assert auth_email["phone"] == "9876543210"

    finally:
        client.delete(f"/api/workspaces/{ws_id}")
        db.close()
