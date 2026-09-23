"""
Unit tests for data lineage, EAV indexing, and master entity models (PRJ-07).
"""

from datetime import datetime
import pytest
from sqlalchemy import inspect
from backend.database import SessionLocal, engine
from backend.models import (
    Source,
    SourceColumn,
    AttributeIndex,
    MasterEntity,
    EntityAttribute,
    EnrichmentHop
)


def test_models_insertion_and_lineage():
    """Verify end-to-end insertion, foreign key relationships, and queryability."""
    db = SessionLocal()
    import uuid
    test_ent_id = f"ENT-{uuid.uuid4().hex[:6].upper()}"
    try:
        # 1. Insert Source
        source = Source(
            name=f"test_source_{uuid.uuid4().hex[:4]}.csv",
            source_type="CSV",
            file_path="data/hr_db.csv",
            record_count=1200,
            status="INDEXED"
        )
        db.add(source)
        db.commit()
        db.refresh(source)
        assert source.id is not None

        # 2. Insert SourceColumn mapping
        col = SourceColumn(
            source_id=source.id,
            original_name="mobile_number",
            canonical_field="phone",
            confidence_score=0.95,
            is_identifier=True
        )
        db.add(col)

        # 3. Insert AttributeIndex (EAV entry)
        attr = AttributeIndex(
            source_id=source.id,
            record_index=0,
            canonical_field="phone",
            original_value="+91 98765 43210",
            normalized_value="9876543210",
            is_identifier=True
        )
        db.add(attr)

        # 4. Insert MasterEntity
        entity = MasterEntity(
            id=test_ent_id,
            canonical_name="John Doe"
        )
        db.add(entity)
        db.commit()
        db.refresh(entity)

        # 5. Insert EntityAttribute
        ent_attr = EntityAttribute(
            entity_id=entity.id,
            source_id=source.id,
            record_index=0,
            canonical_field="phone",
            original_value="+91 98765 43210",
            normalized_value="9876543210",
            is_identifier=True
        )
        db.add(ent_attr)

        # 6. Insert EnrichmentHop
        hop = EnrichmentHop(
            entity_id=entity.id,
            step_order=1,
            source_id=source.id,
            matched_field="full_name",
            matched_value="John Doe",
            discovered_field="mobile_number",
            discovered_value="9876543210"
        )
        db.add(hop)
        db.commit()

        # Query & Relationship assertions
        queried_entity = db.query(MasterEntity).filter_by(id=test_ent_id).first()
        assert queried_entity is not None
        assert len(queried_entity.attributes) == 1
        assert queried_entity.attributes[0].normalized_value == "9876543210"
        assert len(queried_entity.hops) == 1
        assert queried_entity.hops[0].discovered_field == "mobile_number"

        # EAV composite index lookup
        indexed_lookup = db.query(AttributeIndex).filter_by(
            source_id=source.id,
            canonical_field="phone",
            normalized_value="9876543210"
        ).first()
        assert indexed_lookup is not None
        assert indexed_lookup.record_index == 0

    finally:
        # Clean up test records
        try:
            db.query(EnrichmentHop).filter_by(entity_id=test_ent_id).delete()
            db.query(EntityAttribute).filter_by(entity_id=test_ent_id).delete()
            db.query(MasterEntity).filter_by(id=test_ent_id).delete()
            db.query(AttributeIndex).filter_by(source_id=source.id).delete()
            db.query(SourceColumn).filter_by(source_id=source.id).delete()
            db.query(Source).filter_by(id=source.id).delete()
            db.commit()
        except Exception:
            db.rollback()
        db.close()


def test_composite_index_exists():
    """Verify that ix_attr_canonical_normalized exists on attribute_indices."""
    inspector = inspect(engine)
    indexes = inspector.get_indexes("attribute_indices")
    composite = [idx for idx in indexes if idx["name"] == "ix_attr_canonical_normalized"]
    assert len(composite) == 1
    assert composite[0]["column_names"] == ["canonical_field", "normalized_value"]
