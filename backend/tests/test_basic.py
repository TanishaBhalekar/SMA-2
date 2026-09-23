"""
Basic unit tests for config, database initialization, and resolution components.
"""

import pytest
from backend import config
from backend.database import engine, Base, SessionLocal
from backend.models import RawRecord, CanonicalEntity, EntityCluster, ResolutionJob
from backend.services.resolution_service import ProgressiveResolutionEngine


def test_config_loads():
    """Verify config exposes DATABASE_URL and GEMINI_API_KEY attributes."""
    assert hasattr(config, "DATABASE_URL")
    assert hasattr(config, "GEMINI_API_KEY")
    assert config.DATABASE_URL is not None


def test_database_tables_create():
    """Verify ORM models can create all tables without error."""
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    assert session is not None
    session.close()


def test_resolution_engine_exact_match():
    """Verify deterministic matching on identical emails."""
    engine = ProgressiveResolutionEngine()
    record1 = {"name": "Alice Smith", "email": "alice@example.com"}
    record2 = {"name": "A. Smith", "email": "alice@example.com"}
    result = engine.evaluate_pair(record1, record2)
    assert result["match"] is True
    assert result["method"] == "deterministic"


def test_resolution_engine_fuzzy_match():
    """Verify fuzzy matching on near-identical names."""
    engine = ProgressiveResolutionEngine(exact_threshold=0.90, fuzzy_threshold=0.75, enable_llm=False)
    record1 = {"name": "Robert Downey Jr", "email": "robert1@example.com"}
    record2 = {"name": "Robert Downey", "email": "rdj@different.com"}
    result = engine.evaluate_pair(record1, record2)
    assert result["score"] > 0.70
