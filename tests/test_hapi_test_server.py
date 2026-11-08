"""Tests for the HAPI FHIR public test server probe + opt-in fetch (mocked) + live smoke (gated).

The public test server was verified live 2026-11-08: GET /baseR4/metadata
returns HTTP 200, CapabilityStatement, fhirVersion 4.0.1, software "HAPI
FHIR Server 8.13.10-SNAPSHOT/6bd250944e/2026-09-25", status active. The
same check found 107,211 Observation resources and ZERO synthetic-* ones —
so a live resource fetch against the public server fails honestly today.
Mocked payloads below reuse the verified live metadata shape. Live smoke
tests are gated by TMRDS_LIVE_SMOKE=1 and fail honestly if the server is
unreachable.
"""
from __future__ import annotations

import os

import httpx
import pytest

from engines.hapi_test_server import (
    HAPI_TEST_SERVER_URL,
    HapiTestServerUnavailable,
    describe,
    hapi_test_server_env_hint,
    verify_test_server,
)
from engines.medical_stack_catalog import medical_stack_catalog
from engines.synthetic_fhir_connector import (
    SyntheticFHIRDisabled,
    fetch_synthetic_fhir,
)

LIVE = os.getenv("TMRDS_LIVE_SMOKE") == "1"
needs_live = pytest.mark.skipif(not LIVE, reason="Live smoke test opt-in only (TMRDS_LIVE_SMOKE=1)")


def _metadata_payload() -> dict:
    # Shape verified live 2026-11-08 (trimmed; full statement is ~2 MB).
    return {
        "resourceType": "CapabilityStatement",
        "status": "active",
        "date": "2026-11-07T23:34:24.315-05:00",
        "fhirVersion": "4.0.1",
        "software": {
            "name": "HAPI FHIR Server",
            "version": "8.13.10-SNAPSHOT/6bd250944e/2026-09-25",
        },
        "kind": "instance",
    }


def _sample_observation() -> dict:
    return {
        "resourceType": "Observation", "id": "synthetic-cbc-1",
        "meta": {"tag": [{"system": "urn:tmrds:data-classification", "code": "synthetic"}]},
        "status": "final",
        "code": {"coding": [{"system": "http://loinc.org", "code": "718-7"}]},
        "effectiveDateTime": "2026-05-01T08:00:00Z",
        "valueQuantity": {"value": 13.2, "system": "http://unitsofmeasure.org",
                          "unit": "g/dL", "code": "g/dL"},
    }


def _hapi_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    """Opt-in env pointing the gated connector at the HAPI test server."""
    hint = hapi_test_server_env_hint()
    for key, value in hint.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("TMRDS_SERVICE_AUTH_REQUIRED", "false")


# ---- metadata probe ----

