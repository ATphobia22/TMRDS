"""
TurboVecIndex — memory-optimized spatial vector index for TMRDS.
Targets sub-millisecond similarity search within a constrained memory layout.
"""
from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional

import numpy as np


class TurboVecIndex:
    """Lightweight in-process vector index (API-compatible with FAISS/pgvector swap)."""

    def __init__(self, dim: int = 384, max_vectors: int = 100_000) -> None:
        if dim < 8:
            raise ValueError("dim must be >= 8")
        self.dim = dim
        self.max_vectors = max_vectors
        self._ids: List[str] = []
        self._matrix: Optional[np.ndarray] = None
        self._meta: Dict[str, Dict[str, Any]] = {}

    def _normalize(self, vec: np.ndarray) -> np.ndarray:
        v = np.asarray(vec, dtype=np.float32).reshape(-1)
        if v.shape[0] != self.dim:
            raise ValueError(f"Expected dim={self.dim}, got {v.shape[0]}")
        n = np.linalg.norm(v)
        return v / n if n > 0 else v

    def add(self, vector_id: str, vector: List[float], metadata: Optional[Dict[str, Any]] = None) -> None:
        if len(self._ids) >= self.max_vectors:
            raise RuntimeError("TurboVecIndex capacity exceeded")
        v = self._normalize(np.array(vector))
        if self._matrix is None:
            self._matrix = v.reshape(1, -1)
        else:
            self._matrix = np.vstack([self._matrix, v.reshape(1, -1)])
        self._ids.append(vector_id)
        self._meta[vector_id] = metadata or {}

    def search(self, query: List[float], top_k: int = 5) -> Dict[str, Any]:
        if self._matrix is None or len(self._ids) == 0:
            return {"hits": [], "count": 0}
        q = self._normalize(np.array(query))
        scores = self._matrix @ q
        k = min(top_k, len(self._ids))
        idx = np.argpartition(-scores, kth=k - 1)[:k]
        idx = idx[np.argsort(-scores[idx])]
        hits = []
        for i in idx:
            vid = self._ids[int(i)]
            hits.append({
                "id": vid,
                "score": float(scores[i]),
                "metadata": self._meta.get(vid, {}),
            })
        return {"hits": hits, "count": len(hits), "dim": self.dim}

    def content_hash(self, vector_id: str) -> Optional[str]:
        if vector_id not in self._meta:
            return None
        payload = f"{vector_id}:{self._meta[vector_id]}"
        return hashlib.sha256(payload.encode()).hexdigest()

    def stats(self) -> Dict[str, Any]:
        n = len(self._ids)
        bytes_est = n * self.dim * 4 if n else 0
        return {
            "node": "TurboVecIndex",
            "vectors": n,
            "dim": self.dim,
            "est_bytes": bytes_est,
            "est_mb": round(bytes_est / (1024 * 1024), 3),
            "capacity": self.max_vectors,
            "status": "READY",
        }
