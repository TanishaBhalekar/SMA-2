"""
Database Initialization Script for Unified Progressive Entity Resolution (PRJ-07).
Creates all database tables defined in SQLAlchemy ORM models.
"""

import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from sqlalchemy import inspect
from backend.database import engine, Base
# Import all models to register with Base.metadata
from backend.models import (
    Workspace,
    Source,
    SourceColumn,
    AttributeIndex,
    MasterEntity,
    EntityAttribute,
    EnrichmentHop,
    RawRecord,
    CanonicalEntity,
    EntityCluster,
    ResolutionJob
)


def init_database():
    """
    Initializes database schema by creating all registered tables.
    """
    print("[*] Connecting to database using engine...")
    print(f"    Database URL: {engine.url}")
    print("[*] Creating all database tables via Base.metadata.create_all...")
    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    print(f"[+] Database initialization successful. ({len(table_names)} tables verified)")
    for table in sorted(table_names):
        cols = [col["name"] for col in inspector.get_columns(table)]
        print(f"    - Table '{table}': {len(cols)} columns -> {', '.join(cols[:5])}{'...' if len(cols) > 5 else ''}")

    return table_names


if __name__ == "__main__":
    init_database()
