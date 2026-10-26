"""The synthetic FHIR connector must never contact a clinical endpoint by default."""
from __future__ import annotations

from copy import deepcopy
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi.testclient import TestClient

from api.main import app
from engines.open_source_medical_core import OpenSourceMedicalCore
from engines.synthetic_fhir_connector import (
    SyntheticFHIRDisabled, SyntheticFHIRUnavailable,
    fetch_synthetic_fhir, synthetic_fhir_config,
)


def sample_observation() -> dict:
    return {
        "resourceType": "Observation", "id": "synthetic-cbc-1",
        "meta": {"tag": [{"system": "urn:tmrds:data-classification", "code": "synthetic"}]},
        "status": "final",
        "code": {"coding": [{"system": "http://loinc.org", "code": "718-7"}]},
        "effectiveDateTime": "2026-05-01T08:00:00Z",
        "valueQuantity": {"value": 13.2, "system": "http://unitsofmeasure.org",
                          "unit": "g/dL", "code": "g/dL"},
    }


def configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TMRDS_ENV", "development")
    monkeypatch.setenv("TMRDS_SYNTHETIC_WORKBENCH_ENABLED", "true")
    monkeypatch.setenv("TMRDS_SYNTHETIC_FHIR_FETCH_ENABLED", "true")
    monkeypatch.setenv("TMRDS_SYNTHETIC_FHIR_BASE_URL", "https://synthetic.example.org/fhir")
    monkeypatch.setenv("TMRDS_SYNTHETIC_FHIR_ALLOWED_HOSTS", "synthetic.example.org")
    monkeypatch.setenv("TMRDS_SYNTHETIC_FHIR_TOKEN", "local-fake-token-test-only")
    monkeypatch.setenv("TMRDS_SERVICE_AUTH_REQUIRED", "false")


def test_unconfigured_core_is_not_ready() -> None:
    status = OpenSourceMedicalCore().status()
    assert status["status"] == "NOT_CONNECTED"
    assert status["patient_data_exchange_enabled"] is False
    assert status["institutional_connection_verified"] is False


def test_connector_requires_explicit_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    configured(monkeypatch)
    monkeypatch.setenv("TMRDS_SYNTHETIC_FHIR_FETCH_ENABLED", "false")
    with pytest.raises(SyntheticFHIRDisabled):
        synthetic_fhir_config()


def test_connector_denied_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    configured(monkeypatch)
    monkeypatch.setenv("TMRDS_ENV", "production")
    with pytest.raises(SyntheticFHIRDisabled):
        synthetic_fhir_config()


@pytest.mark.parametrize("host,url", [
    ("synthetic.example.org", "http://synthetic.example.org/fhir"),
    ("other.example.org", "https://synthetic.example.org/fhir"),
    ("synthetic.example.org", "https://user:pass@synthetic.example.org/fhir"),
    ("synthetic.example.org", "https://synthetic.example.org/fhir?access=secret"),
])
def test_host_and_scheme_allowlist(
    monkeypatch: pytest.MonkeyPatch, host: str, url: str,
) -> None:
    configured(monkeypatch)
    monkeypatch.setenv("TMRDS_SYNTHETIC_FHIR_ALLOWED_HOSTS", host)
    monkeypatch.setenv("TMRDS_SYNTHETIC_FHIR_BASE_URL", url)
    with pytest.raises(SyntheticFHIRDisabled):
        synthetic_fhir_config()


def test_connector_needs_test_token(monkeypatch: pytest.MonkeyPatch) -> None:
    configured(monkeypatch)
    monkeypatch.delenv("TMRDS_SYNTHETIC_FHIR_TOKEN")
    with pytest.raises(SyntheticFHIRDisabled):
        synthetic_fhir_config()


@pytest.mark.asyncio
async def test_synthetic_observation_read_maps_to_safe_public_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    configured(monkeypatch)
    observed = []
    def handler(request: httpx.Request) -> httpx.Response:
        observed.append(request)
        return httpx.Response(
            200, json=sample_observation(), headers={"content-type": "application/fhir+json"},
        )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await fetch_synthetic_fhir("Observation", "synthetic-cbc-1", client=client)
    assert len(observed) == 1
    assert observed[0].url.path == "/fhir/Observation/synthetic-cbc-1"
    assert observed[0].headers["Authorization"].split(" ", 1) == ["Bearer", "local-fake-token-test-only"]
    assert result["patient_data_accepted"] is False
    assert result["external_data_transmitted"] is False
    assert result["trends"][0]["measurements"][0]["value"] == 13.2
    assert "subject" not in str(result)


@pytest.mark.asyncio
async def test_connector_rejects_non_synthetic_id(monkeypatch: pytest.MonkeyPatch) -> None:
    configured(monkeypatch)
    async with httpx.AsyncClient(transport=httpx.MockTransport(
        lambda _request: httpx.Response(200, json=sample_observation()),
    )) as client:
        with pytest.raises(ValueError, match="synthetic"):
            await fetch_synthetic_fhir("Observation", "Patient-abc", client=client)
        with pytest.raises(ValueError, match="unsupported"):
            await fetch_synthetic_fhir("Patient", "synthetic-cbc-1", client=client)


@pytest.mark.asyncio
async def test_connector_rejects_untrusted_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    configured(monkeypatch)
    payload = sample_observation()
    payload["subject"] = {"reference": "Patient/real-person"}
    async with httpx.AsyncClient(transport=httpx.MockTransport(
        lambda _request: httpx.Response(
            200, json=payload, headers={"content-type": "application/fhir+json"},
        ),
    )) as client:
        with pytest.raises(SyntheticFHIRUnavailable, match="synthetic schema"):
            await fetch_synthetic_fhir("Observation", "synthetic-cbc-1", client=client)


@pytest.mark.parametrize("code,expected", [(302, "did not return"), (500, "did not return")])
@pytest.mark.asyncio
async def test_connector_denies_redirects_and_errors(
    monkeypatch: pytest.MonkeyPatch, code: int, expected: str,
) -> None:
    configured(monkeypatch)
    async with httpx.AsyncClient(transport=httpx.MockTransport(
        lambda _request: httpx.Response(code, headers={"location": "https://example.com"}),
    )) as client:
        with pytest.raises(SyntheticFHIRUnavailable, match=expected):
            await fetch_synthetic_fhir("Observation", "synthetic-cbc-1", client=client)


@pytest.mark.asyncio
async def test_connector_bounds_response_size(monkeypatch: pytest.MonkeyPatch) -> None:
    configured(monkeypatch)
    async with httpx.AsyncClient(transport=httpx.MockTransport(
        lambda _request: httpx.Response(
            200, content=b"x" * 65537, headers={"content-type": "application/fhir+json"},
        ),
    )) as client:
        with pytest.raises(SyntheticFHIRUnavailable, match="exceeds limit"):
            await fetch_synthetic_fhir("Observation", "synthetic-cbc-1", client=client)


def test_api_test_fhir_read_is_routed(monkeypatch: pytest.MonkeyPatch) -> None:
    configured(monkeypatch)
    from api import medical_workbench_routes
    monkeypatch.setattr(
        medical_workbench_routes, "fetch_synthetic_fhir",
        AsyncMock(return_value={"status": "synthetic-research-demo", "patient_data_accepted": False}),
    )
    client = TestClient(app)
    response = client.get("/api/v1/medical/synthetic/fhir/Observation/synthetic-cbc-1")
    assert response.status_code == 200
    assert response.json()["patient_data_accepted"] is False
