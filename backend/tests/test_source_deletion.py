"""
Test Suite for Dataset Cascade Deletion and Automatic Graph Re-Clustering.

Validates:
1. Cascade deletion:
   - Deleting a source deletes all associated rows in attribute_indices,
     entity_attributes, enrichment_hops, source_columns/mappings, and the source itself.
2. Automatic graph re-clustering:
   - After deleting a source from a multi-source session, DSU connected components
     and cross-source multi-hop link counters automatically re-cluster and update.
3. Total clearance:
   - When the last source is deleted, master entities drop to 0.
"""

from pathlib import Path
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
from backend.services.ingestion import ingest_source

client = TestClient(app)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"


def test_cascade_delete_source_and_automatic_reclustering():
    db = SessionLocal()
    ws_id = None

    try:
        # 1. Create a fresh workspace session
        res_ws = client.post(
            "/api/workspaces",
            json={"name": "Cascade Deletion Test Session", "description": "Testing deletion cascade and re-clustering"}
        )
        assert res_ws.status_code == 201
        ws_id = res_ws.json()["id"]

        # 2. Ingest Dataset A, Dataset B, and Dataset E
        test_files = [
            "dataset_A_customers.csv",
            "dataset_B_contacts.csv",
            "dataset_E_updates.csv"
        ]
        source_ids = []

        for fname in test_files:
            fpath = DATA_DIR / fname
            assert fpath.exists(), f"Missing file: {fpath}"

            with open(fpath, "rb") as f:
                res_up = client.post(
                    "/api/sources/upload",
                    data={"source_type": "CSV", "workspace_id": ws_id},
                    files={"file": (fname, f, "text/csv")}
                )
            assert res_up.status_code == 201
            up_data = res_up.json()
            sid = up_data["source_id"]
            source_ids.append(sid)

            confirmed_mappings = {
                col: {
                    "canonical_field": meta["canonical_field"],
                    "confidence_score": meta.get("confidence", 0.95),
                    "is_identifier": meta.get("is_identifier", False)
                }
                for col, meta in up_data["suggested_mappings"].items()
            }
            res_conf = client.post(
                f"/api/sources/{sid}/confirm-mapping",
                json={"mappings": confirmed_mappings}
            )
            assert res_conf.status_code == 202

            ingest_source(source_id=sid, db=db)

        # 3. Resolve session initially
        res_res = client.post(f"/api/workspaces/{ws_id}/resolve")
        assert res_res.status_code == 200

        res_stats_before = client.get(f"/api/workspaces/{ws_id}/stats")
        stats_before = res_stats_before.json()
        assert stats_before["master_entities"] == 11  # 10 baseline + 1 new (Devendra)
        assert stats_before["total_sources"] == 3

        dataset_e_sid = source_ids[2]

        # Verify dataset E attributes exist in DB
        attrs_e_count = db.query(AttributeIndex).filter_by(source_id=dataset_e_sid).count()
        assert attrs_e_count > 0, "Dataset E attributes should exist prior to deletion"

        cols_e_count = db.query(SourceColumn).filter_by(source_id=dataset_e_sid).count()
        assert cols_e_count > 0, "Dataset E source_columns should exist prior to deletion"

        # 4. Trigger DELETE /api/sources/{source_id} for Dataset E
        res_del = client.delete(f"/api/sources/{dataset_e_sid}")
        assert res_del.status_code == 200, f"Delete failed: {res_del.text}"
        del_data = res_del.json()
        assert del_data["status"] == "deleted"
        assert del_data["source_id"] == dataset_e_sid

        # 5. Verify Database Cascade Deletion
        # Check attribute_indices
        attrs_remaining = db.query(AttributeIndex).filter_by(source_id=dataset_e_sid).count()
        assert attrs_remaining == 0, f"Expected 0 attributes for deleted source, found {attrs_remaining}"

        # Check source_columns
        cols_remaining = db.query(SourceColumn).filter_by(source_id=dataset_e_sid).count()
        assert cols_remaining == 0, f"Expected 0 source_columns for deleted source, found {cols_remaining}"

        # Check entity_attributes
        ent_attrs_remaining = db.query(EntityAttribute).filter_by(source_id=dataset_e_sid).count()
        assert ent_attrs_remaining == 0, f"Expected 0 entity_attributes for deleted source, found {ent_attrs_remaining}"

        # Check enrichment_hops
        hops_remaining = db.query(EnrichmentHop).filter_by(source_id=dataset_e_sid).count()
        assert hops_remaining == 0, f"Expected 0 enrichment_hops for deleted source, found {hops_remaining}"

        # Check source record
        src_obj = db.query(Source).filter_by(id=dataset_e_sid).first()
        assert src_obj is None, "Source record itself should be deleted"

        # 6. Verify Automatic Graph Re-Clustering Telemetry
        res_stats_after = client.get(f"/api/workspaces/{ws_id}/stats")
        stats_after = res_stats_after.json()

        # Devendra Verma from Dataset E is gone, so entities drop from 11 back to 10
        assert stats_after["master_entities"] == 10, f"Expected 10 master entities after removing E, got {stats_after['master_entities']}"
        assert stats_after["total_sources"] == 2, f"Expected 2 sources remaining, got {stats_after['total_sources']}"

        # Devendra should no longer exist in search
        res_search_dev = client.get(f"/api/entities/search?field=name&value=Devendra Verma&workspace_id={ws_id}")
        assert res_search_dev.status_code == 404, "Devendra Verma should no longer exist after Dataset E is deleted"

        # 7. Delete remaining sources and verify complete clearance
        for remaining_sid in source_ids[:2]:
            res_d = client.delete(f"/api/sources/{remaining_sid}")
            assert res_d.status_code == 200

        res_stats_empty = client.get(f"/api/workspaces/{ws_id}/stats")
        stats_empty = res_stats_empty.json()
        assert stats_empty["total_sources"] == 0
        assert stats_empty["master_entities"] == 0
        assert stats_empty["links_discovered"] == 0

    finally:
        if ws_id:
            try:
                client.delete(f"/api/workspaces/{ws_id}")
            except Exception:
                pass
        db.close()
