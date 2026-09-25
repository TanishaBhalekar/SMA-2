"""
Automated Verification Script for Entity Resolution & Clustering (PRJ-07).

Priority Requirements Verified:
1. Ingest datasets A, B, C, D into a fresh test session. Assert entity count == 10.
2. Ingest dataset E into the same session. Assert:
   - Total Master Entities == 11.
   - Aarav Patel merged (contains phone 9876510001 and username aarav_p).
   - Cross-source links > 0.
   - Devendra Verma exists as entity #11.
3. Report back with terminal confirmation of test results.
"""

import sys
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure root repository directory is on sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from backend.main import app
from backend.database import SessionLocal
from backend.services.ingestion import ingest_source

client = TestClient(app)
DATA_DIR = BASE_DIR / "data"


def test_resolution_counts_and_incremental_merging():
    """
    Executes the exact mathematical verification protocol:
    1. Ingest datasets A, B, C, D -> Assert Master Entities == 10.
    2. Ingest dataset E -> Assert Master Entities == 11, cross-source links > 0,
       Aarav Patel merged, and Devendra Verma isolated as entity #11.
    """
    db = SessionLocal()
    ws_id = None

    try:
        # Step 1: Initialize fresh isolated workspace session
        res_ws = client.post(
            "/api/workspaces",
            json={
                "name": "Automated Resolution Counts Protocol",
                "description": "Verification of DSU clustering, incremental merging, and metrics"
            }
        )
        assert res_ws.status_code == 201, f"Failed to create workspace: {res_ws.text}"
        ws_id = res_ws.json()["id"]
        print(f"\n[+] Created active workspace session: {ws_id}")

        # Baseline Datasets A, B, C, D
        baseline_datasets = [
            "dataset_A_customers.csv",
            "dataset_B_contacts.csv",
            "dataset_C_business.csv",
            "dataset_D_members.csv"
        ]

        print("\n--- Phase 1: Ingesting Baseline Datasets (A, B, C, D) ---")
        for fname in baseline_datasets:
            fpath = DATA_DIR / fname
            assert fpath.exists(), f"Missing dataset file: {fpath}"

            with open(fpath, "rb") as f:
                res_up = client.post(
                    "/api/sources/upload",
                    data={"source_type": "CSV", "workspace_id": ws_id},
                    files={"file": (fname, f, "text/csv")}
                )
            assert res_up.status_code == 201, f"Upload failed for {fname}: {res_up.text}"
            up_data = res_up.json()
            source_id = up_data["source_id"]

            # Confirm auto-suggested column mappings
            confirmed_mappings = {
                col: {
                    "canonical_field": meta["canonical_field"],
                    "confidence_score": meta.get("confidence", 0.95),
                    "is_identifier": meta.get("is_identifier", False)
                }
                for col, meta in up_data["suggested_mappings"].items()
            }
            res_conf = client.post(
                f"/api/sources/{source_id}/confirm-mapping",
                json={"mappings": confirmed_mappings}
            )
            assert res_conf.status_code == 202, f"Confirm mapping failed for {fname}: {res_conf.text}"

            # Ingest synchronously into database
            ingest_res = ingest_source(source_id=source_id, db=db)
            print(f"  -> Ingested {fname} (source_id={source_id}, records={ingest_res['record_count']})")

        # Execute Session-Wide DSU Resolution
        res_resolve = client.post(f"/api/workspaces/{ws_id}/resolve")
        assert res_resolve.status_code == 200, f"Resolution failed: {res_resolve.text}"

        # Fetch baseline telemetry
        res_stats = client.get(f"/api/workspaces/{ws_id}/stats")
        assert res_stats.status_code == 200
        stats_baseline = res_stats.json()

        print(f"\n[Telemetry Baseline A+B+C+D]:")
        print(f"  • Master Entities Discovered: {stats_baseline['master_entities']}")
        print(f"  • Cross-Source Multi-Hop Links: {stats_baseline['links_discovered']}")
        print(f"  • Total Attributes Indexed: {stats_baseline['total_attributes_indexed']}")
        print(f"  • Total Sources Ingested: {stats_baseline['total_sources']}")

        # ASSERTION 1: Exactly 10 Master Entities
        assert stats_baseline["master_entities"] == 10, (
            f"Assertion Failed: Expected exactly 10 Master Entities for A+B+C+D, got {stats_baseline['master_entities']}"
        )
        print("  [PASS] Assertion 1: Total Master Entities for A+B+C+D == 10.")

        # Step 2: Incremental Ingestion of Dataset E
        print("\n--- Phase 2: Ingesting Incremental Dataset E (Updates & New Identity) ---")
        fname_e = "dataset_E_updates.csv"
        fpath_e = DATA_DIR / fname_e
        if not fpath_e.exists():
            fpath_e = DATA_DIR / "dataset_E.csv"
        assert fpath_e.exists(), f"Missing Dataset E file at: {fpath_e}"

        with open(fpath_e, "rb") as f:
            res_up_e = client.post(
                "/api/sources/upload",
                data={"source_type": "CSV", "workspace_id": ws_id},
                files={"file": (fname_e, f, "text/csv")}
            )
        assert res_up_e.status_code == 201, f"Upload failed for {fname_e}: {res_up_e.text}"
        up_data_e = res_up_e.json()
        source_id_e = up_data_e["source_id"]

        confirmed_mappings_e = {
            col: {
                "canonical_field": meta["canonical_field"],
                "confidence_score": meta.get("confidence", 0.95),
                "is_identifier": meta.get("is_identifier", False)
            }
            for col, meta in up_data_e["suggested_mappings"].items()
        }
        res_conf_e = client.post(
            f"/api/sources/{source_id_e}/confirm-mapping",
            json={"mappings": confirmed_mappings_e}
        )
        assert res_conf_e.status_code == 202

        ingest_res_e = ingest_source(source_id=source_id_e, db=db)
        print(f"  -> Ingested {fname_e} (source_id={source_id_e}, records={ingest_res_e['record_count']})")

        # Re-run Session-Wide DSU Resolution Pass
        res_resolve_e = client.post(f"/api/workspaces/{ws_id}/resolve")
        assert res_resolve_e.status_code == 200

        # Fetch post-E telemetry
        res_stats_e = client.get(f"/api/workspaces/{ws_id}/stats")
        assert res_stats_e.status_code == 200
        stats_e = res_stats_e.json()

        print(f"\n[Telemetry Combined A+B+C+D+E]:")
        print(f"  • Master Entities Discovered: {stats_e['master_entities']}")
        print(f"  • Cross-Source Multi-Hop Links: {stats_e['links_discovered']}")
        print(f"  • Total Attributes Indexed: {stats_e['total_attributes_indexed']}")
        print(f"  • Total Sources Ingested: {stats_e['total_sources']}")

        # ASSERTION 2A: Total Master Entities across A+B+C+D+E == 11
        assert stats_e["master_entities"] == 11, (
            f"Assertion Failed: Expected exactly 11 Master Entities across A+B+C+D+E, got {stats_e['master_entities']}"
        )
        print("  [PASS] Assertion 2A: Total Master Entities across A+B+C+D+E == 11 (10 baseline + 1 new).")

        # ASSERTION 2B: Cross-Source Multi-Hop Links > 0
        assert stats_e["links_discovered"] > 0, (
            f"Assertion Failed: Expected links_discovered > 0, got {stats_e['links_discovered']}"
        )
        print(f"  [PASS] Assertion 2B: Cross-source multi-hop links formed == {stats_e['links_discovered']} (> 0).")

        # ASSERTION 2C: Aarav Patel merged across silos with phone 9876510001 and username aarav_p
        res_search_aarav = client.get(
            f"/api/entities/search?field=name&value=Aarav Patel&workspace_id={ws_id}"
        )
        assert res_search_aarav.status_code == 200, f"Search failed: {res_search_aarav.text}"
        aarav_data = res_search_aarav.json()
        aarav_entity = aarav_data["entity"]
        aarav_auth = aarav_entity["authoritative_profile"]
        aarav_consolidated = aarav_entity["consolidated_attributes"]
        aarav_lineage = aarav_data.get("lineage", [])

        # Check phone and username
        all_phones = aarav_consolidated.get("phone", []) + [aarav_auth.get("phone", "")]
        all_usernames = aarav_consolidated.get("username", []) + [aarav_auth.get("username", "")]

        assert any("9876510001" in str(p) for p in all_phones), f"Aarav phone 9876510001 not found: {all_phones}"
        assert any("aarav_p" in str(u).lower() for u in all_usernames), f"Aarav username aarav_p not found: {all_usernames}"

        # Check cross-dataset lineage includes dataset E and baseline datasets
        source_names_linked = {l.get("source_name", "") for l in aarav_lineage}
        print(f"  [Lineage] Aarav Patel linked datasets: {source_names_linked}")
        assert len(source_names_linked) >= 2, f"Expected Aarav to span at least 2 datasets, got {source_names_linked}"
        print("  [PASS] Assertion 2C: Aarav Patel merged with phone '9876510001' and username 'aarav_p'.")

        # ASSERTION 2D: Devendra Verma exists as entity #11
        res_search_dev = client.get(
            f"/api/entities/search?field=name&value=Devendra Verma&workspace_id={ws_id}"
        )
        assert res_search_dev.status_code == 200, f"Search for Devendra Verma failed: {res_search_dev.text}"
        dev_data = res_search_dev.json()
        dev_entity = dev_data["entity"]
        assert "Devendra" in dev_entity["canonical_name"], f"Unexpected canonical name: {dev_entity['canonical_name']}"
        dev_auth = dev_entity["authoritative_profile"]
        assert dev_auth.get("email") == "devendra.verma@example.com"
        assert dev_auth.get("username") == "devendra_v"
        print(f"  [PASS] Assertion 2D: Devendra Verma verified as entity #11 (ID: {dev_entity['id']}).")

        print("\n======================================================================")
        print("   ALL MATHEMATICAL VERIFICATION TESTS PASSED SUCCESSFULLY (100%)    ")
        print("======================================================================\n")

    finally:
        if ws_id:
            client.delete(f"/api/workspaces/{ws_id}")
            print(f"[+] Cleaned up test workspace {ws_id}")
        db.close()


if __name__ == "__main__":
    test_resolution_counts_and_incremental_merging()
