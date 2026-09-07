"""
Clinical Swarm Orchestrator for TMRDS.

Inspired by production multi-agent patterns (Swarms framework: hierarchical,
concurrent, sequential workflows). Coordinates specialist advisory agents
without external hard dependency.

Does NOT make clinical decisions. Outputs are parallel advisory perspectives
for human review only.
"""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Optional


class ClinicalAgent:
    def __init__(self, name: str, role: str, run_fn: Callable[[str], Dict[str, Any]]) -> None:
        self.name = name
        self.role = role
        self._run = run_fn

    def run(self, task: str) -> Dict[str, Any]:
        out = self._run(task)
        out.setdefault("agent", self.name)
        out.setdefault("role", self.role)
        return out


def _analytical(task: str) -> Dict[str, Any]:
    return {"perspective": "analytical", "focus": "structure problem into measurable claims", "task": task}


def _empirical(task: str) -> Dict[str, Any]:
    return {"perspective": "empirical", "focus": "demand measured outcomes / trial evidence", "task": task}


def _skeptic(task: str) -> Dict[str, Any]:
    return {"perspective": "skeptic", "focus": "challenge assumptions, confounders, harm", "task": task}


def _guideline(task: str) -> Dict[str, Any]:
    return {"perspective": "guideline", "focus": "map to standards FHIR/OMOP/NLM evidence path", "task": task}


def _safety(task: str) -> Dict[str, Any]:
    return {"perspective": "safety", "focus": "bias, equity, contraindications, human gate", "task": task}


class ClinicalSwarmOrchestrator:
    """Fan-out specialist agents; merge advisory briefs."""

    def __init__(self) -> None:
        self.agents = [
            ClinicalAgent("analytical", "decompose", _analytical),
            ClinicalAgent("empirical", "evidence", _empirical),
            ClinicalAgent("skeptic", "challenge", _skeptic),
            ClinicalAgent("guideline", "standards", _guideline),
            ClinicalAgent("safety", "harm_reduction", _safety),
        ]

    def concurrent(self, task: str, max_workers: int = 5) -> Dict[str, Any]:
        t0 = time.time()
        results: List[Dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futs = {pool.submit(a.run, task): a.name for a in self.agents}
            for fut in as_completed(futs):
                try:
                    results.append(fut.result())
                except Exception as exc:  # noqa: BLE001
                    results.append({"agent": futs[fut], "error": str(exc)})
        return {
            "task": task,
            "mode": "concurrent",
            "agent_count": len(results),
            "perspectives": results,
            "latency_sec": round(time.time() - t0, 4),
            "advisory_only": True,
            "status": "SWARM_COMPLETE",
        }

    def sequential(self, task: str) -> Dict[str, Any]:
        chain = []
        ctx = task
        for a in self.agents:
            r = a.run(ctx)
            chain.append(r)
            ctx = f"{task} | prior={r.get('perspective')}"
        return {
            "task": task,
            "mode": "sequential",
            "chain": chain,
            "advisory_only": True,
            "status": "SWARM_COMPLETE",
        }

    def status(self) -> Dict[str, Any]:
        return {
            "node": "ClinicalSwarmOrchestrator",
            "agents": [a.name for a in self.agents],
            "patterns": ["concurrent", "sequential"],
            "external_ref": "Swarms multi-agent orchestration patterns (optional pip install swarms)",
            "status": "READY",
        }
