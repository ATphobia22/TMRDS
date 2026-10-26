"""Synthetic contracts; never contact external services."""
from datetime import datetime, timezone
import pytest
from engines.biomedical_provider_registry import PROVIDERS, list_providers, validate_research_record


def example():
    return {"provider_id": "arca", "source_id": "synthetic-source",
            "source_url": "https://example.org/synthetic",
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "summary": "Synthetic public metadata",
            "clinical_promotion_allowed": False, "human_authority_final": True}


def test_discovery_never_claims_remote_connection():
    catalog = list_providers()
    assert len(PROVIDERS) == 12
    assert all(p["status"] == "NOT_CONNECTED" and not p["execution_enabled"] for p in catalog["providers"])
    assert catalog["clinical_promotion_allowed"] is False


def test_domain_filter_and_invalid_domain():
    assert list_providers("clinical_trials")["providers"]
    with pytest.raises(ValueError):
        list_providers("clinical_diagnosis")


def test_valid_record_remains_unreviewed():
    assert validate_research_record(example())["status"] == "UNREVIEWED_SOURCE_RECORD"


@pytest.mark.parametrize("key,value", [
    ("provider_id", "unknown"),
    ("source_id", ""),
    ("source_url", "http://example.org"),
    ("source_url", "https://user:pass@example.org"),
    ("retrieved_at", "not-a-date"),
    ("human_authority_final", False),
    ("clinical_promotion_allowed", True),
])
def test_unsafe_records_rejected(key, value):
    record = example()
    record[key] = value
    with pytest.raises(ValueError):
        validate_research_record(record)


def test_patient_identifiers_not_allowed():
    record = example()
    record["patient_identifier"] = "synthetic-patient"
    with pytest.raises(ValueError):
        validate_research_record(record)
