"""Safety invariants for shared research evidence display payloads."""
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from engines.research_evidence_display import (
    EvidenceCitation,
    ResearchEvidenceDisplay,
    ResearchResultStatus,
    ResearchReviewStatus,
)


def _payload(**overrides):
    payload = {
        "research_question": "What is known about a synthetic research topic?",
        "status": ResearchResultStatus.SUPPORTED,
        "summary": "Synthetic research-only summary.",
        "citations": [EvidenceCitation(source_id="synthetic-study", title="Synthetic study", retrieved_at=datetime.now(timezone.utc))],
        "evidence_assertion_ids": ["synthetic-assertion"],
        "model_version": "test-v1",
        "limitations": ["Not clinically validated."],
        "uncertainty_basis": "Evidence quality requires independent review.",
    }
    payload.update(overrides)
    return payload


def test_supported_result_requires_citations():
    with pytest.raises(ValidationError, match="cited provenance"):
        ResearchEvidenceDisplay(**_payload(citations=[]))


def test_supported_result_requires_assertion_ids():
    with pytest.raises(ValidationError, match="cited provenance"):
        ResearchEvidenceDisplay(**_payload(evidence_assertion_ids=[]))


def test_conflicting_result_requires_provenance():
    with pytest.raises(ValidationError, match="cited provenance"):
        ResearchEvidenceDisplay(**_payload(status="conflicting", citations=[]))


@pytest.mark.parametrize("status", ["insufficient", "unavailable"])
def test_unavailable_or_insufficient_cannot_be_marked_reviewed(status):
    with pytest.raises(ValidationError, match="cannot be marked reviewed"):
        ResearchEvidenceDisplay(**_payload(status=status, citations=[], review_status="reviewed"))


@pytest.mark.parametrize("field,value", [
    ("human_authority_final", False),
    ("research_advisory", False),
    ("clinical_promotion_allowed", True),
])
def test_clinical_promotion_is_forbidden(field, value):
    with pytest.raises(ValidationError, match="research-only"):
        ResearchEvidenceDisplay(**_payload(**{field: value}))


def test_insufficient_evidence_can_be_displayed_as_pending():
    result = ResearchEvidenceDisplay(**_payload(status="insufficient", citations=[], evidence_assertion_ids=[]))
    assert result.review_status == ResearchReviewStatus.PENDING
    assert result.clinical_promotion_allowed is False


def test_unknown_fields_rejected():
    with pytest.raises(ValidationError):
        ResearchEvidenceDisplay(**_payload(patient_identifier="not-permitted"))
