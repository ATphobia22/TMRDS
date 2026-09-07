"""
Epistemic Parallel Reasoning Router for TMRDS.

Runs multiple reasoning branches in parallel (analytical, empirical, skeptic,
lateral, safety, guideline) and scores divergence for audit of exploration breadth.

TF-IDF-style token divergence is a lightweight quantitative audit signal —
not a measure of clinical correctness.

Combines with ClinicalSwarmOrchestrator. Advisory only.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List


BRANCHES = (
    "analytical",
    "empirical",
    "skeptic",
    "lateral",
    "safety",
    "guideline",
    "patient_context",
    "resource_stewardship",
)


def _tokens(text: str) -> Counter:
    return Counter(re.findall(r"[a-z0-9]+", text.lower()))


def _cosine(a: Counter, b: Counter) -> float:
    keys = set(a) | set(b)
    if not keys:
        return 0.0
    dot = sum(a[k] * b[k] for k in keys)
    na = math.sqrt(sum(v * v for v in a.values())) or 1.0
    nb = math.sqrt(sum(v * v for v in b.values())) or 1.0
    return dot / (na * nb)


class EpistemicParallelRouter:
    def branch(self, name: str, problem: str) -> Dict[str, Any]:
        prompts = {
            "analytical": f"Decompose into testable claims: {problem}",
            "empirical": f"What measured evidence is required: {problem}",
            "skeptic": f"What could be wrong or harmful: {problem}",
            "lateral": f"Alternative framings / rare differentials: {problem}",
            "safety": f"Bias, equity, contraindications: {problem}",
            "guideline": f"Standards path FHIR/OMOP/NLM/trials: {problem}",
            "patient_context": f"Individual goals, comorbidities, values: {problem}",
            "resource_stewardship": f"Feasible rural/tri-state resources: {problem}",
        }
        text = prompts.get(name, problem)
        return {"branch": name, "brief": text, "tokens": dict(_tokens(text))}

    def run(self, problem: str) -> Dict[str, Any]:
        results: List[Dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=8) as pool:
            futs = [pool.submit(self.branch, b, problem) for b in BRANCHES]
            for fut in as_completed(futs):
                results.append(fut.result())
        # pairwise divergence = 1 - mean cosine similarity
        vecs = [_tokens(r["brief"]) for r in results]
        sims = []
        for i in range(len(vecs)):
            for j in range(i + 1, len(vecs)):
                sims.append(_cosine(vecs[i], vecs[j]))
        mean_sim = sum(sims) / len(sims) if sims else 0.0
        divergence = round(1.0 - mean_sim, 4)
        return {
            "problem": problem,
            "branches": results,
            "mean_cosine_similarity": round(mean_sim, 4),
            "tfidf_style_divergence": divergence,
            "note": "High divergence = broader exploration, not higher clinical truth",
            "advisory_only": True,
            "status": "NPR_COMPLETE",
        }

    def status(self) -> Dict[str, Any]:
        return {
            "node": "EpistemicParallelRouter",
            "branches": list(BRANCHES),
            "status": "READY",
        }
