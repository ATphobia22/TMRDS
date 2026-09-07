"""
Real-time operational analytics for TMRDS clinician dashboard.
Tracks request volumes, evidence source latency, specialty routing mix,
and audit activity.
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from typing import Any, Deque, Dict, Optional


class RealtimeAnalytics:
    def __init__(self, window_sec: int = 3600) -> None:
        self.window_sec = window_sec
        self._lock = threading.Lock()
        self._events: Deque[Dict[str, Any]] = deque()
        self._counters: Dict[str, int] = defaultdict(int)
        self._latencies: Dict[str, Deque[float]] = defaultdict(lambda: deque(maxlen=200))
        self._started = time.time()

    def _trim(self) -> None:
        cutoff = time.time() - self.window_sec
        while self._events and self._events[0]["ts"] < cutoff:
            self._events.popleft()

    def record(
        self,
        event_type: str,
        *,
        specialty: Optional[str] = None,
        source: Optional[str] = None,
        latency_ms: Optional[float] = None,
        ok: bool = True,
    ) -> None:
        with self._lock:
            now = time.time()
            self._events.append(
                {
                    "ts": now,
                    "event_type": event_type,
                    "specialty": specialty,
                    "source": source,
                    "latency_ms": latency_ms,
                    "ok": ok,
                }
            )
            self._counters[event_type] += 1
            if source and latency_ms is not None:
                self._latencies[source].append(latency_ms)
            self._trim()

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            self._trim()
            by_specialty: Dict[str, int] = defaultdict(int)
            by_source: Dict[str, int] = defaultdict(int)
            errors = 0
            for e in self._events:
                if e.get("specialty"):
                    by_specialty[e["specialty"]] += 1
                if e.get("source"):
                    by_source[e["source"]] += 1
                if not e.get("ok", True):
                    errors += 1
            latency_summary = {}
            for src, vals in self._latencies.items():
                if not vals:
                    continue
                ordered = sorted(vals)
                latency_summary[src] = {
                    "count": len(ordered),
                    "p50_ms": ordered[len(ordered) // 2],
                    "p95_ms": ordered[int(len(ordered) * 0.95) - 1] if len(ordered) > 1 else ordered[0],
                    "max_ms": ordered[-1],
                }
            return {
                "window_sec": self.window_sec,
                "uptime_sec": round(time.time() - self._started, 1),
                "events_in_window": len(self._events),
                "counters": dict(self._counters),
                "by_specialty": dict(by_specialty),
                "by_source": dict(by_source),
                "errors_in_window": errors,
                "latency": latency_summary,
                "status": "LIVE",
            }

    def status(self) -> Dict[str, Any]:
        snap = self.snapshot()
        return {"node": "RealtimeAnalytics", **snap}
