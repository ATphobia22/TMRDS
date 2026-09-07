"""
Evidence Ledger for TMRDS.
Immutable content_hash provenance for every clinical / research record.
Aligned with Tri-State Systems Manager evidence-before-inference doctrine.
"""
from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Dict, List, Optional


class EvidenceLedger:
    """Append-only evidence store. Human authority remains final."""

    def __init__(self) -> None:
        self._entries: List[Dict[str, Any]] = []

    @staticmethod
    def _hash(payload: Any) -> str:
        raw = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def append(
        self,
        record_type: str,
        payload: Dict[str, Any],
        source: str,
        verification_status: str = "UNVERIFIED",
    ) -> Dict[str, Any]:
        if verification_status not in (
            "UNVERIFIED",
            "MACHINE_CHECKED",
            "HUMAN_REVIEWED",
            "AUTHORITY_ACCEPTED",
        ):
            raise ValueError("Invalid verification_status")

        content_hash = self._hash(payload)
        entry = {
            "id": f"ev-{len(self._entries)+1:08d}",
            "record_type": record_type,
            "content_hash": content_hash,
            "source": source,
            "verification_status": verification_status,
            "timestamp_unix": time.time(),
            "payload_summary": {k: payload[k] for k in list(payload)[:8]},
        }
        self._entries.append(entry)
        return entry

    def verify(self, entry_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        for e in self._entries:
            if e["id"] == entry_id:
                expected = e["content_hash"]
                actual = self._hash(payload)
                return {
                    "id": entry_id,
                    "match": expected == actual,
                    "expected_hash": expected,
                    "actual_hash": actual,
                    "verification_status": e["verification_status"],
                }
        return {"id": entry_id, "match": False, "error": "NOT_FOUND"}

    def promote(self, entry_id: str, new_status: str, reviewer: str) -> Dict[str, Any]:
        for e in self._entries:
            if e["id"] == entry_id:
                e["verification_status"] = new_status
                e["reviewed_by"] = reviewer
                e["reviewed_at"] = time.time()
                return e
        return {"error": "NOT_FOUND", "id": entry_id}

    def list_entries(self, record_type: Optional[str] = None) -> List[Dict[str, Any]]:
        if record_type is None:
            return list(self._entries)
        return [e for e in self._entries if e["record_type"] == record_type]

    def status(self) -> Dict[str, Any]:
        return {
            "node": "EvidenceLedger",
            "entry_count": len(self._entries),
            "doctrine": "evidence_before_inference",
            "human_authority_final": True,
            "status": "READY",
        }
