from __future__ import annotations

from fastapi import HTTPException

from api.error_responses import safe_upstream_error


def test_safe_upstream_error_uses_stable_public_contract() -> None:
    secret_detail = "Authorization: Bearer extremely-sensitive-token"
    error = safe_upstream_error("CDC", secret_detail)

    assert isinstance(error, HTTPException)
    assert error.status_code == 502
    assert error.detail == {
        "code": "UPSTREAM_FAILURE",
        "message": "CDC upstream request failed.",
    }
    assert secret_detail not in str(error.detail)


def test_safe_upstream_error_rejects_untrusted_service_label() -> None:
    error = safe_upstream_error("CDC\nAuthorization", "secret")

    assert error.detail == {
        "code": "UPSTREAM_FAILURE",
        "message": "Upstream request failed.",
    }
