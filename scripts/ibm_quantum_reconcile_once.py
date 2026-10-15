"""Run one explicitly enabled, bounded IBM Quantum reconciliation pass."""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from uuid import UUID

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


async def resolve_unknown(
    submission_id: UUID, ibm_job_id: str, operator_id: str, evidence_reference: str
) -> bool:
    ledger = QuantumJobLedger()
    try:
        return await ledger.resolve_unknown_submission(
            submission_id,
            ibm_job_id=ibm_job_id,
            operator_id=operator_id,
            evidence_reference=evidence_reference,
        )
    finally:
        await ledger.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=25, help="number of known jobs to inspect (1-100)")
    parser.add_argument("--resolve-unknown", type=UUID, help="resolve an ambiguous submission with operator evidence")
    parser.add_argument("--ibm-job-id", help="confirmed IBM job ID for operator resolution")
    parser.add_argument("--operator-id", help="operator audit identifier")
    parser.add_argument("--evidence-reference", help="credential-free artifact URI or HTTPS evidence URL")
    args = parser.parse_args()
    if not 1 <= args.limit <= 100:
        parser.error("--limit must be between 1 and 100")

    if args.resolve_unknown is not None:
        if not all((args.ibm_job_id, args.operator_id, args.evidence_reference)):
            parser.error("--resolve-unknown requires --ibm-job-id, --operator-id, and --evidence-reference")
        if os.getenv("TMRDS_QUANTUM_OPERATOR_RESOLUTION_ENABLED") != "true":
            print("operator resolution is disabled; explicit privileged opt-in is required", file=sys.stderr)
            return 2
        try:
            resolved = asyncio.run(resolve_unknown(
                args.resolve_unknown, args.ibm_job_id, args.operator_id, args.evidence_reference
            ))
        except Exception as exc:
            print(f"operator resolution unavailable: {type(exc).__name__}", file=sys.stderr)
            return 2
        if not resolved:
            print("no unresolved submission matched; no ledger state was changed", file=sys.stderr)
            return 2
        print("ambiguous submission resolved and operator evidence recorded")
        return 0

    try:
        return asyncio.run(run_once(args.limit))
    except Exception as exc:
        print(f"reconciliation unavailable: {type(exc).__name__}", file=sys.stderr)
        return 2



if __name__ == "__main__":
    raise SystemExit(main())
