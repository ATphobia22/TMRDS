"""Run one explicitly enabled, bounded IBM Quantum reconciliation pass."""
from __future__ import annotations

import argparse
import asyncio
import os
import sys

from engines.ibm_quantum_compute import IBMQuantumComputeClient
from engines.ibm_quantum_job_ledger import QuantumJobLedger
from engines.ibm_quantum_reconciler import IBMQuantumReconciler
from engines.quantum_artifact_store import LocalQuantumArtifactStore


async def run_once(limit: int) -> int:
    if os.getenv("TMRDS_IBM_QUANTUM_RECONCILER_ENABLED") != "true":
        print("reconciliation is disabled; set TMRDS_IBM_QUANTUM_RECONCILER_ENABLED=true", file=sys.stderr)
        return 2
    ledger = QuantumJobLedger()
    client = IBMQuantumComputeClient.from_environment()
    try:
        await ledger.connect()
        store = LocalQuantumArtifactStore()
        reconciler = IBMQuantumReconciler(
            ledger, client, result_sink=store.store, batch_limit=limit
        )
        counts = await reconciler.reconcile_once()
        # Counts are safe operational metadata; never print job IDs or payloads.
        print("reconciliation summary: " + ", ".join(f"{key}={value}" for key, value in sorted(counts.items())))
        return 0 if counts["errors"] == 0 else 1
    finally:
        client.close()
        await ledger.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=25, help="number of known jobs to inspect (1-100)")
    args = parser.parse_args()
    if not 1 <= args.limit <= 100:
        parser.error("--limit must be between 1 and 100")
    try:
        return asyncio.run(run_once(args.limit))
    except (ValueError, RuntimeError) as exc:
        print(f"reconciliation unavailable: {type(exc).__name__}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
