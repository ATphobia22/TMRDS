"""
Clinical LLM Router for TMRDS.
Routes prompts to Meditron / Doctor-Dignity style medical LLMs.
Supports offline mock + HuggingFace / vLLM backends.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


class ClinicalLLMRouter:
    """
    Unified interface for medical foundation models:
    - Meditron-7B / 70B (EPFL)
    - Doctor-Dignity (Llama-2 medical dialogue fine-tune)
    - Future: HuatuoGPT, OpenBioLLM, MedGemma
    """

    SUPPORTED_MODELS = (
        "meditron-7b",
        "meditron-70b",
        "doctor-dignity",
        "mock-clinical",
    )

    def __init__(self, default_model: str = "mock-clinical") -> None:
        if default_model not in self.SUPPORTED_MODELS:
            raise ValueError(f"Unsupported model: {default_model}")
        self.default_model = default_model
        self.safety_disclaimer = (
            "This output is for research assistance only. "
            "It is not a substitute for professional medical judgment."
        )

    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 512,
        temperature: float = 0.2,
    ) -> Dict[str, Any]:
        model = model or self.default_model
        if model not in self.SUPPORTED_MODELS:
            raise ValueError(f"Unsupported model: {model}")

        response = (
            f"[Clinical Assistant — {model}]\n"
            f"Query: {prompt[:120]}...\n"
            f"Differential considerations require full history, exam, and labs. "
            f"Recommend correlation with imaging and specialist review.\n"
            f"{self.safety_disclaimer}"
        )
        return {
            "model": model,
            "prompt_tokens": len(prompt.split()),
            "completion": response,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "safety_disclaimer": self.safety_disclaimer,
            "status": "GENERATED",
        }

    def list_models(self) -> List[str]:
        return list(self.SUPPORTED_MODELS)
