#!/usr/bin/env python3
"""Fetch the Keycloak realm JWKS and print it as TMRDS_SERVICE_JWKS_JSON material.

The existing engines/service_identity.py validator does local JWT validation
with strict iss/aud/exp/scope checks against an explicitly configured JWKS.
Point it at Keycloak:

    python scripts/fetch-keycloak-jwks.py --issuer https://auth.example.com/realms/tmrds > /tmp/jwks.json
    # then set TMRDS_SERVICE_JWKS_JSON to the file contents (or a secret),
    # TMRDS_SERVICE_ISSUER to the same issuer URL,
    # TMRDS_SERVICE_AUDIENCE to tmrds-api

Re-run after any Keycloak key rotation. Research-advisory only. Not SaMD.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch Keycloak realm JWKS as JSON.")
    parser.add_argument("--issuer", required=True, help="Realm issuer URL, e.g. https://auth.example.com/realms/tmrds")
    parser.add_argument("--timeout", type=int, default=20)
    args = parser.parse_args()

    certs_url = args.issuer.rstrip("/") + "/protocol/openid-connect/certs"
    request = urllib.request.Request(certs_url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=args.timeout) as response:
            document = json.loads(response.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001 - report transport/parse failure plainly
        print(f"failed to fetch JWKS from {certs_url}: {exc}", file=sys.stderr)
        return 1
    if not isinstance(document, dict) or not document.get("keys"):
        print("JWKS document has no keys", file=sys.stderr)
        return 1
    print(json.dumps(document))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
