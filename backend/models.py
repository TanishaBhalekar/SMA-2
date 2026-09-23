"""
SQLAlchemy ORM models for Unified Progressive Entity Resolution & Data Repository (PRJ-07).
Implements full data lineage, EAV indexing, progressive enrichment hops, and canonical entities.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean, DateTime,
    ForeignKey, Index, JSON
)
from sqlalchemy.orm import relationship
from backend.database import Base


# ============================================================================
# Operational Silo & Data Lineage Models
# ============================================================================

class Source(Base):
    """
    Ingested operational silo source metadata (CSV, SQL dumps, etc.).
    Tracks status through the ingestion and indexing lifecycle.
    """
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    source_type = Column(String(50), nullable=False)  # 'CSV' or 'SQL'
    file_path = Column(String(500), nullable=False)
    record_count = Column(Integer, default=0)
    status = Column(String(50), default="UPLOADED", index=True)  # 'UPLOADED', 'MAPPED', 'INDEXED', 'FAILED'
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    columns = relationship("SourceColumn", back_populates="source", cascade="all, delete-orphan")
    attributes = relationship("AttributeIndex", back_populates="source", cascade="all, delete-orphan")


class SourceColumn(Base):
    """
    Column metadata mapping raw operational fields to canonical vocabulary.
    """
    __tablename__ = "source_columns"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False, index=True)
    original_name = Column(String(255), nullable=False)
    canonical_field = Column(String(100), nullable=False, index=True)
    confidence_score = Column(Float, default=1.0)
    is_identifier = Column(Boolean, default=False, index=True)

    source = relationship("Source", back_populates="columns")


class AttributeIndex(Base):
    """
    Entity-Attribute-Value (EAV) inverted index across all source records.
    Provides fast O(1) matching via composite index on (canonical_field, normalized_value).
    """
    __tablename__ = "attribute_indices"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False, index=True)
    record_index = Column(Integer, nullable=False, index=True)
    canonical_field = Column(String(100), nullable=False, index=True)
    original_value = Column(Text, nullable=True)
    normalized_value = Column(String(500), nullable=True, index=True)
    is_identifier = Column(Boolean, default=False, index=True)

    source = relationship("Source", back_populates="attributes")

    __table_args__ = (
        Index("ix_attr_canonical_normalized", "canonical_field", "normalized_value"),
    )


# ============================================================================
# Master Entity & Progressive Enrichment Models
# ============================================================================

class MasterEntity(Base):
    """
    Unified golden master entity produced by progressive cross-silo discovery.
    """
    __tablename__ = "master_entities"

    id = Column(String(100), primary_key=True, index=True)  # e.g., 'ENT-1042'
    canonical_name = Column(String(255), nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    attributes = relationship("EntityAttribute", back_populates="entity", cascade="all, delete-orphan")
    hops = relationship("EnrichmentHop", back_populates="entity", cascade="all, delete-orphan", order_by="EnrichmentHop.step_order")


class EntityAttribute(Base):
    """
    Full provenance attribution linking master entity attributes back to raw source records.
    """
    __tablename__ = "entity_attributes"

    id = Column(Integer, primary_key=True, index=True)
    entity_id = Column(String(100), ForeignKey("master_entities.id"), nullable=False, index=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False, index=True)
    record_index = Column(Integer, nullable=False)
    canonical_field = Column(String(100), nullable=False, index=True)
    original_value = Column(Text, nullable=True)
    normalized_value = Column(String(500), nullable=True, index=True)
    is_identifier = Column(Boolean, default=False, index=True)

    entity = relationship("MasterEntity", back_populates="attributes")
    source = relationship("Source")


class EnrichmentHop(Base):
    """
    Audit trail capturing each step of the multi-database progressive discovery pathway.
    """
    __tablename__ = "enrichment_hops"

    id = Column(Integer, primary_key=True, index=True)
    entity_id = Column(String(100), ForeignKey("master_entities.id"), nullable=False, index=True)
    step_order = Column(Integer, nullable=False)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False, index=True)
    matched_field = Column(String(100), nullable=False)
    matched_value = Column(String(500), nullable=False)
    discovered_field = Column(String(100), nullable=False)
    discovered_value = Column(String(500), nullable=False)

    entity = relationship("MasterEntity", back_populates="hops")
    source = relationship("Source")


# ============================================================================
# Staging & Legacy Pipeline Models (Preserved for compatibility)
# ============================================================================

class RawRecord(Base):
    """Ingested staging records awaiting progressive resolution."""
    __tablename__ = "raw_records"

    id = Column(Integer, primary_key=True, index=True)
    source_name = Column(String(100), nullable=False, index=True)
    external_id = Column(String(150), nullable=True, index=True)
    payload = Column(JSON, nullable=False)
    status = Column(String(50), default="pending", index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    clusters = relationship("EntityCluster", back_populates="raw_record")


class CanonicalEntity(Base):
    """Legacy canonical entity representation."""
    __tablename__ = "canonical_entities"

    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String(50), default="person", index=True)
    display_name = Column(String(255), nullable=False, index=True)
    attributes = Column(JSON, nullable=False, default=dict)
    confidence_score = Column(Float, default=1.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    records = relationship("EntityCluster", back_populates="canonical_entity")


class EntityCluster(Base):
    """Junction mapping raw records to canonical entities."""
    __tablename__ = "entity_clusters"

    id = Column(Integer, primary_key=True, index=True)
    canonical_entity_id = Column(Integer, ForeignKey("canonical_entities.id"), nullable=False, index=True)
    raw_record_id = Column(Integer, ForeignKey("raw_records.id"), nullable=False, index=True)
    match_score = Column(Float, nullable=False)
    resolution_method = Column(String(50), default="deterministic")
    review_status = Column(String(50), default="auto_accepted")
    match_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    canonical_entity = relationship("CanonicalEntity", back_populates="records")
    raw_record = relationship("RawRecord", back_populates="clusters")


class ResolutionJob(Base):
    """Batch resolution telemetry."""
    __tablename__ = "resolution_jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_type = Column(String(50), default="batch_progressive")
    status = Column(String(50), default="running")
    total_records = Column(Integer, default=0)
    resolved_count = Column(Integer, default=0)
    ambiguous_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)
