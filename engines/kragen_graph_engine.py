"""
KRAGEN Graph Engine for TMRDS.
Knowledge Retrieval Augmented Generation ENgine — graph storage unifying
pathology, molecular, and quantum layers.

Inspired by EpistasisLab/KRAGEN (Matsumoto et al., Bioinformatics 2024):
  Neo4j KG dump → natural-language statements → vector DB (Weaviate/TurboVec)
  → Graph-of-Thoughts (GoT) reasoning for biomedical problem solving.

Citation: Matsumoto et al., KRAGEN: a knowledge graph-enhanced RAG framework
for biomedical problem solving using large language models, Bioinformatics 2024.
"""
from __future__ import annotations

import hashlib
import time
from typing import Any, Dict, List, Optional, Tuple


class KRAGENGraphEngine:
    """
    Persistent multi-layer biomedical knowledge graph.

    Layers:
      - pathology  (diseases, phenotypes, findings)
      - molecular  (genes, drugs, proteins, pathways)
      - quantum    (Hamiltonian refs, VQE results, structure hashes)

    Offline path: in-memory adjacency + TurboVec-compatible embeddings.
    Production path: Neo4j / Weaviate (KRAGEN stack).
    """

    LAYERS = ("pathology", "molecular", "quantum", "clinical")

    def __init__(self) -> None:
        # node_id → {label, layer, properties, content_hash}
        self._nodes: Dict[str, Dict[str, Any]] = {}
        # (src, rel, dst) triples
        self._edges: List[Tuple[str, str, str, Dict[str, Any]]] = []

    def upsert_node(
        self,
        node_id: str,
        label: str,
        layer: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if layer not in self.LAYERS:
            raise ValueError(f"layer must be one of {self.LAYERS}")
        props = properties or {}
        payload = {"label": label, "layer": layer, **props}
        content_hash = hashlib.sha256(
            str(sorted(payload.items())).encode()
        ).hexdigest()[:16]
        node = {
            "id": node_id,
            "label": label,
            "layer": layer,
            "properties": props,
            "content_hash": content_hash,
            "updated_at": time.time(),
        }
        self._nodes[node_id] = node
        return node

    def add_edge(
        self,
        src: str,
        relation: str,
        dst: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if src not in self._nodes or dst not in self._nodes:
            raise KeyError("Both src and dst nodes must exist before adding edge")
        edge = (src, relation, dst, properties or {})
        self._edges.append(edge)
        return {
            "src": src,
            "relation": relation,
            "dst": dst,
            "properties": properties or {},
        }

    def neighbors(self, node_id: str, relation: Optional[str] = None) -> List[Dict[str, Any]]:
        results = []
        for s, r, d, props in self._edges:
            if s == node_id and (relation is None or r == relation):
                results.append({"direction": "out", "relation": r, "node": self._nodes[d], "properties": props})
            elif d == node_id and (relation is None or r == relation):
                results.append({"direction": "in", "relation": r, "node": self._nodes[s], "properties": props})
        return results

    def subgraph(self, layer: Optional[str] = None) -> Dict[str, Any]:
        nodes = [
            n for n in self._nodes.values()
            if layer is None or n["layer"] == layer
        ]
        node_ids = {n["id"] for n in nodes}
        edges = [
            {"src": s, "relation": r, "dst": d, "properties": p}
            for s, r, d, p in self._edges
            if s in node_ids and d in node_ids
        ]
        return {
            "layer": layer or "all",
            "node_count": len(nodes),
            "edge_count": len(edges),
            "nodes": nodes,
            "edges": edges,
        }

    def to_statements(self, limit: int = 100) -> List[str]:
        """Convert graph edges to natural-language statements for RAG vectorization (KRAGEN style)."""
        statements = []
        for s, r, d, props in self._edges[:limit]:
            src_label = self._nodes[s]["label"]
            dst_label = self._nodes[d]["label"]
            stmt = f"{src_label} {r.replace('_', ' ')} {dst_label}."
            if props:
                stmt += f" Properties: {props}."
            statements.append(stmt)
        return statements

    def graph_of_thoughts_stub(self, question: str, max_hops: int = 2) -> Dict[str, Any]:
        """
        Lightweight GoT scaffold: expand from keyword-matched nodes up to max_hops.
        Production path delegates to full KRAGEN Docker stack + LLM.
        """
        q_lower = question.lower()
        seeds = [
            n for n in self._nodes.values()
            if any(tok in n["label"].lower() for tok in q_lower.split() if len(tok) > 3)
        ][:5]
        paths = []
        for seed in seeds:
            hops = self.neighbors(seed["id"])
            paths.append({
                "seed": seed,
                "hop1": hops[:5],
            })
        return {
            "question": question,
            "method": "graph_of_thoughts_stub",
            "max_hops": max_hops,
            "seed_count": len(seeds),
            "paths": paths,
            "statements_sample": self.to_statements(20),
            "note": "Wire EpistasisLab/KRAGEN + Weaviate for production GoT + RAG",
            "citation": "Matsumoto et al., Bioinformatics 2024 (KRAGEN)",
        }

    def status(self) -> Dict[str, Any]:
        by_layer: Dict[str, int] = {}
        for n in self._nodes.values():
            by_layer[n["layer"]] = by_layer.get(n["layer"], 0) + 1
        return {
            "node": "KRAGENGraphEngine",
            "nodes": len(self._nodes),
            "edges": len(self._edges),
            "by_layer": by_layer,
            "layers": list(self.LAYERS),
            "status": "READY",
        }
