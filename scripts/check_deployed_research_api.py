#!/usr/bin/env python3
"""Monitor TMRDS's *independently deployed* public research service.

No patient data, no 22-source fan-out, no upstream API polling from this job.
Source health is audited by the separate scheduled source-governance workflow.
"""
from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from urllib import error, request

BASE_URL = "https://tmrds-public-evidence-api.onrender.com"
USER_AGENT = "TMRDS-public-health-audit/1.0"
MAX_BYTES = 131072


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch_json(path: str, *, timeout: float = 55) -> dict:
    if not path.startswith("/") or "//" in path or any(x in path for x in ("@", "#", "..")):
        raise ValueError("Health check URL must be a fixed same-origin path")
    url = BASE_URL + path
    req = request.Request(url, headers={"Accept": "application/json", "User-Agent": USER_AGENT})
    opener = request.build_opener(NoRedirect)
    with opener.open(req, timeout=timeout) as response:
        if response.status != 200 or response.geturl() != url:
            raise ValueError("Unexpected public API HTTP status or redirect")
        ctype = response.headers.get("Content-Type", "").lower()
        if "application/json" not in ctype:
            raise ValueError("Health probe did not return JSON")
        if int(response.headers.get("Content-Length") or 0) > MAX_BYTES:
            raise ValueError("JSON response exceeded read limit")
        body = response.read(MAX_BYTES + 1)
        if len(body) > MAX_BYTES:
            raise ValueError("JSON response exceeded read limit")
    data = json.loads(body)
    if not isinstance(data, dict):
        raise ValueError("Unexpected JSON schema")
    return data


def assess_payloads(payloads: dict[str, dict]) -> dict:
    ready = payloads["/health/ready"]
    if ready.get("status") != "ready":
        raise ValueError("Public research service is not ready")
    if ready.get("external_sources_verified") is not False:
        raise ValueError("Process readiness must not claim upstream validation")
    config = payloads["/backend-config.json"]
    if config.get("api_mode") != "same-origin":
        raise ValueError("Python backend not enabled on same-origin service")
    records = payloads["/api/v1/research/medical-projects?category=genomics"]
    if records.get("clinical_promotion_allowed") is not False:
        raise ValueError("Research catalog cannot imply clinical promotion")
    if records.get("all_platforms_installed") is not False:
        raise ValueError("Catalog cannot claim all software installed")
    if records.get("license_approvals_completed") is not False:
        raise ValueError("License approvals must be separately reviewed")
    if not isinstance(records.get("count"), int) or records["count"] < 10:
        raise ValueError("Genomic resource catalog incomplete")
    formats = payloads["/api/v1/research/file-format-capabilities"]
    if (formats.get("mode") != "local_synthetic_only" or
            formats.get("patient_data_ingestion_enabled") is not False or
            formats.get("public_patient_upload_enabled") is not False):
        raise ValueError("A prohibited patient data route or format status was advertised")
    alphafold = payloads["/api/v1/research/alphafold3-status"]
    if (alphafold.get("status") != "not_configured" or
            alphafold.get("model_parameters_bundled") is not False or
            alphafold.get("inference_submitted") is not False):
        raise ValueError("Unsupported AlphaFold 3 activation claim")
    return {
        "status": "research_service_ready",
        "api_mode": "same-origin",
        "source_health_not_verified": True,
        "genomics_reference_count": records["count"],
        "clinical_data_routes_enabled": False,
        "local_synthetic_only": True,
        "alphafold3_inference_enabled": False,
    }


def run_smoke() -> dict:
    paths = (
        "/health/ready",
        "/backend-config.json",
        "/api/v1/research/medical-projects?category=genomics",
        "/api/v1/research/file-format-capabilities",
        "/api/v1/research/alphafold3-status",
    )
    payloads = {}
    for index, path in enumerate(paths):
        attempts = 2 if index == 0 else 1
        for attempt in range(attempts):
            try:
                payloads[path] = fetch_json(path)
                break
            except (OSError, ValueError, json.JSONDecodeError, error.HTTPError):
                if attempt + 1 == attempts:
                    raise
                # Free-plan services may need to wake up. No asynchronous job is implied.
                time.sleep(8)
    result = assess_payloads(payloads)
    receipt = {
        "schema_version": "1.0",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "source_url": BASE_URL,
        "scope": "HTTPS process and nonclinical contract; excludes external source health",
        **result,
    }
    canonical = json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode()
    receipt["sha256"] = hashlib.sha256(canonical).hexdigest()
    receipt["sha256_scope"] = "receipt_fields_before_hash_not_raw_remote_responses"
    return receipt


def main() -> int:
    try:
        receipt = run_smoke()
    except Exception as exc:
        # No response body or exception URL (which might expose a query) in CI logs.
        print(json.dumps({"status": "research_service_unverified", "reason": type(exc).__name__}))
        return 1
    with open("public-api-smoke-receipt.json", "w", encoding="utf8") as output:
        json.dump(receipt, output, indent=2, sort_keys=True)
        output.write("\n")
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
