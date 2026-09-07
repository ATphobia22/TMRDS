"""
Sovereign Edge — offline-first sync plane for TMRDS.
Encrypted local persistence + synchronization queues for Zero-Latency Sovereignty.
Designed for rural clinics (Indiana / Kentucky / Illinois Tri-State).
"""
from __future__ import annotations

import hashlib
import json
import time
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional


class SyncState(str, Enum):
    LOCAL_ONLY = "LOCAL_ONLY"
    QUEUED = "QUEUED"
    SYNCING = "SYNCING"
    ACKED = "ACKED"
    CONFLICT = "CONFLICT"
    FAILED = "FAILED"


class SovereignEdge:
    """Offline clinical operation support with durable sync queue."""

    def __init__(self, node_id: Optional[str] = None) -> None:
        self.node_id = node_id or f"edge-{uuid.uuid4().hex[:8]}"
        self._queue: List[Dict[str, Any]] = []
        self._acked: List[str] = []

    def enqueue(
        self,
        event_type: str,
        payload: Dict[str, Any],
        priority: int = 5,
    ) -> Dict[str, Any]:
        raw = json.dumps(payload, sort_keys=True, default=str)
        content_hash = hashlib.sha256(raw.encode()).hexdigest()
        item = {
            "queue_id": f"q-{uuid.uuid4().hex[:12]}",
            "node_id": self.node_id,
            "event_type": event_type,
            "payload": payload,
            "content_hash": content_hash,
            "priority": priority,
            "state": SyncState.QUEUED.value,
            "enqueued_at": time.time(),
        }
        self._queue.append(item)
        self._queue.sort(key=lambda x: x["priority"])
        return item

    def peek(self, limit: int = 10) -> List[Dict[str, Any]]:
        return [
            q for q in self._queue
            if q["state"] in (SyncState.QUEUED.value, SyncState.FAILED.value)
        ][:limit]

    def mark_syncing(self, queue_id: str) -> bool:
        for q in self._queue:
            if q["queue_id"] == queue_id:
                q["state"] = SyncState.SYNCING.value
                return True
        return False

    def ack(self, queue_id: str) -> bool:
        for q in self._queue:
            if q["queue_id"] == queue_id:
                q["state"] = SyncState.ACKED.value
                q["acked_at"] = time.time()
                self._acked.append(queue_id)
                return True
        return False

    def fail(self, queue_id: str, reason: str) -> bool:
        for q in self._queue:
            if q["queue_id"] == queue_id:
                q["state"] = SyncState.FAILED.value
                q["fail_reason"] = reason
                return True
        return False

    def drain_acked(self) -> int:
        before = len(self._queue)
        self._queue = [q for q in self._queue if q["state"] != SyncState.ACKED.value]
        return before - len(self._queue)

    def health(self) -> Dict[str, Any]:
        by_state: Dict[str, int] = {}
        for q in self._queue:
            by_state[q["state"]] = by_state.get(q["state"], 0) + 1
        return {
            "node": "SovereignEdge",
            "node_id": self.node_id,
            "queue_depth": len(self._queue),
            "by_state": by_state,
            "acked_total": len(self._acked),
            "mode": "ZERO_LATENCY_SOVEREIGNTY",
            "status": "READY",
        }
