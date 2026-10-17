"""
BioCoder-aware Research Assistant for TMRDS.
Provides structured prompts and evaluation hooks for bioinformatics
code generation. The detached mock response is never represented as real generation.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


class BioCoderAssistant:
    """Bioinformatics code-generation helper for research workflows."""

    DOMAINS = (
        "sequence_analysis",
        "structure_prediction",
        "variant_calling",
        "differential_expression",
        "pathway_enrichment",
        "molecular_docking_prep",
    )

    def __init__(self, llm_router: Optional[Any] = None) -> None:
        self.llm_router = llm_router

    def build_prompt(
        self,
        task_description: str,
        language: str = "python",
        context_imports: Optional[List[str]] = None,
        domain: str = "sequence_analysis",
    ) -> str:
        imports = context_imports or []
        import_block = "\n".join(f"import {m}" for m in imports) if imports else "# (no extra imports)"
        return (
            f"You are an expert bioinformatics engineer.\n"
            f"Domain: {domain}\n"
            f"Language: {language}\n"
            f"Required context:\n{import_block}\n\n"
            f"Task:\n{task_description}\n\n"
            f"Constraints:\n"
            f"- Produce complete, runnable code.\n"
            f"- Prefer Biopython / pysam / pandas / numpy where appropriate.\n"
            f"- Include type hints and a minimal docstring.\n"
            f"- Do not invent non-existent APIs.\n"
        )

    def generate_code(
        self,
        task_description: str,
        language: str = "python",
        domain: str = "sequence_analysis",
        context_imports: Optional[List[str]] = None,
        model: str = "mock-clinical",
    ) -> Dict[str, Any]:
        prompt = self.build_prompt(task_description, language, context_imports, domain)
        if self.llm_router is not None:
            result = self.llm_router.generate(prompt, model=model, max_tokens=1024, temperature=0.1)
            backend = result.get("backend", "unknown")
            status = result.get("status", "UNKNOWN")
            return {
                "prompt": prompt,
                "completion": result.get("completion"),
                "model": result.get("model"),
                "backend": backend,
                "domain": domain,
                "status": "MOCK" if status == "MOCK" or backend == "mock" else status,
                "mock_fallback": bool(result.get("mock_fallback", status == "MOCK" or backend == "mock")),
                "fallback_reason": result.get("fallback_reason"),
                "safety_disclaimer": result.get("safety_disclaimer"),
            }
        return {
            "prompt": prompt,
            "completion": (
                f"# BioCoder mock — domain={domain}\n"
                f"# Task: {task_description[:80]}...\n"
                "# No code was generated or executed; connect a reviewed model backend.\n"
                "def solve():\n"
                "    raise NotImplementedError('Wire ClinicalLLMRouter for real generation')\n"
            ),
            "model": "mock",
            "backend": "mock",
            "domain": domain,
            "status": "MOCK",
            "mock_fallback": False,
            "fallback_reason": "no_model_router_configured",
            "citation": "Tang et al., BioCoder: a benchmark for bioinformatics code generation, Bioinformatics 2024",
        }

    def status(self) -> Dict[str, Any]:
        return {
            "node": "BioCoderAssistant",
            "domains": list(self.DOMAINS),
            "llm_attached": self.llm_router is not None,
            "status": "READY" if self.llm_router is not None else "MOCK_ONLY",
        }
