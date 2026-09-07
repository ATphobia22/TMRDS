"""Provider-neutral AI governance contracts for TMRDS research workflows.

This module deliberately treats model output as advisory derived material. It
cannot promote a generation to a clinical recommendation or a cure claim.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class GovernanceStatus(str, Enum):
    ACTIVE = "active"
    REVIEW_REQUIRED = "review_required"
    SUSPENDED = "suspended"
    RETIRED = "retired"


class EvidenceEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    generation_id: str = Field(min_length=3, max_length=256)
    model_id: str = Field(min_length=1, max_length=256)
    model_version: str = Field(min_length=1, max_length=128)
    prompt_id: str | None = Field(default=None, max_length=256)
    prompt_version: str | None = Field(default=None, max_length=128)
    dataset_ids: list[str] = Field(default_factory=list)
    retrieved_at: datetime
    evidence_assertion_ids: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)
    uncertainty: float | None = Field(default=None, ge=0.0, le=1.0)
    human_authority_final: bool = True
    research_advisory: bool = True
    governance_status: GovernanceStatus


class ResearchGenerationDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approved_for_research: bool
    requires_human_review: bool
    reason: str


@dataclass(frozen=True)
class RegisteredModel:
    model_id: str
    model_version: str
    purpose: str
    provider: str


class AIGovernanceRegistry:
    """Small in-process registry used by tests and local sovereign-edge mode.

    Production persistence is supplied by the AI-governance PostgreSQL tables.
    """

    def __init__(self) -> None:
        self._models: dict[tuple[str, str], RegisteredModel] = {}

    def register_model(
        self,
        model_id: str,
        model_version: str,
        purpose: str,
        provider: str,
    ) -> RegisteredModel:
        key = (model_id, model_version)
        if key in self._models:
            raise ValueError(f"model version already registered: {model_id}@{model_version}")
        model = RegisteredModel(model_id, model_version, purpose, provider)
        self._models[key] = model
        return model

    def get_model(self, model_id: str, model_version: str) -> RegisteredModel | None:
        return self._models.get((model_id, model_version))


def validate_generation_for_research(
    envelope: EvidenceEnvelope,
) -> ResearchGenerationDecision:
    """Validate minimum governance conditions for a research-only generation."""
    if not envelope.evidence_assertion_ids:
        raise ValueError("generation provenance is required: no evidence assertions supplied")
    if not envelope.human_authority_final:
        raise ValueError("human authority must remain final")
    if not envelope.research_advisory:
        raise ValueError("clinical or autonomous promotion is outside the research engine")
    if envelope.governance_status in {
        GovernanceStatus.SUSPENDED,
        GovernanceStatus.RETIRED,
    }:
        return ResearchGenerationDecision(
            approved_for_research=False,
            requires_human_review=True,
            reason=f"model governance status is {envelope.governance_status.value}",
        )
    return ResearchGenerationDecision(
        approved_for_research=True,
        requires_human_review=True,
        reason="provenance-bearing research output; human review remains mandatory",
    )
