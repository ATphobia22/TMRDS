"""Read-only identity probe for the HAPI FHIR public test server.

The HAPI public test server (https://hapi.fhir.org/baseR4) is a shared,
unauthenticated FHIR R4 test endpoint run by the HAPI project. It holds
synthetic/test data only, offers no SLA, and must never receive PHI or
real patient identifiers.

This module does exactly one thing: fetch the server's CapabilityStatement
(``/metadata``) and verify it is the expected HAPI test server. It fetches
no resources, no patient data, and no Observation/ImagingStudy records.
Resource fetch still goes through the gated synthetic connector
(``engines/synthetic_fhir_connector.py``) with all of its guards intact:
explicit opt-in env flags, HTTPS allowlisted host, bearer token, synthetic-
IDs only, no Patient resource, disabled in production.

Verified live 2026-11-08: GET /baseR4/metadata returns HTTP 200,
CapabilityStatement, fhirVersion 4.0.1, software "HAPI FHIR Server
8.13.10-SNAPSHOT/6bd250944e/2026-09-25", status active. The same check
found 107,211 Observation resources on the server and ZERO resources with
a synthetic-* ID — so a live resource fetch against the public server
fails honestly today (there is nothing synthetic-ID'd to fetch). Do not
create resources on the shared public server to work around that.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

HAPI_TEST_SERVER_URL = "https://hapi.fhir.org/baseR4"

# Env names the operator needs for a resource fetch through the gated
# synthetic connector. The public server ignores Authorization headers, so
# the token below must be a PLACEHOLDER — never a real credential.
REQUIRED_ENV = (
    "TMRDS_SYNTHETIC_WORKBENCH_ENABLED",
    "TMRDS_SYNTHETIC_FHIR_FETCH_ENABLED",
    "TMRDS_SYNTHETIC_FHIR_BASE_URL",
    "TMRDS_SYNTHETIC_FHIR_ALLOWED_HOSTS",
    "TMRDS_SYNTHETIC_FHIR_TOKEN",
)


class HapiTestServerUnavailable(RuntimeError):
    """Raised when the HAPI test server cannot be verified as expected."""


def describe() -> dict[str, Any]:
    """Static opt-in description for the workbench/ops surface. No network."""
    return {
        "server_url": HAPI_TEST_SERVER_URL,
        "fhir_version": "4.0.1",
        "software": "HAPI FHIR Server",
        "synthetic_only": True,
        "no_phi": True,
        "no_sla": True,
        "requires_env": list(REQUIRED_ENV),
        "token_note": (
            "The public test server ignores Authorization headers. Use a "
            "placeholder token for the connector config; never send a real "
            "credential to a public server."
        ),
        "limitations": [
            "Metadata probe only — this module fetches no clinical resources.",
            "No synthetic-* Observation/ImagingStudy resources exist on the "
            "public server (verified 2026-11-08: 0 matches), so a live "
            "resource fetch fails honestly until such resources exist.",
            "Do not create resources on the shared public server.",
            "Resource fetch requires the gated synthetic connector with all "
            "guards intact; this probe does not bypass them.",
        ],
    }


async def verify_test_server(
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    """Verify the public test server identity via /metadata. No PHI involved.

    Returns the verified server identity. Raises HapiTestServerUnavailable
    for transport failures, non-200 responses, or a CapabilityStatement
    that is not the expected HAPI FHIR R4 test server.
    """
    url = f"{HAPI_TEST_SERVER_URL}/metadata"
    headers = {
        "Accept": "application/fhir+json",
        "User-Agent": "TMRDS/1.0 (research evidence discovery; mailto:tmrds@example.org)",
    }

    async def _read(active: httpx.AsyncClient) -> dict[str, Any]:
        try:
            response = await active.get(url, headers=headers, follow_redirects=False)
        except httpx.HTTPError as exc:
            raise HapiTestServerUnavailable("HAPI test server is unreachable") from exc
        if response.status_code != 200:
            raise HapiTestServerUnavailable(
                f"HAPI test server metadata returned HTTP {response.status_code}"
            )
        try:
            document = response.json()
        except ValueError as exc:
            raise HapiTestServerUnavailable("HAPI test server returned non-JSON metadata") from exc
        if not isinstance(document, dict) or document.get("resourceType") != "CapabilityStatement":
            raise HapiTestServerUnavailable("HAPI test server did not return a CapabilityStatement")
        if document.get("fhirVersion") != "4.0.1":
            raise HapiTestServerUnavailable(
                f"HAPI test server reports unexpected FHIR version {document.get('fhirVersion')!r}; expected 4.0.1"
            )
        software = document.get("software") or {}
        name = software.get("name") if isinstance(software, dict) else None
        if not isinstance(name, str) or not name.startswith("HAPI FHIR Server"):
            raise HapiTestServerUnavailable("HAPI test server software is not HAPI FHIR Server")
        return {
            "status": "reachable",
            "server_url": HAPI_TEST_SERVER_URL,
            "fhir_version": document.get("fhirVersion"),
            "software": name,
            "software_version": software.get("version"),
            "server_status": document.get("status"),
            "server_date": document.get("date"),
            "synthetic_only": True,
            "no_phi": True,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
        }

    if client is not None:
        return await _read(client)
    # No trust_env=False here: the probe reads public metadata from a fixed
    # URL through the environment egress proxy, like every other pipeline.
    # (trust_env=False would force a direct connection, which this VM's
    # egress blocks — direct TLS fails with SSL WRONG_VERSION_NUMBER.)
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(30.0, connect=10.0),
        verify=True,
        follow_redirects=False,
    ) as owned:
        return await _read(owned)


def hapi_test_server_env_hint() -> dict[str, str]:
    """Example operator configuration for a fetch via the gated connector.

    Values are examples, not credentials. The token must be a placeholder.
    """
    return {
        "TMRDS_ENV": "development",
        "TMRDS_SYNTHETIC_WORKBENCH_ENABLED": "true",
        "TMRDS_SYNTHETIC_FHIR_FETCH_ENABLED": "true",
        "TMRDS_SYNTHETIC_FHIR_BASE_URL": HAPI_TEST_SERVER_URL,
        "TMRDS_SYNTHETIC_FHIR_ALLOWED_HOSTS": "hapi.fhir.org",
        "TMRDS_SYNTHETIC_FHIR_TOKEN": "placeholder-token",
    }
