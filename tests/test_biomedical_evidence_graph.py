from datetime import datetime, timezone

import pytest

from engines.biomedical_canonicalization import canonicalize_label, canonicalize_record
from engines.biomedical_evidence_models import Directness, EntityType, EvidenceAssertion, EvidenceType, ReplicationState
from engines.evidence_conflict_engine import EvidenceConflictEngine
from engines.evidence_source_registry import default_source_registry


def test_canonicalization_is_deterministic():
    assert canonicalize_label("  BRCA1\tGene ") == "brca1 gene"
    a = canonicalize_record(EntityType.GENE, "BRCA1", [("HGNC", "1100")])
    b = canonicalize_record(EntityType.GENE, "BRCA1", [("HGNC", "1100")])
    assert a.entity_id == b.entity_id
    assert a.identifiers == {"hgnc": "1100"}


def test_source_registry_contains_live_public_sources():
    registry = default_source_registry()
    ids = {source.source_id for source in registry.list()}
    assert {"cdc_cdi", "openneuro", "clinicaltrials_gov", "openfda", "nlm_clinical_tables", "pubmed", "europe_pmc"} <= ids


def _assertion(assertion_id: str, direction: str, grade: str) -> EvidenceAssertion:
    return EvidenceAssertion(
        assertion_id=assertion_id,
        subject_entity_id="disease:x",
        predicate="associated_with",
        object_entity_id="gene:y",
        source_id="pubmed",
        source_record_id=assertion_id,
        retrieved_at=datetime.now(timezone.utc),
        adapter_version="1.0.0",
        normalization_version="1.0.0",
        evidence_type=EvidenceType.CLINICAL_TRIAL,
        evidence_grade=grade,
        directness=Directness.DIRECT_HUMAN,
        replication_state=ReplicationState.UNKNOWN,
        effect_direction=direction,
        content_hash=(assertion_id.ljust(64, "0"))[:64],
    )


def test_conflict_engine_preserves_opposite_effects():
    conflicts = EvidenceConflictEngine().detect([_assertion("a1", "positive", "moderate"), _assertion("a2", "negative", "moderate")])
    assert len(conflicts) == 1
    assert conflicts[0].assertion_ids == ["a1", "a2"]
    assert conflicts[0].state.value == "HUMAN_REVIEW_REQUIRED"


def test_conflict_engine_does_not_compare_different_populations():
    left = _assertion("a1", "positive", "moderate").model_copy(update={"population_context": "adults"})
    right = _assertion("a2", "negative", "moderate").model_copy(update={"population_context": "children"})
    assert EvidenceConflictEngine().detect([left, right]) == []
