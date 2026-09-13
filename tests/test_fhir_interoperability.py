from __future__ import annotations

import pytest

from engines.fhir_interoperability import FHIRInteroperabilityConfig, FHIRResourceValidator, build_audit_event, build_provenance


def test_valid_r4_resource_passes() -> None:
    validator = FHIRResourceValidator(FHIRInteroperabilityConfig(fhir_version="R4", us_core_version="9.0.0"))
    resource = {
        "resourceType": "Patient",
        "id": "patient-1",
        "meta": {"profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-patient"]},
    }
    assert validator.validate(resource) == []


def test_invalid_resource_type_and_id_are_rejected() -> None:
    validator = FHIRResourceValidator(FHIRInteroperabilityConfig())
    errors = validator.validate({"resourceType": "NotAResource", "id": "bad id"})
    assert any("resourceType" in error for error in errors)
    assert any("id" in error for error in errors)


def test_profile_is_reported_when_requested() -> None:
    validator = FHIRResourceValidator(FHIRInteroperabilityConfig(required_profiles={"Patient": "profile-patient"}))
    errors = validator.validate({"resourceType": "Patient", "id": "p1", "meta": {"profile": []}})
    assert any("required profile" in error for error in errors)


def test_provenance_and_audit_event_are_r4_resources() -> None:
    provenance = build_provenance("Patient/p1", "Service/tmrds", "req-123")
    audit = build_audit_event("Service/tmrds", "Patient/p1", "read", "req-123")
    assert provenance["resourceType"] == "Provenance"
    assert audit["resourceType"] == "AuditEvent"
    assert provenance["target"][0]["reference"] == "Patient/p1"
    assert audit["entity"][0]["what"]["reference"] == "Patient/p1"


def test_configuration_rejects_non_r4() -> None:
    with pytest.raises(ValueError, match="R4"):
        FHIRInteroperabilityConfig(fhir_version="R5")
