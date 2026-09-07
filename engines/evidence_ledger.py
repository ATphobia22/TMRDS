"""
Evidence Ledger — append-only provenance log with content hashes.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


class EvidenceLedger:
    def __init__(self, path: str = "data/research/evidence_ledger.jsonl") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def content_hash(self, payload: Dict[str, Any]) -> str:
        body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(body).hexdigest()

    def append(self, record: Dict[str, Any]) -> Dict[str, Any]:
        entry = dict(record)
        entry["ts"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        entry["content_hash"] = self.content_hash(entry)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, separators=(",", ":")) + "\n")
        return entry

    def recent(self, limit: int = 50) -> List[Dict[str, Any]]:
        if not self.path.exists():
            return []
        lines = self.path.read_text(encoding="utf-8").strip().splitlines()
        out: List[Dict[str, Any]] = []
        for line in lines[-limit:]:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return out

    def status(self) -> Dict[str, Any]:
        return {
            "node": "EvidenceLedger",
            "path": str(self.path),
            "exists": self.path.exists(),
            "status": "READY",
        }