@pytest.mark.asyncio
async def test_verify_test_server_accepts_verified_metadata() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == f"{HAPI_TEST_SERVER_URL}/metadata"
        assert request.headers["Accept"] == "application/fhir+json"
        assert "Authorization" not in request.headers  # probe sends no credentials
        return httpx.Response(200, json=_metadata_payload(),
                              headers={"content-type": "application/fhir+json"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        identity = await verify_test_server(client)
    assert identity["status"] == "reachable"
    assert identity["server_url"] == HAPI_TEST_SERVER_URL
    assert identity["fhir_version"] == "4.0.1"
    assert identity["software"] == "HAPI FHIR Server"
    assert identity["software_version"] == "8.13.10-SNAPSHOT/6bd250944e/2026-09-25"
    assert identity["synthetic_only"] is True
    assert identity["no_phi"] is True


@pytest.mark.asyncio
async def test_verify_test_server_rejects_wrong_fhir_version() -> None:
    payload = _metadata_payload()
    payload["fhirVersion"] = "5.0.0"
    async with httpx.AsyncClient(transport=httpx.MockTransport(
        lambda _r: httpx.Response(200, json=payload),
    )) as client:
        with pytest.raises(HapiTestServerUnavailable, match="FHIR version"):
            await verify_test_server(client)


@pytest.mark.asyncio
async def test_verify_test_server_rejects_non_capability_statement() -> None:
    async with httpx.AsyncClient(transport=httpx.MockTransport(
        lambda _r: httpx.Response(200, json={"resourceType": "Bundle"}),
    )) as client:
        with pytest.raises(HapiTestServerUnavailable, match="CapabilityStatement"):
            await verify_test_server(client)


@pytest.mark.asyncio
async def test_verify_test_server_rejects_non_200() -> None:
    async with httpx.AsyncClient(transport=httpx.MockTransport(
        lambda _r: httpx.Response(503),
    )) as client:
        with pytest.raises(HapiTestServerUnavailable, match="HTTP 503"):
            await verify_test_server(client)


def test_describe_is_static_and_synthetic_only() -> None:
    info = describe()
    assert info["server_url"] == HAPI_TEST_SERVER_URL
    assert info["synthetic_only"] is True
    assert info["no_phi"] is True
    assert "TMRDS_SYNTHETIC_FHIR_TOKEN" in info["requires_env"]
    assert "placeholder" in info["token_note"]


def test_catalog_lists_hapi_test_server() -> None:
    projects = medical_stack_catalog("interoperability")["projects"]
    entry = next(p for p in projects if p["project_id"] == "hapi_fhir_test_server")
    assert entry["repository"] == HAPI_TEST_SERVER_URL
    assert "Synthetic test data only" in entry["caution"]


# ---- opt-in fetch through the gated connector (mocked HAPI-shaped server) ----

@pytest.mark.asyncio
async def test_hapi_opt_in_fetch_works_with_guards_intact(monkeypatch: pytest.MonkeyPatch) -> None:
    _hapi_configured(monkeypatch)
    observed = []

    def handler(request: httpx.Request) -> httpx.Response:
        observed.append(request)
        assert str(request.url).startswith(HAPI_TEST_SERVER_URL)
        return httpx.Response(
            200, json=_sample_observation(),
            headers={"content-type": "application/fhir+json"},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await fetch_synthetic_fhir("Observation", "synthetic-cbc-1", client=client)
    assert len(observed) == 1
    assert observed[0].url.path == "/baseR4/Observation/synthetic-cbc-1"
    # Placeholder token is sent (connector requires one); it is not a real credential.
    assert observed[0].headers["Authorization"] == "Bearer placeholder-token"
    assert result["patient_data_accepted"] is False
    assert result["trends"][0]["measurements"][0]["value"] == 13.2


def test_hapi_fetch_refused_without_allowlisted_host(monkeypatch: pytest.MonkeyPatch) -> None:
    """The public host is NOT allowlisted by default — the guard stays intact."""
    _hapi_configured(monkeypatch)
    monkeypatch.setenv("TMRDS_SYNTHETIC_FHIR_ALLOWED_HOSTS", "synthetic.example.org")
    from engines.synthetic_fhir_connector import synthetic_fhir_config
    with pytest.raises(SyntheticFHIRDisabled):
        synthetic_fhir_config()


def test_hapi_fetch_refused_without_explicit_opt_in(monkeypatch: pytest.MonkeyPatch) -> None:
    _hapi_configured(monkeypatch)
    monkeypatch.setenv("TMRDS_SYNTHETIC_FHIR_FETCH_ENABLED", "false")
    from engines.synthetic_fhir_connector import synthetic_fhir_config
    with pytest.raises(SyntheticFHIRDisabled):
        synthetic_fhir_config()


# ---- live smoke (gated) ----

@needs_live
@pytest.mark.asyncio
async def test_live_hapi_metadata_is_expected_test_server() -> None:
    identity = await verify_test_server()
    assert identity["status"] == "reachable"
    assert identity["fhir_version"] == "4.0.1"
    assert identity["software"].startswith("HAPI FHIR Server")
