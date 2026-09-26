"""
Pydantic schemas and DTOs for Unified Progressive Entity Resolution & Data Repository (PRJ-07).
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, ConfigDict, Field, field_serializer


def serialize_utc_iso(dt: Optional[Union[datetime, str]]) -> Optional[str]:
    """Ensures created_at/updated_at serializes as an ISO 8601 string with UTC indicator 'Z'."""
    if dt is None:
        return None
    if isinstance(dt, datetime):
        if dt.tzinfo is not None:
            dt_utc = dt.astimezone(timezone.utc)
        else:
            dt_utc = dt.replace(tzinfo=timezone.utc)
        iso = dt_utc.isoformat()
        if iso.endswith("+00:00"):
            return iso[:-6] + "Z"
        return iso if iso.endswith("Z") else iso + "Z"
    if isinstance(dt, str):
        if dt.endswith("+00:00"):
            return dt[:-6] + "Z"
        return dt if dt.endswith("Z") else dt + "Z"
    return str(dt)


# --- Health & System Info Schemas ---
class HealthResponse(BaseModel):
    status: str
    version: str = "1.0.0"
    project: str = "Unified Progressive Entity Resolution & Data Repository (PRJ-07)"
    database_connected: bool
    gemini_configured: bool


# --- Raw Record Schemas ---
class RawRecordBase(BaseModel):
    source_name: str = Field(..., json_schema_extra={"example": "crm_salesforce"})
    external_id: Optional[str] = Field(None, json_schema_extra={"example": "CUST-98432"})
    payload: Dict[str, Any] = Field(..., json_schema_extra={"example": {"name": "Alice Smith", "email": "alice.smith@example.com"}})


class RawRecordCreate(RawRecordBase):
    pass


class RawRecordResponse(RawRecordBase):
    id: int
    status: str
    created_at: Union[datetime, str]

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("created_at")
    def serialize_created_at(self, v):
        return serialize_utc_iso(v)


# --- Canonical Entity Schemas ---
class CanonicalEntityBase(BaseModel):
    entity_type: str = Field("person", json_schema_extra={"example": "person"})
    display_name: str = Field(..., json_schema_extra={"example": "Alice Smith"})
    attributes: Dict[str, Any] = Field(default_factory=dict)
    confidence_score: float = Field(1.0, ge=0.0, le=1.0)


class CanonicalEntityCreate(CanonicalEntityBase):
    pass


class CanonicalEntityResponse(CanonicalEntityBase):
    id: int
    created_at: Union[datetime, str]
    updated_at: Optional[Union[datetime, str]] = None

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("created_at")
    def serialize_created_at(self, v):
        return serialize_utc_iso(v)

    @field_serializer("updated_at")
    def serialize_updated_at(self, v):
        return serialize_utc_iso(v)


# --- Entity Cluster Schemas ---
class EntityClusterResponse(BaseModel):
    id: int
    canonical_entity_id: int
    raw_record_id: int
    match_score: float
    resolution_method: str
    review_status: str
    match_metadata: Optional[Dict[str, Any]] = None
    created_at: Union[datetime, str]

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("created_at")
    def serialize_created_at(self, v):
        return serialize_utc_iso(v)


# --- Resolution Request & Run Schemas ---
class ResolutionRunRequest(BaseModel):
    deterministic_threshold: float = Field(0.95, ge=0.0, le=1.0, description="Exact/Deterministic match cutoff")
    fuzzy_threshold: float = Field(0.80, ge=0.0, le=1.0, description="Fuzzy matching cutoff for candidate grouping")
    use_llm_disambiguation: bool = Field(True, description="Enable Gemini LLM for borderline ambiguous cases")


class ResolutionJobResponse(BaseModel):
    id: int
    job_type: str
    status: str
    total_records: int
    resolved_count: int
    ambiguous_count: int
    created_at: Union[datetime, str]
    completed_at: Optional[Union[datetime, str]] = None

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("created_at")
    def serialize_created_at(self, v):
        return serialize_utc_iso(v)

    @field_serializer("completed_at")
    def serialize_completed_at(self, v):
        return serialize_utc_iso(v)


# --- Source Ingestion & Mapping Schemas ---
class SourceColumnMappingIn(BaseModel):
    canonical_field: str
    confidence_score: float = 1.0
    is_identifier: bool = False


class MappingConfirmationRequest(BaseModel):
    mappings: Dict[str, SourceColumnMappingIn]


class SourceResponse(BaseModel):
    id: int
    workspace_id: Optional[str] = None
    name: str
    source_type: str
    file_path: str
    record_count: int
    status: str
    created_at: Union[datetime, str]

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("created_at")
    def serialize_created_at(self, v):
        return serialize_utc_iso(v)


class SourceStatusResponse(BaseModel):
    source_id: int
    workspace_id: Optional[str] = None
    name: str
    source_type: str
    status: str
    record_count: int
    created_at: Union[datetime, str]

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("created_at")
    def serialize_created_at(self, v):
        return serialize_utc_iso(v)


class UploadResponse(BaseModel):
    source_id: int
    workspace_id: Optional[str] = None
    name: str
    source_type: str
    file_path: str
    status: str
    columns: List[str]
    sample_rows: List[Dict[str, Any]]
    suggested_mappings: Dict[str, Dict[str, Any]]
    column_samples: Optional[Dict[str, List[str]]] = None


# --- Workspace & Ingestion Session Schemas ---
class WorkspaceBase(BaseModel):
    name: str = Field(..., json_schema_extra={"example": "Q3 Enterprise Ingestion Session"})
    description: Optional[str] = Field(None, json_schema_extra={"example": "Consolidated CRM and HR dumps for marketing outreach"})


class WorkspaceCreate(BaseModel):
    name: Optional[str] = Field(None, json_schema_extra={"example": "Session – 2026-09-24 00:54"})
    description: Optional[str] = None


class WorkspaceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class WorkspaceResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    created_at: Union[datetime, str]
    updated_at: Optional[Union[datetime, str]] = None
    total_sources: int = 0
    total_records: int = 0
    total_attributes_indexed: int = 0
    master_entities: int = 0
    links_discovered: int = 0

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("created_at")
    def serialize_created_at(self, v):
        return serialize_utc_iso(v)

    @field_serializer("updated_at")
    def serialize_updated_at(self, v):
        return serialize_utc_iso(v)


class WorkspaceDetailResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    created_at: Union[datetime, str]
    updated_at: Optional[Union[datetime, str]] = None
    sources: List[SourceResponse] = []
    stats: Dict[str, Any] = {}

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("created_at")
    def serialize_created_at(self, v):
        return serialize_utc_iso(v)

    @field_serializer("updated_at")
    def serialize_updated_at(self, v):
        return serialize_utc_iso(v)
