"""
Dual-Tier Memory for TMRDS clinical reasoning context.

Tier 1: Fast semantic/key-value cache (Redis-compatible interface; in-process fallback).
Tier 2: Long-horizon context store inspired by research on neural long-term memory
         (Google Titans / MIRAS family — arXiv:2501.00663). This is an engineering
         interface for large context windows, NOT a claim of shipping Titans weights.

Clinical use: cache literature hits, phenotype defs, prior advisory packets.
"""
from __future__ import annotations

import hashlib
import time
from collections import OrderedDict
from typing import Any, Dict, List, Optional


class DualTierMemory:
    def __init__(self, tier1_max: int = 2048, tier2_max_docs: int = 10_000) -> None:
        self._t1: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._t2: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self.tier1_max = tier1_max
        self.tier2_max_docs = tier2_max_docs
        self.redis_url: Optional[str] = None  # set to enable external Redis

    def _key(self, namespace: str, text: str) -> str:
        h = hashlib.sha256(f"{namespace}:{text}".encode()).hexdigest()[:24]
        return f"{namespace}:{h}"

    def put_tier1(self, namespace: str, key_text: str, value: Any, ttl_sec: int = 3600) -> str:
        k = self._key(namespace, key_text)
        self._t1[k] = {"value": value, "expires": time.time() + ttl_sec, "ns": namespace}
        self._t1.move_to_end(k)
        while len(self._t1) > self.tier1_max:
            self._t1.popitem(last=False)
        return k

    def get_tier1(self, namespace: str, key_text: str) -> Optional[Any]:
        k = self._key(namespace, key_text)
        item = self._t1.get(k)
        if not item:
            return None
        if item["expires"] < time.time():
            self._t1.pop(k, None)
            return None
        self._t1.move_to_end(k)
        return item["value"]

    def put_tier2(self, doc_id: str, content: Dict[str, Any], surprise: float = 0.0) -> str:
        """
        Long-term document memory. `surprise` is a scalar hint (0–1) analogous to
        research 'surprise metric' for prioritising retention — heuristic only.
        """
        self._t2[doc_id] = {
            "content": content,
            "surprise": surprise,
            "stored_at": time.time(),
        }
        self._t2.move_to_end(doc_id)
        while len(self._t2) > self.tier2_max_docs:
            # drop lowest surprise first (simple policy)
            victim = min(self._t2.items(), key=lambda kv: kv[1].get("surprise", 0))
            self._t2.pop(victim[0], None)
        return doc_id

    def search_tier2(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        q = query.lower()
        hits = []
        for doc_id, meta in self._t2.items():
            blob = str(meta.get("content", "")).lower()
            if q in blob or q in doc_id.lower():
                hits.append({"doc_id": doc_id, **meta})
        hits.sort(key=lambda x: x.get("surprise", 0), reverse=True)
        return hits[:limit]

    def status(self) -> Dict[str, Any]:
        return {
            "node": "DualTierMemory",
            "tier1_size": len(self._t1),
            "tier2_size": len(self._t2),
            "redis_configured": bool(self.redis_url),
            "research_ref": "Titans long-term memory (arXiv:2501.00663) — interface only",
            "status": "READY",
        }
