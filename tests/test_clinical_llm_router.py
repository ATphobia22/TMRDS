from __future__ import annotations

import pytest

from engines.clinical_llm_router import ClinicalLLMRouter


def test_default_router_explicitly_reports_mock_only() -> None:
    router = ClinicalLLMRouter()
    result = router.generate("Summarize evidence provenance.")

    assert result["status"] == "MOCK_ONLY"
    assert result["inference_executed"] is False
    assert result["backend"] == "mock"
    assert "no language-model inference was performed" in result["completion"]
    assert result["human_review_required"] is True
    assert router.backend_status()["status"] == "MOCK_ONLY"


@pytest.mark.parametrize("max_tokens", [0, -1, 8193, True])
def test_invalid_max_tokens_are_rejected(max_tokens: int) -> None:
    with pytest.raises(ValueError, match="max_tokens"):
        ClinicalLLMRouter().generate("test", max_tokens=max_tokens)


@pytest.mark.parametrize("temperature", [-0.1, 2.1, float("nan"), float("inf")])
def test_invalid_temperature_is_rejected(temperature: float) -> None:
    with pytest.raises(ValueError, match="temperature"):
        ClinicalLLMRouter().generate("test", temperature=temperature)


def test_empty_prompt_is_rejected() -> None:
    with pytest.raises(ValueError, match="prompt"):
        ClinicalLLMRouter().generate("  ")
