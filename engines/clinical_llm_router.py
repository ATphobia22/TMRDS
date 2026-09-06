"""
Clinical LLM Router for TMRDS.
Backends: vLLM (preferred), HuggingFace transformers, mock.
Targets: Meditron-7B / 70B, Doctor-Dignity, future medical LLMs.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger("TMRDS.ClinicalLLM")

try:
    from vllm import LLM, SamplingParams
    VLLM_AVAILABLE = True
except ImportError:
    VLLM_AVAILABLE = False

try:
    from transformers import AutoModelForCausalLM, AutoTokenizer
    import torch
    HF_AVAILABLE = True
except ImportError:
    HF_AVAILABLE = False


class ClinicalLLMRouter:
    """
    Unified medical LLM interface.

    Backend priority:
      1. vLLM  (high-throughput GPU serving)
      2. HuggingFace transformers
      3. mock  (CI / offline)

    Model map:
      meditron-7b   → epfl-llm/meditron-7b
      meditron-70b  → epfl-llm/meditron-70b
      doctor-dignity → DOCTOR_DIGNITY_PATH or default HF id
    """

    MODEL_MAP = {
        "meditron-7b": "epfl-llm/meditron-7b",
        "meditron-70b": "epfl-llm/meditron-70b",
        "doctor-dignity": os.getenv("DOCTOR_DIGNITY_PATH", "llSourcell/doctorGPT_mini"),
        "mock-clinical": None,
    }

    SUPPORTED_MODELS = tuple(MODEL_MAP.keys())

    def __init__(
        self,
        default_model: str = "mock-clinical",
        backend: str = "auto",
        tensor_parallel_size: int = 1,
    ) -> None:
        if default_model not in self.SUPPORTED_MODELS:
            raise ValueError(f"Unsupported model: {default_model}")
        self.default_model = default_model
        self.backend = self._resolve_backend(backend)
        self.tensor_parallel_size = tensor_parallel_size
        self._llm = None
        self._tokenizer = None
        self.safety_disclaimer = (
            "This output is for research assistance only. "
            "It is not a substitute for professional medical judgment."
        )
        if self.default_model != "mock-clinical":
            self._lazy_load(self.default_model)

    def _resolve_backend(self, backend: str) -> str:
        if backend == "auto":
            if VLLM_AVAILABLE:
                return "vllm"
            if HF_AVAILABLE:
                return "hf"
            return "mock"
        return backend

    def _lazy_load(self, model_key: str) -> None:
        hf_id = self.MODEL_MAP.get(model_key)
        if not hf_id:
            return
        try:
            if self.backend == "vllm" and VLLM_AVAILABLE:
                logger.info("Loading %s via vLLM", hf_id)
                self._llm = LLM(
                    model=hf_id,
                    tensor_parallel_size=self.tensor_parallel_size,
                    trust_remote_code=True,
                )
            elif self.backend == "hf" and HF_AVAILABLE:
                logger.info("Loading %s via HuggingFace", hf_id)
                self._tokenizer = AutoTokenizer.from_pretrained(hf_id, trust_remote_code=True)
                self._llm = AutoModelForCausalLM.from_pretrained(
                    hf_id,
                    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                    device_map="auto",
                    trust_remote_code=True,
                )
            else:
                logger.warning("Requested backend unavailable — falling back to mock")
                self.backend = "mock"
        except Exception as exc:  # noqa: BLE001
            logger.error("Model load failed: %s — using mock", exc)
            self.backend = "mock"
            self._llm = None

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

        if model != self.default_model and model != "mock-clinical":
            self._lazy_load(model)

        if self.backend == "vllm" and self._llm is not None:
            params = SamplingParams(temperature=temperature, max_tokens=max_tokens)
            outputs = self._llm.generate([prompt], params)
            completion = outputs[0].outputs[0].text
        elif self.backend == "hf" and self._llm is not None and self._tokenizer is not None:
            inputs = self._tokenizer(prompt, return_tensors="pt").to(self._llm.device)
            with torch.no_grad():
                out = self._llm.generate(
                    **inputs,
                    max_new_tokens=max_tokens,
                    temperature=temperature,
                    do_sample=temperature > 0,
                )
            completion = self._tokenizer.decode(out[0], skip_special_tokens=True)
        else:
            completion = (
                f"[Clinical Assistant — {model} (mock)]\n"
                f"Query: {prompt[:120]}...\n"
                f"Differential considerations require full history, exam, and labs. "
                f"Recommend correlation with imaging and specialist review.\n"
                f"{self.safety_disclaimer}"
            )

        return {
            "model": model,
            "backend": self.backend,
            "prompt_tokens": len(prompt.split()),
            "completion": completion,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "safety_disclaimer": self.safety_disclaimer,
            "status": "GENERATED",
        }

    def list_models(self) -> List[str]:
        return list(self.SUPPORTED_MODELS)

    def backend_status(self) -> Dict[str, Any]:
        return {
            "active_backend": self.backend,
            "vllm_available": VLLM_AVAILABLE,
            "hf_available": HF_AVAILABLE,
            "default_model": self.default_model,
        }
