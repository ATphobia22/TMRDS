from datetime import datetime, timezone

import pytest

from engines.ai_governance import (
    AIGovernanceRegistry,
    EvidenceEnvelope,
    GovernanceStatus,
    validate_generation_for_research,
)


def test_generation_requires_evidence_and_human_authority():
    envelope = EvidenceEnvelope(
        generation_id="gen-1",
        model_id="model-1",
        model_version="1.0.0",
        retrieved_at=datetime.now(timezone.utc),
        evidence_assertion_ids=["assertion-1"],
        human_authority_final=True,
        research_advisory=True,
        governance_status=GovernanceStatus.REVIEW_REQUIRED,
    )
    assert validate_generation_for_research(envelope).approved_for_research is True


def test_generation_without_provenance_is_rejected():
    envelope = EvidenceEnvelope(
        generation_id="gen-2",
        model_id="model-1",
        model_version="1.0.0",
        retrieved_at=datetime.now(timezone.utc),
        evidence_assertion_ids=[],
        human_authority_final=True,
        research_advisory=True,
        governance_status=GovernanceStatus.REVIEW_REQUIRED,
    )
    with pytest.raises(ValueError, match="provenance"):
        validate_generation_for_research(envelope)


def test_registry_rejects_duplicate_model_version():
    registry = AIGovernanceRegistry()
    registry.register_model("model-1", "1.0.0", "research", "vendor-independent")
    with pytest.raises(ValueError, match="already registered"):
        registry.register_model("model-1", "1.0.0", "research", "vendor-independent")
