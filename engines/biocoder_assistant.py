"""Bioinformatics code-generation helper with explicit unavailable/mock states."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("TMRDS.BioCoderAssistant")


class BioCoderAssistant:
    """Build domain-specific prompts and delegate only to an explicitly attached router.

    This class does not fabricate runnable code when no generation backend exists.
    Generated biomedical/bioinformatics code must be reviewed and tested before use.
    """

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
        if not isinstance(task_description, str) or not task_description.strip():
            raise ValueError("task_description must be a non-empty string")
        if len(task_description) > 20_000:
            raise ValueError("task_description exceeds the 20000-character limit")
        if not isinstance(language, str) or not language.strip():
            raise ValueError("language must be a non-empty string")
        if domain not in self.DOMAINS:
            raise ValueError(f"unsupported domain: {domain}")

        imports = context_imports or []
        if any(not isinstance(module, str) or not module.strip() for module in imports):
            raise ValueError("context_imports must contain non-empty strings")
        import_block = (
            "\n".join(f"import {module}" for module in imports)
            if imports
            else "# (no extra imports)"
        )
        return (
            "You are an expert bioinformatics engineer.\n"
            f"Domain: {domain}\n"
            f"Language: {language}\n"
            f"Required context:\n{import_block}\n\n"
            f"Task:\n{task_description.strip()}\n\n"
            "Constraints:\n"
            "- Produce complete, runnable code only when the backend supports generation.\n"
            "- Prefer Biopython / pysam / pandas / numpy where appropriate.\n"
            "- Include type hints and a minimal docstring.\n"
            "- Do not invent non-existent APIs.\n"
            "- Label assumptions and require human review before execution.\n"
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
        if self.llm_router is None:
            return {
                "prompt": prompt,
                "completion": None,
                "model": None,
                "backend": None,
                "domain": domain,
                "status": "UNAVAILABLE",
                "reason": "No code-generation backend is configured.",
                "review_required": True,
            }

        generate = getattr(self.llm_router, "generate", None)
        if not callable(generate):
            return {
                "prompt": prompt,
                "completion": None,
                "model": None,
                "backend": None,
                "domain": domain,
                "status": "UNAVAILABLE",
                "reason": "Configured router does not expose a callable generate method.",
                "review_required": True,
            }

        try:
            result = generate(prompt, model=model, max_tokens=1024, temperature=0.1)
        except Exception as exc:  # noqa: BLE001 - public result must not expose raw exception text
            logger.warning("BioCoder generation failed (%s)", type(exc).__name__)
            return {
                "prompt": prompt,
                "completion": None,
                "model": model,
                "backend": None,
                "domain": domain,
                "status": "ERROR",
                "reason": f"Generation failed ({type(exc).__name__}).",
                "review_required": True,
            }

        if not isinstance(result, dict):
            return {
                "prompt": prompt,
                "completion": None,
                "model": model,
                "backend": None,
                "domain": domain,
                "status": "ERROR",
                "reason": "Generation backend returned an invalid response.",
                "review_required": True,
            }

        backend = result.get("backend")
        completion = result.get("completion")
        actual_model = result.get("model", model)
        is_mock = str(backend or "").casefold() in {"mock", "mock_only", "mock-only"}
        is_mock = is_mock or str(actual_model or "").casefold() in {"mock", "mock-clinical"}
        return {
            "prompt": prompt,
            "completion": completion if isinstance(completion, str) and completion.strip() else None,
            "model": actual_model,
            "backend": backend,
            "domain": domain,
            "status": "MOCK" if is_mock else ("GENERATED" if completion else "ERROR"),
            "reason": "Mock output is not validated executable code." if is_mock else None,
            "review_required": True,
        }

    def status(self) -> Dict[str, Any]:
        configured = self.llm_router is not None and callable(
            getattr(self.llm_router, "generate", None)
        )
        return {
            "node": "BioCoderAssistant",
            "domains": list(self.DOMAINS),
            "llm_attached": configured,
            "status": "READY" if configured else "UNAVAILABLE",
        }
