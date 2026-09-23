"""
Database schema migration script for Workspaces and Ingestion Sessions (PRJ-07).
Safely adds workspace_id foreign keys, indexes, and migrates baseline demo records
into a dedicated 'Baseline Demo Session' workspace.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone
import sqlite3

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from sqlalchemy import inspect, text
from backend.database import engine, SessionLocal, Base
from backend.models import Workspace, Source, AttributeIndex, MasterEntity


BASELINE_WORKSPACE_ID = "baseline-demo-session"
BASELINE_WORKSPACE_NAME = "Baseline Demo Session"
BASELINE_WORKSPACE_DESC = "Migrated baseline demo session containing initial dataset silos."


def run_migration():
    """
    Executes database schema migrations and data backfilling.
    """
    print("[*] Running Database Schema Migration...")

    # 1. Create any tables that don't exist yet (e.g. workspaces)
    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    # 2. Check and add workspace_id column if missing in SQLite
    with engine.begin() as conn:
        for table_name in ["sources", "attribute_indices", "master_entities"]:
            if table_name in existing_tables:
                columns = [col["name"] for col in inspector.get_columns(table_name)]
                if "workspace_id" not in columns:
                    print(f"    [+] Adding missing column 'workspace_id' to table '{table_name}'...")
                    conn.execute(text(
                        f"ALTER TABLE {table_name} ADD COLUMN workspace_id VARCHAR(36) REFERENCES workspaces(id) ON DELETE CASCADE"
                    ))

        # Ensure performance indexes exist
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_sources_workspace_id ON sources (workspace_id)"))
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_attr_workspace_canonical_norm ON attribute_indices (workspace_id, canonical_field, normalized_value)"
            ))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_master_entities_workspace_id ON master_entities (workspace_id)"))
        except Exception as e:
            print(f"    [!] Index creation note: {e}")

    # 3. Check for unassociated demo records and backfill into Baseline Demo Session
    db = SessionLocal()
    try:
        unassigned_sources_count = db.query(Source).filter(Source.workspace_id.is_(None)).count()
        baseline_ws = db.query(Workspace).filter_by(id=BASELINE_WORKSPACE_ID).first()

        if unassigned_sources_count > 0:
            now_utc = datetime.now(timezone.utc)
            if not baseline_ws:
                print(f"    [+] Creating baseline workspace '{BASELINE_WORKSPACE_NAME}' ({BASELINE_WORKSPACE_ID})...")
                baseline_ws = Workspace(
                    id=BASELINE_WORKSPACE_ID,
                    name=BASELINE_WORKSPACE_NAME,
                    description=BASELINE_WORKSPACE_DESC,
                    created_at=now_utc,
                    updated_at=now_utc
                )
                db.add(baseline_ws)
                db.commit()

            print(f"    [+] Associating {unassigned_sources_count} legacy sources to '{BASELINE_WORKSPACE_NAME}'...")
            db.query(Source).filter(Source.workspace_id.is_(None)).update(
                {Source.workspace_id: BASELINE_WORKSPACE_ID},
                synchronize_session=False
            )
            db.query(AttributeIndex).filter(AttributeIndex.workspace_id.is_(None)).update(
                {AttributeIndex.workspace_id: BASELINE_WORKSPACE_ID},
                synchronize_session=False
            )
            db.query(MasterEntity).filter(MasterEntity.workspace_id.is_(None)).update(
                {MasterEntity.workspace_id: BASELINE_WORKSPACE_ID},
                synchronize_session=False
            )
            db.commit()
            print("    [+] Legacy records successfully migrated to Baseline Demo Session.")
        else:
            print("    [+] All existing sources already have assigned workspaces.")

    finally:
        db.close()

    print("[+] Migration completed successfully.")


if __name__ == "__main__":
    run_migration()
