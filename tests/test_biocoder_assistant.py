from __future__ import annotations

from typing import Any

import pytest

from engines.biocoder_assistant import BioCoderAssistant


class FakeRouter:
    def __init__(self, result: dict[str, Any]) -> None:
        self.result = result

    def generate(self, prompt: str, **kwargs: Any) -> dict[str, Any]:
        assert "Domain: sequence_analysis" in prompt
        assert kwargs["max_tokens"] == 1024
        return self.result


def test_unconfigured_backend_does_not_fabricate_code() -> None:
    assistant = BioCoderAssistant()

    result = assistant.generate_code("Parse a FASTA file")

    assert result["status"] == "UNAVAILABLE"
    assert result["completion"] is None
    assert result["review_required"] is True
    assert assistant.status()["status"] == "UNAVAILABLE"


def test_real_router_completion_is_reported_as_generated() -> None:
    assistant = BioCoderAssistant(
        FakeRouter({"completion": "def solve() -> int:\n    return 1", "model": "test-model", "backend": "test"})
    )

    result = assistant.generate_code("Return a constant")

    assert result["status"] == "GENERATED"
    assert result["completion"].startswith("def solve")
    assert result["review_required"] is True


def test_mock_router_is_not_reported_as_real_generation() -> None:
    assistant = BioCoderAssistant(
        FakeRouter({"completion": "mock output", "model": "mock-clinical", "backend": "mock"})
    )

    result = assistant.generate_code("Return a constant")

    assert result["status"] == "MOCK"
    assert result["reason"] is not None


def test_empty_task_is_rejected() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        BioCoderAssistant().generate_code("  ")


def test_unknown_domain_is_rejected() -> None:
    with pytest.raises(ValueError, match="unsupported domain"):
        BioCoderAssistant().generate_code("Parse FASTA", domain="unknown")


def test_router_failure_does_not_leak_exception_message() -> None:
    class BrokenRouter:
        def generate(self, prompt: str, **kwargs: Any) -> dict[str, Any]:
            raise RuntimeError("secret-like internal detail")

    result = BioCoderAssistant(BrokenRouter()).generate_code("Parse FASTA")

    assert result["status"] == "ERROR"
    assert "secret-like internal detail" not in str(result)
