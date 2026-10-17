"""
Clinical LLM Router for TMRDS.
Backends: vLLM (preferred), HuggingFace transformers, mock.
Targets are optional research backends; generated output is not clinical advice.
"""
from __future__ import annotations

import logging
import math
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


def _env_flag(name: str, default: str = "false") -> bool:
    """Parse a positive opt-in environment flag without permissive truthiness."""
    return os.getenv(name, default).strip().casefold() in {"1", "true", "yes", "on"}


class ClinicalLLMRouter:
    """Unified medical research-assistance LLM interface.

    Remote model repositories can contain executable code. Loading such code is
    disabled by default and requires explicit TMRDS_LLM_TRUST_REMOTE_CODE=true.
    """

    MODEL_MAP = {
        "meditron-7b": "epfl-llm/meditron-7b",
        "meditron-70b": "epfl-llm/meditron-70b",
        "doctor-dignity": os.getenv("DOCTOR_DIGNITY_PATH", "llSourcell/doctorGPT_mini"),
        "mock-clinical": None,
    }
    SUPPORTED_MODELS = tuple(MODEL_MAP.keys())
    SUPPORTED_BACKENDS = {"auto", "vllm", "hf", "mock"}
    MAX_PROMPT_CHARS = 100_000
    MAX_GENERATION_TOKENS = 8192

    def __init__(
        self,
        default_model: str = "mock-clinical",
        backend: str = "auto",
        tensor_parallel_size: int = 1,
    ) -> None:
        if default_model not in self.SUPPORTED_MODELS:
            raise ValueError(f"Unsupported model: {default_model}")
        if backend not in self.SUPPORTED_BACKENDS:
            raise ValueError(f"Unsupported backend: {backend}")
        if not isinstance(tensor_parallel_size, int) or isinstance(tensor_parallel_size, bool) or tensor_parallel_size < 1:
            raise ValueError("tensor_parallel_size must be a positive integer")

        self.default_model = default_model
        self.backend = self._resolve_backend(backend)
        self.tensor_parallel_size = tensor_parallel_size
        self.trust_remote_code = _env_flag("TMRDS_LLM_TRUST_REMOTE_CODE", "false")
        self._llm = None
        self._tokenizer = None
        self._mock_fallback_reason: Optional[str] = "mock_backend_selected" if self.backend == "mock" else None
        self.safety_disclaimer = (
            "This output is for research assistance only. "
            "It is not a substitute for professional medical judgment."
        )
        if self.trust_remote_code:
            logger.warning(
                "TMRDS_LLM_TRUST_REMOTE_CODE is enabled; model loading may execute code from the model repository. "
                "Use only reviewed, pinned model artifacts."
            )
        if self.default_model != "mock-clinical":
            self._lazy_load(self.default_model)

    def _resolve_backend(self, backend: str) -> str:
        if backend != "auto":
            return backend
        if VLLM_AVAILABLE:
            return "vllm"
        if HF_AVAILABLE:
            return "hf"
        return "mock"

    def _lazy_load(self, model_key: str) -> None:
        hf_id = self.MODEL_MAP.get(model_key)
        if not hf_id:
            return
        try:
            if self.backend == "vllm" and VLLM_AVAILABLE:
                logger.info("Loading approved model identifier %s via vLLM", hf_id)
                self._llm = LLM(
                    model=hf_id,
                    tensor_parallel_size=self.tensor_parallel_size,
                    trust_remote_code=self.trust_remote_code,
                )
                self._mock_fallback_reason = None
            elif self.backend == "hf" and HF_AVAILABLE:
                logger.info("Loading approved model identifier %s via HuggingFace", hf_id)
                self._tokenizer = AutoTokenizer.from_pretrained(
                    hf_id,
                    trust_remote_code=self.trust_remote_code,
                )
                self._llm = AutoModelForCausalLM.from_pretrained(
                    hf_id,
                    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                    device_map="auto",
                    trust_remote_code=self.trust_remote_code,
                )
                self._mock_fallback_reason = None
            else:
                logger.warning("Requested model backend is unavailable; using explicit mock fallback")
                self.backend = "mock"
                self._mock_fallback_reason = "backend_unavailable"
        except Exception as exc:  # noqa: BLE001
            # Avoid logging remote exception text, which may contain local paths or request metadata.
            logger.error("Model loading failed (%s); using explicit mock fallback", type(exc).__name__)
            self.backend = "mock"
            self._llm = None
            self._tokenizer = None
            self._mock_fallback_reason = "model_load_failed"

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
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("prompt must be a non-empty string")
        if len(prompt) > self.MAX_PROMPT_CHARS:
            raise ValueError(f"prompt exceeds the {self.MAX_PROMPT_CHARS}-character limit")
        if (
            not isinstance(max_tokens, int)
            or isinstance(max_tokens, bool)
            or not 1 <= max_tokens <= self.MAX_GENERATION_TOKENS
        ):
            raise ValueError(f"max_tokens must be between 1 and {self.MAX_GENERATION_TOKENS}")
        if (
            not isinstance(temperature, (int, float))
            or isinstance(temperature, bool)
            or not math.isfinite(temperature)
            or not 0.0 <= temperature <= 2.0
        ):
            raise ValueError("temperature must be a finite number between 0 and 2")

        if model != self.default_model and model != "mock-clinical":
            self._lazy_load(model)

        used_mock = model == "mock-clinical"
        completion: str
        if not used_mock and self.backend == "vllm" and self._llm is not None:
            params = SamplingParams(temperature=float(temperature), max_tokens=max_tokens)
            outputs = self._llm.generate([prompt], params)
            completion = outputs[0].outputs[0].text
        elif not used_mock and self.backend == "hf" and self._llm is not None and self._tokenizer is not None:
            inputs = self._tokenizer(prompt, return_tensors="pt").to(self._llm.device)
            with torch.no_grad():
                out = self._llm.generate(
                    **inputs,
                    max_new_tokens=max_tokens,
                    temperature=float(temperature),
                    do_sample=temperature > 0,
                )
            completion = self._tokenizer.decode(out[0], skip_special_tokens=True)
        else:
            used_mock = True
            completion = (
                f"[Clinical Assistant — {model} (mock; research-only)]\n"
                f"Query: {prompt[:120]}...\n"
                "No non-mock model execution was performed. Do not interpret this placeholder "
                "as a model-generated clinical conclusion.\n"
                f"{self.safety_disclaimer}"
            )

        fallback = used_mock and model != "mock-clinical"
        return {
            "model": model,
            "backend": "mock" if used_mock else self.backend,
            "prompt_tokens": len(prompt.split()),
            "completion": completion,
            "max_tokens": max_tokens,
            "temperature": float(temperature),
            "safety_disclaimer": self.safety_disclaimer,
            "status": "MOCK" if used_mock else "GENERATED",
            "mock_fallback": fallback,
            "fallback_reason": self._mock_fallback_reason if fallback else None,
            "trust_remote_code": self.trust_remote_code,
        }

    def list_models(self) -> List[str]:
        return list(self.SUPPORTED_MODELS)

    def backend_status(self) -> Dict[str, Any]:
        return {
            "active_backend": self.backend,
            "vllm_available": VLLM_AVAILABLE,
            "hf_available": HF_AVAILABLE,
            "default_model": self.default_model,
            "trust_remote_code": self.trust_remote_code,
            "mock_fallback": self.backend == "mock" and self.default_model != "mock-clinical",
            "fallback_reason": self._mock_fallback_reason,
        }
