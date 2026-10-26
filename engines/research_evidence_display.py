"""Research-only evidence display contracts shared by patient and clinician interfaces.

No model-derived confidence scores, clinical approval or treatment recommendations.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ResearchResultStatus(str, Enum):
    SUPPORTED = "supported"
    CONFLICTING = "conflicting"
    INSUFFICIENT = "insufficient"
    UNAVAILABLE = "unavailable"


class ResearchReviewStatus(str, Enum):
    PENDING = "pending"
    REVIEWED = "reviewed"


class EvidenceCitation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(min_length=1, max_length=256)
    title: str = Field(min_length=1, max_length=512)
    retrieved_at: datetime
    published_at: datetime | None = None
    doi: str | None = Field(default=None, max_length=256)


class ResearchEvidenceDisplay(BaseModel):
    """Validated display payload; never a clinical authorization record."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0"
    research_question: str = Field(min_length=3, max_length=2000)
    status: ResearchResultStatus
    summary: str = Field(min_length=1, max_length=4000)
    citations: list[EvidenceCitation] = Field(default_factory=list)
    evidence_assertion_ids: list[str] = Field(default_factory=list)
    model_version: str = Field(min_length=1, max_length=128)
    limitations: list[str] = Field(min_length=1)
    uncertainty_basis: str = Field(min_length=1, max_length=2000)
    review_status: ResearchReviewStatus = ResearchReviewStatus.PENDING
    human_authority_final: bool = True
    research_advisory: bool = True
    clinical_promotion_allowed: bool = False

    @model_validator(mode="after")
    def enforce_research_boundary(self) -> "ResearchEvidenceDisplay":
        if not self.human_authority_final or not self.research_advisory or self.clinical_promotion_allowed:
            raise ValueError("research-only human-authority boundary must remain enforced")
        if self.status in {ResearchResultStatus.SUPPORTED, ResearchResultStatus.CONFLICTING}:
            if not self.citations or not self.evidence_assertion_ids:
                raise ValueError("supported or conflicting research claims require cited provenance")
        if self.status in {ResearchResultStatus.INSUFFICIENT, ResearchResultStatus.UNAVAILABLE}:
            if self.review_status == ResearchReviewStatus.REVIEWED:
                raise ValueError("insufficient or unavailable evidence cannot be marked reviewed")
        return self
