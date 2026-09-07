"""Typed domain contracts for the TMRDS governed biomedical evidence graph."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EntityType(str, Enum):
    DISEASE = "Disease"
    PHENOTYPE = "Phenotype"
    GENE = "Gene"
    VARIANT = "Variant"
    PROTEIN = "Protein"
    PATHWAY = "Pathway"
    COMPOUND = "Compound"
    DRUG = "Drug"
    CLINICAL_TRIAL = "ClinicalTrial"
    PUBLICATION = "Publication"
    PREPRINT = "Preprint"
    IMAGING_DATASET = "ImagingDataset"
    RESEARCH_DATASET = "ResearchDataset"
    STUDY = "Study"
    ORGANIZATION = "Organization"
    INVESTIGATOR = "Investigator"
    BIOMARKER = "Biomarker"
    ANATOMICAL_STRUCTURE = "AnatomicalStructure"
    CELL_TYPE = "CellType"
    TISSUE = "Tissue"
    POPULATION = "Population"
    DRUG_TARGET = "DrugTarget"
    ADVERSE_EVENT = "AdverseEvent"


class EvidenceType(str, Enum):
    RANDOMIZED_TRIAL = "randomized_trial"
    CLINICAL_TRIAL = "clinical_trial"
    COHORT = "cohort"
    CASE_CONTROL = "case_control"
    OBSERVATIONAL = "observational"
    IN_VITRO = "in_vitro"
    ANIMAL = "animal"
    COMPUTATIONAL = "computational"
    CURATED_DATABASE = "curated_database"
    REGULATORY = "regulatory"
    SYSTEMATIC_REVIEW = "systematic_review"
    META_ANALYSIS = "meta_analysis"
    UNKNOWN = "unknown"


class Directness(str, Enum):
    DIRECT_HUMAN = "direct_human"
    INDIRECT_HUMAN = "indirect_human"
    PRECLINICAL = "preclinical"
    COMPUTATIONAL = "computational"
    UNKNOWN = "unknown"


class ReplicationState(str, Enum):
    SINGLE = "single_observation"
    REPLICATED = "replicated"
    INDEPENDENTLY_REPLICATED = "independently_replicated"
    UNKNOWN = "unknown"


class HumanReviewState(str, Enum):
    UNREVIEWED = "unreviewed"
    REVIEWED = "reviewed"
    ACCEPTED_FOR_RESEARCH = "accepted_for_research"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class ConflictState(str, Enum):
    OPEN = "OPEN"
    MIXED = "MIXED"
    RESOLVED_BY_SOURCE = "RESOLVED_BY_SOURCE"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"


class ConflictType(str, Enum):
    OPPOSITE_EFFECT = "opposite_effect"
    POSITIVE_VS_NULL = "positive_vs_null"
    INCOMPATIBLE_CLASSIFICATION = "incompatible_classification"
    SOURCE_VERSION_DISAGREEMENT = "source_version_disagreement"
    ENTITY_IDENTITY_DISAGREEMENT = "entity_identity_disagreement"
    UNIT_MISMATCH = "unit_mismatch"
    SUPERSESSION = "supersession"


class SourceRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(min_length=2, max_length=128)
    provider: str = Field(min_length=1, max_length=256)
    name: str = Field(min_length=1, max_length=256)
    endpoint: str | None = None
    protocol: str = Field(default="https", min_length=1, max_length=64)
    authority_class: str = Field(min_length=1, max_length=64)
    license: str = Field(min_length=1, max_length=256)
    access_policy: str = Field(min_length=1, max_length=64)
    allowed_use: str = Field(min_length=1, max_length=512)
    update_frequency: str | None = None
    version_strategy: str | None = None
    schema_version: str | None = None
    identifier_namespaces: list[str] = Field(default_factory=list)
    entity_types: list[EntityType] = Field(default_factory=list)


class CanonicalEntity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity_id: str = Field(min_length=3, max_length=256)
    entity_type: EntityType
    label: str = Field(min_length=1, max_length=1024)
    normalized_label: str = Field(min_length=1, max_length=1024)
    identifiers: dict[str, str] = Field(default_factory=dict)
    synonyms: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)
    properties: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class EvidenceAssertion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assertion_id: str = Field(min_length=3, max_length=256)
    subject_entity_id: str = Field(min_length=3, max_length=256)
    predicate: str = Field(min_length=1, max_length=128)
    object_entity_id: str = Field(min_length=3, max_length=256)
    source_id: str = Field(min_length=2, max_length=128)
    source_record_id: str = Field(min_length=1, max_length=512)
    source_uri: str | None = None
    published_at: datetime | None = None
    retrieved_at: datetime
    source_version: str | None = None
    adapter_version: str = Field(min_length=1, max_length=128)
    normalization_version: str = Field(min_length=1, max_length=128)
    evidence_type: EvidenceType
    evidence_grade: str = Field(min_length=1, max_length=64)
    directness: Directness
    replication_state: ReplicationState
    effect_direction: str | None = None
    effect_measure: float | None = None
    effect_units: str | None = None
    population_context: str | None = None
    methodology: str | None = None
    content_hash: str = Field(min_length=64, max_length=64)
    supersedes_assertion_id: str | None = None
    conflict_group_id: str | None = None
    human_review_state: HumanReviewState = HumanReviewState.UNREVIEWED

    @field_validator("content_hash")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        int(value, 16)
        return value.lower()


class EvidenceAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assertion_id: str
    source_authority: str
    evidence_type: EvidenceType
    directness: Directness
    replication_state: ReplicationState
    methodological_quality: str | None = None
    recency_class: str | None = None
    graph_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    reviewer_id: str | None = None
    assessed_at: datetime


class ConflictGroup(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conflict_group_id: str = Field(min_length=3, max_length=256)
    conflict_type: ConflictType
    assertion_ids: list[str] = Field(min_length=2)
    affected_entity_ids: list[str] = Field(min_length=1)
    detected_at: datetime
    comparison_basis: str = Field(min_length=1, max_length=2048)
    state: ConflictState
    resolution_provenance: str | None = None


class IngestionObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str
    source_record_id: str
    retrieved_at: datetime
    source_version: str | None = None
    request_parameters: dict[str, Any] = Field(default_factory=dict)
    raw_payload_hash: str = Field(min_length=64, max_length=64)
    adapter_version: str
    normalization_version: str


class GraphPathStep(BaseModel):
    subject_entity_id: str
    predicate: str
    object_entity_id: str
    assertion_id: str
    evidence_type: EvidenceType
    evidence_grade: str
    source_id: str
    conflict_group_id: str | None = None
