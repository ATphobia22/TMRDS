"""Opt-in, read-only smoke check for the IBM Quantum Compute Service.

Run only after configuring IBM_QUANTUM_API_KEY and IBM_QUANTUM_INSTANCE_CRN:
    IBM_QUANTUM_LIVE_SMOKE=1 python scripts/ibm_quantum_readonly_smoke.py

This script never submits a quantum job and never prints credentials or payload values.
"""
from __future__ import annotations

import os
import sys
from typing import Any

from engines.ibm_quantum_compute import IBMQuantumComputeClient


def describe(payload: dict[str, Any] | list[Any]) -> str:
    """Return structural metadata only; do not print remote payload values."""
    if isinstance(payload, dict):
        return f"object with keys={sorted(str(key) for key in payload.keys())}"
    return f"array with {len(payload)} item(s)"


def main() -> int:
    if os.getenv("IBM_QUANTUM_LIVE_SMOKE") != "1":
        print(
            "Refusing network access: set IBM_QUANTUM_LIVE_SMOKE=1 to opt in.",
            file=sys.stderr,
        )
        return 2

    try:
        with IBMQuantumComputeClient.from_environment() as client:
            instance = client.get_instance_details()
            print(f"Instance endpoint: OK ({describe(instance)})")
            backends = client.list_backends()
            print(f"Backend listing endpoint: OK ({describe(backends)})")
    except (ValueError, RuntimeError) as exc:
        # Adapter errors intentionally avoid embedding credentials or response bodies.
        print(f"IBM Quantum read-only smoke check failed: {exc}", file=sys.stderr)
        return 1

    print("Read-only smoke check passed; no quantum job was submitted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
