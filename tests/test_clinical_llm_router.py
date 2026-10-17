from __future__ import annotations

import pytest

from engines.biocoder_assistant import BioCoderAssistant
from engines.clinical_llm_router import ClinicalLLMRouter


def test_mock_backend_is_labeled_mock_not_generated() -> None:
    router = ClinicalLLMRouter(default_model="mock-clinical", backend="mock")
    result = router.generate("Summarize a fictional research task.")
    assert result["status"] == "MOCK"
    assert result["backend"] == "mock"
    assert result["mock_fallback"] is False


@pytest.mark.parametrize("kwargs", [
    {"prompt": ""},
    {"prompt": "valid", "max_tokens": 0},
    {"prompt": "valid", "max_tokens": 8193},
    {"prompt": "valid", "temperature": float("nan")},
    {"prompt": "valid", "temperature": 2.1},
])
def test_generation_rejects_invalid_bounds(kwargs: dict[str, object]) -> None:
    router = ClinicalLLMRouter(default_model="mock-clinical", backend="mock")
    with pytest.raises(ValueError):
        router.generate(**kwargs)


def test_remote_code_execution_is_disabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TMRDS_LLM_TRUST_REMOTE_CODE", raising=False)
    router = ClinicalLLMRouter(default_model="mock-clinical", backend="mock")
    assert router.trust_remote_code is False


def test_biocoder_preserves_mock_status_from_router() -> None:
    class MockRouter:
        def generate(self, prompt: str, **kwargs: object) -> dict[str, object]:
            return {
                "completion": "# mock output",
                "model": "test-model",
                "backend": "mock",
                "status": "MOCK",
                "mock_fallback": True,
                "fallback_reason": "model_load_failed",
            }

    result = BioCoderAssistant(llm_router=MockRouter()).generate_code("test task")
    assert result["status"] == "MOCK"
    assert result["mock_fallback"] is True
    assert result["fallback_reason"] == "model_load_failed"


def test_unconfigured_biocoder_is_explicitly_mock_only() -> None:
    assistant = BioCoderAssistant()
    result = assistant.generate_code("test task")
    assert result["status"] == "MOCK"
    assert result["backend"] == "mock"
    assert assistant.status()["status"] == "MOCK_ONLY"
