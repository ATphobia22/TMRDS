"""Research-only local LLM router with explicit mock-state reporting."""
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
    """Unified research-only local LLM interface.

    Remote model repository code is never trusted implicitly. If a model cannot
    load under the default safe configuration, generation is explicitly marked
    MOCK_ONLY; callers must not treat the fallback text as model output.
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
        if not isinstance(tensor_parallel_size, int) or tensor_parallel_size < 1:
            raise ValueError("tensor_parallel_size must be a positive integer")
        if backend not in {"auto", "vllm", "hf", "mock"}:
            raise ValueError("backend must be one of: auto, vllm, hf, mock")

        self.default_model = default_model
        self.backend = "mock" if default_model == "mock-clinical" else self._resolve_backend(backend)
        self.tensor_parallel_size = tensor_parallel_size
        self._llm = None
        self._tokenizer = None
        self.safety_disclaimer = (
            "Research assistance only. Outputs require independent review and "
            "must not be used as diagnosis, prescribing, or autonomous clinical action."
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
                logger.info("Loading model %s via vLLM with remote code disabled", hf_id)
                self._llm = LLM(
                    model=hf_id,
                    tensor_parallel_size=self.tensor_parallel_size,
                    trust_remote_code=False,
                )
            elif self.backend == "hf" and HF_AVAILABLE:
                logger.info("Loading model %s via HuggingFace with remote code disabled", hf_id)
                self._tokenizer = AutoTokenizer.from_pretrained(hf_id, trust_remote_code=False)
                self._llm = AutoModelForCausalLM.from_pretrained(
                    hf_id,
                    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                    device_map="auto",
                    trust_remote_code=False,
                )
            else:
                logger.warning("Requested backend unavailable; switching to explicit mock mode")
                self.backend = "mock"
        except Exception as exc:  # noqa: BLE001 - avoid exposing provider/model internals
            logger.error("Model load failed (%s); switching to explicit mock mode", type(exc).__name__)
            self.backend = "mock"
            self._llm = None
            self._tokenizer = None

    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 512,
        temperature: float = 0.2,
    ) -> Dict[str, Any]:
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("prompt must be a non-empty string")
        if isinstance(max_tokens, bool) or not isinstance(max_tokens, int) or not 1 <= max_tokens <= 8192:
            raise ValueError("max_tokens must be an integer from 1 through 8192")
        if not isinstance(temperature, (int, float)) or not 0 <= temperature <= 2:
            raise ValueError("temperature must be between 0 and 2")

        model = model or self.default_model
        if model not in self.SUPPORTED_MODELS:
            raise ValueError(f"Unsupported model: {model}")

        if model != self.default_model and model != "mock-clinical":
            self._lazy_load(model)

        inference_executed = False
        if self.backend == "vllm" and self._llm is not None:
            params = SamplingParams(temperature=float(temperature), max_tokens=max_tokens)
            outputs = self._llm.generate([prompt], params)
            completion = outputs[0].outputs[0].text
            inference_executed = True
        elif self.backend == "hf" and self._llm is not None and self._tokenizer is not None:
            inputs = self._tokenizer(prompt, return_tensors="pt").to(self._llm.device)
            with torch.no_grad():
                out = self._llm.generate(
                    **inputs,
                    max_new_tokens=max_tokens,
                    temperature=float(temperature),
                    do_sample=temperature > 0,
                )
            completion = self._tokenizer.decode(out[0], skip_special_tokens=True)
            inference_executed = True
        else:
            completion = (
                "MOCK_ONLY: no language-model inference was performed. "
                "Configure and verify a supported local model backend before requesting generation. "
                + self.safety_disclaimer
            )

        return {
            "model": model,
            "backend": self.backend if inference_executed else "mock",
            "prompt_tokens": len(prompt.split()),
            "completion": completion,
            "max_tokens": max_tokens,
            "temperature": float(temperature),
            "safety_disclaimer": self.safety_disclaimer,
            "status": "GENERATED" if inference_executed else "MOCK_ONLY",
            "inference_executed": inference_executed,
            "human_review_required": True,
        }

    def list_models(self) -> List[str]:
        return list(self.SUPPORTED_MODELS)

    def backend_status(self) -> Dict[str, Any]:
        loaded = self._llm is not None and (
            self.backend == "vllm" or (self.backend == "hf" and self._tokenizer is not None)
        )
        return {
            "active_backend": self.backend if loaded else "mock",
            "vllm_available": VLLM_AVAILABLE,
            "hf_available": HF_AVAILABLE,
            "default_model": self.default_model,
            "model_loaded": loaded,
            "status": "READY" if loaded else "MOCK_ONLY",
        }
