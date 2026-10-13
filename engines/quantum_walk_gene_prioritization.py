"""
Quantum-walk gene prioritization — research hypothesis ranking only.

Continuous-time quantum walk (CTQW) on a protein–protein interaction (PPI)
adjacency matrix ranks candidate genes by proximity to seed disease genes.

Reference pattern (research literature):
  Golds et al., "Disease gene prioritization with quantum walks",
  Bioinformatics 2024 — CTQW on PPI adjacency (QA method).

This module is NOT clinical interpretation, diagnosis, or treatment advice.
Scores are retrieval/hypothesis ranks with explicit classical baseline comparison.
Steward: Anthony John Tucker. Human authority final. Not SaMD.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

RESEARCH_ADVISORY = {
    "status": "research-advisory",
    "human_authority_final": True,
    "not_samd": True,
    "not_clinical_decision_support": True,
    "claim_type": "computational_hypothesis",
}


def _normalize_adjacency(adj: np.ndarray) -> np.ndarray:
    a = np.asarray(adj, dtype=np.float64)
    if a.ndim != 2 or a.shape[0] != a.shape[1]:
        raise ValueError("adjacency must be square")
    a = 0.5 * (a + a.T)
    np.fill_diagonal(a, 0.0)
    return a


def continuous_time_quantum_walk_scores(
    adjacency: np.ndarray,
    seed_indices: Sequence[int],
    *,
    evolution_time: float = 1.0,
) -> np.ndarray:
    a = _normalize_adjacency(adjacency)
    n = a.shape[0]
    seeds = [i for i in seed_indices if 0 <= int(i) < n]
    if not seeds:
        raise ValueError("seed_indices empty or out of range")

    psi0 = np.zeros(n, dtype=np.complex128)
    amp = 1.0 / math.sqrt(len(seeds))
    for i in seeds:
        psi0[int(i)] = amp

    eigvals, eigvecs = np.linalg.eigh(a)
    phases = np.exp(-1j * eigvals * float(evolution_time))
    psi_t = eigvecs @ (phases * (eigvecs.conj().T @ psi0))
    probs = np.abs(psi_t) ** 2
    return probs.real.astype(np.float64)


def classical_random_walk_scores(
    adjacency: np.ndarray,
    seed_indices: Sequence[int],
    *,
    steps: int = 10,
    restart: float = 0.15,
) -> np.ndarray:
    a = _normalize_adjacency(adjacency)
    n = a.shape[0]
    seeds = [i for i in seed_indices if 0 <= int(i) < n]
    if not seeds:
        raise ValueError("seed_indices empty or out of range")

    degree = a.sum(axis=1)
    degree[degree == 0] = 1.0
    p = a / degree[:, None]

    r = np.zeros(n, dtype=np.float64)
    for i in seeds:
        r[int(i)] = 1.0 / len(seeds)

    teleport = r.copy()
    for _ in range(max(1, int(steps))):
        r = (1.0 - restart) * (p.T @ r) + restart * teleport
    return r


def prioritize_genes(
    gene_names: Sequence[str],
    adjacency: np.ndarray,
    seed_genes: Sequence[str],
    *,
    evolution_time: float = 1.0,
    top_k: int = 10,
) -> Dict[str, Any]:
    names = [str(g) for g in gene_names]
    name_to_idx = {g: i for i, g in enumerate(names)}
    missing = [s for s in seed_genes if s not in name_to_idx]
    seeds = [name_to_idx[s] for s in seed_genes if s in name_to_idx]
    if not seeds:
        return {
            **RESEARCH_ADVISORY,
            "error": "no_seed_genes_in_graph",
            "missing_seeds": list(seed_genes),
            "arrows": [],
        }

    n = len(names)
    adj = np.asarray(adjacency, dtype=np.float64)
    if adj.shape != (n, n):
        return {
            **RESEARCH_ADVISORY,
            "error": "adjacency_shape_mismatch",
            "expected": [n, n],
            "got": list(adj.shape),
        }

    qw = continuous_time_quantum_walk_scores(adj, seeds, evolution_time=evolution_time)
    cw = classical_random_walk_scores(adj, seeds)

    candidate_mask = np.ones(n, dtype=bool)
    for i in seeds:
        candidate_mask[i] = False

    order_q = np.argsort(-qw)
    order_c = np.argsort(-cw)

    def rank_map(order: np.ndarray) -> Dict[str, int]:
        return {names[int(idx)]: rank + 1 for rank, idx in enumerate(order)}

    rq = rank_map(order_q)
    rc = rank_map(order_c)

    arrows: List[Dict[str, Any]] = []
    k = max(1, min(int(top_k), n))
    for idx in order_q:
        i = int(idx)
        if not candidate_mask[i]:
            continue
        arrows.append(
            {
                "gene": names[i],
                "quantum_walk_score": float(qw[i]),
                "classical_baseline_score": float(cw[i]),
                "quantum_rank": rq[names[i]],
                "classical_rank": rc[names[i]],
                "rank_delta_vs_classical": rc[names[i]] - rq[names[i]],
                "claim_type": "computational_hypothesis",
                "not_clinical_interpretation": True,
            }
        )
        if len(arrows) >= k:
            break

    seed_mass = float(sum(qw[i] for i in seeds))
    error_bound = float(min(1.0, abs(1.0 - seed_mass) + 1.0 / max(n, 1)))

    return {
        **RESEARCH_ADVISORY,
        "method": "continuous_time_quantum_walk_on_ppi_adjacency",
        "backend": "classical_linear_algebra_simulator",
        "evolution_time": float(evolution_time),
        "seed_genes": [names[i] for i in seeds],
        "missing_seeds": missing,
        "gene_count": n,
        "error_bound": error_bound,
        "error_bound_note": (
            "Heuristic uncertainty proxy for CTQW on this graph; "
            "not a clinical confidence interval."
        ),
        "classical_baseline": "personalized_pagerank_style_random_walk",
        "arrows": arrows,
        "limitations": [
            "Research ranking only — not pathogenicity or treatment guidance.",
            "Depends entirely on input PPI graph quality and seed choice.",
            "CTQW executed via classical eigensolve (no quantum hardware).",
            "Always compare quantum ranks to classical baseline before hypothesizing.",
        ],
        "literature_pointer": (
            "Golds et al., Bioinformatics 2024 — disease gene prioritization with quantum walks"
        ),
    }


def demo_toy_graph() -> Dict[str, Any]:
    genes = ["SOD1", "TARDBP", "FUS", "C9orf72", "NEK1", "TBK1", "OPTN", "VCP"]
    n = len(genes)
    adj = np.zeros((n, n))
    edges = [
        (0, 1), (0, 2), (1, 2), (1, 3), (2, 4), (3, 5), (4, 5), (4, 6), (5, 7), (6, 7), (0, 4),
    ]
    for i, j in edges:
        adj[i, j] = adj[j, i] = 1.0
    return prioritize_genes(genes, adj, seed_genes=["SOD1"], evolution_time=1.2, top_k=5)
