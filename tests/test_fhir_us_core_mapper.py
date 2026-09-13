from __future__ import annotations

from engines.fhir_us_core_mapper import FHIRUSCoreMapper


def test_mapper_uses_configured_us_core_base_url(monkeypatch) -> None:
    monkeypatch.setenv("TMRDS_US_CORE_BASE_URL", "https://example.org/fhir/us/core/StructureDefinition")
    resource = FHIRUSCoreMapper().patient("p1")
    assert resource["meta"]["profile"][0] == "https://example.org/fhir/us/core/StructureDefinition/us-core-patient"
