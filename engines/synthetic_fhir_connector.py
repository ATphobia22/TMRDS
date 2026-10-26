"""Opt-in FHIR R4 sandbox client for synthetic resources only.

No real patient/clinical exchange. Intended for an operator-controlled HTTPS
synthetic FHIR test server, not a real HAPI/OpenELIS/OpenEMR production instance.
The public gateway may never accept an arbitrary URL or patient identifier.
"""
from __future__ import annotations

import json
import os
import re
from urllib.parse import urlsplit

import httpx

from engines.medical_research_workbench import (
    synthetic_imaging_index,
    synthetic_lab_trends,
)

_TEST_ID = re.compile(r"synthetic-[A-Za-z0-9.-]{1,64}\Z")
_MAX_BYTES = 65536


class SyntheticFHIRDisabled(RuntimeError):
    pass


class SyntheticFHIRUnavailable(RuntimeError):
    pass


def synthetic_fhir_config() -> tuple[str, str]:
    """Fail closed until a trusted local operator explicitly opts into test retrieval."""
    environment = os.getenv("TMRDS_ENV", "development").casefold().strip()
    enabled = os.getenv("TMRDS_SYNTHETIC_WORKBENCH_ENABLED", "").casefold().strip()
    retrieval = os.getenv("TMRDS_SYNTHETIC_FHIR_FETCH_ENABLED", "").casefold().strip()
    if environment in {"production", "prod"} or enabled != "true" or retrieval != "true":
        raise SyntheticFHIRDisabled("FHIR test connector is not enabled")
    base = os.getenv("TMRDS_SYNTHETIC_FHIR_BASE_URL", "").strip().rstrip("/")
    allowed = {
        host.casefold().strip()
        for host in os.getenv("TMRDS_SYNTHETIC_FHIR_ALLOWED_HOSTS", "").split(",")
        if host.strip()
    }
    token = os.getenv("TMRDS_SYNTHETIC_FHIR_TOKEN", "").strip()
    if len(base) > 512 or any(char.isspace() for char in base):
        raise SyntheticFHIRDisabled("FHIR test endpoint configuration is invalid")
    parsed = urlsplit(base)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.hostname.casefold() not in allowed
            or parsed.username or parsed.password or parsed.query or parsed.fragment):
        raise SyntheticFHIRDisabled("FHIR test endpoint must be an explicitly allowed HTTPS host")
    if not token or len(token) > 2048 or "\n" in token or "\r" in token:
        raise SyntheticFHIRDisabled("FHIR test bearer token is missing or invalid")
    return base, token


async def fetch_synthetic_fhir(
    resource_type: str,
    synthetic_id: str,
    *,
    client: httpx.AsyncClient | None = None,
) -> dict:
    """Fetch a single test record and return strictly sanitized derived data.

    A service owner must ensure the upstream is wholly synthetic. Test tagging
    alone cannot prove de-identification. This transport is disabled in prod.
    """
    base, token = synthetic_fhir_config()
    if resource_type not in {"Observation", "ImagingStudy"}:
        raise ValueError("unsupported synthetic FHIR resource type")
    if not isinstance(synthetic_id, str) or not _TEST_ID.fullmatch(synthetic_id):
        raise ValueError("resource id must be a synthetic fixture id")
    url = f"{base}/{resource_type}/{synthetic_id}"
    headers = {"Accept": "application/fhir+json", "Authorization": "Bearer " + token}

    async def _read(active: httpx.AsyncClient) -> dict:
        try:
            async with active.stream("GET", url, headers=headers, follow_redirects=False) as response:
                if response.status_code != 200:
                    raise SyntheticFHIRUnavailable("synthetic FHIR source did not return a resource")
                mime = response.headers.get("content-type", "").partition(";")[0].strip().lower()
                if mime not in {"application/json", "application/fhir+json"}:
                    raise SyntheticFHIRUnavailable("FHIR source returned unsupported content type")
                chunks = bytearray()
                async for chunk in response.aiter_bytes():
                    if len(chunks) + len(chunk) > _MAX_BYTES:
                        raise SyntheticFHIRUnavailable("synthetic FHIR response exceeds limit")
                    chunks.extend(chunk)
        except httpx.HTTPError as exc:
            raise SyntheticFHIRUnavailable("synthetic FHIR transport unavailable") from exc
        try:
            document = json.loads(chunks)
            if not isinstance(document, dict) or document.get("id") != synthetic_id:
                raise ValueError("wrong synthetic resource identifier")
            if resource_type == "Observation":
                return synthetic_lab_trends([document])
            return synthetic_imaging_index([document])
        except (ValueError, TypeError, KeyError) as exc:
            raise SyntheticFHIRUnavailable("upstream data was rejected by the synthetic schema") from exc

    if client is not None:
        return await _read(client)
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(8.0, connect=3.0),
        verify=True,
        trust_env=False,
        follow_redirects=False,
    ) as owned:
        return await _read(owned)
