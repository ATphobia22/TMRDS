"""Tests for api.ops (metrics, rate limiting, security headers) and api.api_key_auth."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from api import ops
from api.api_key_auth import (
    ApiKeyConfigurationUnavailableMiddleware,
    ApiKeyGateMiddleware,
    check_startup_posture,
    load_api_keys,
)
from api.ops import SecurityHeadersMiddleware, setup_metrics, setup_rate_limiting


def _mini_app() -> FastAPI:
    app = FastAPI()

    @app.get("/ping")
    async def ping() -> dict[str, str]:
        return {"status": "ok"}

    return app


def test_metrics_endpoint_exposed_when_available() -> None:
    pytest.importorskip("prometheus_fastapi_instrumentator")
    app = _mini_app()
    assert setup_metrics(app) is True
    client = TestClient(app)
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "http_requests_total" in resp.text or "process_" in resp.text


def test_rate_limit_returns_429_with_retry_after_and_sanitized_shape() -> None:
    pytest.importorskip("slowapi")
    app = _mini_app()

    @app.get("/tight")
    @ops.limiter.limit("2/minute")
    async def tight(request: Request) -> dict[str, str]:
        return {"status": "ok"}

    assert setup_rate_limiting(app) is True
    client = TestClient(app)
    assert client.get("/tight").status_code == 200
    assert client.get("/tight").status_code == 200
    resp = client.get("/tight")
    assert resp.status_code == 429
    assert resp.headers.get("Retry-After") is not None
    body = resp.json()
    assert body["detail"]["code"] == "RATE_LIMITED"
    # sanitized: no internal detail leaked
    assert "slowapi" not in body["detail"]["message"].lower()


def test_security_headers_present() -> None:
    app = _mini_app()
    app.add_middleware(SecurityHeadersMiddleware)
    client = TestClient(app)
    resp = client.get("/ping")
    assert resp.headers["x-content-type-options"] == "nosniff"
    assert resp.headers["x-frame-options"] == "DENY"
    assert resp.headers["referrer-policy"] == "no-referrer"


def _write_key_file(tmp_path: Path, secret: str = "s3cret-value_123", key_id: str = "doc001") -> Path:
    digest = hashlib.sha256(secret.encode()).hexdigest()
    path = tmp_path / "keys.txt"
    path.write_text(f"# comment line\n\n{key_id}:{digest}\n", encoding="utf-8")
    return path


def test_load_api_keys_ok_and_strict(tmp_path: Path) -> None:
    path = _write_key_file(tmp_path)
    keys = load_api_keys(str(path))
    assert list(keys) == ["doc001"]
    assert len(keys["doc001"]) == 64

    bad = tmp_path / "bad.txt"
    bad.write_text("not-a-valid-line\n", encoding="utf-8")
    with pytest.raises(RuntimeError):
        load_api_keys(str(bad))

    with pytest.raises(RuntimeError):
        load_api_keys(str(tmp_path / "missing.txt"))

    empty = tmp_path / "empty.txt"
    empty.write_text("# only comments\n", encoding="utf-8")
    with pytest.raises(RuntimeError):
        load_api_keys(str(empty))


def _gated_app(keys: dict[str, str]) -> FastAPI:
    app = FastAPI()
    app.add_middleware(ApiKeyGateMiddleware, keys=keys)

    @app.get("/api/v1/research/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/live")
    async def live() -> dict[str, str]:
        return {"status": "alive"}

    return app


def test_api_key_gate_allows_valid_key_and_denies_without_leak(tmp_path: Path) -> None:
    secret = "s3cret-value_123"
    keys = load_api_keys(str(_write_key_file(tmp_path, secret=secret)))
    client = TestClient(_gated_app(keys))

    # health stays open
    assert client.get("/health/live").status_code == 200

    # missing key
    resp = client.get("/api/v1/research/health")
    assert resp.status_code == 401
    assert resp.json()["detail"]["code"] == "UNAUTHORIZED"
    assert secret not in resp.text

    # wrong key
    resp = client.get("/api/v1/research/health", headers={"x-api-key": "tmrds_doc001_wrongsecret000"})
    assert resp.status_code == 401

    # valid key
    resp = client.get("/api/v1/research/health", headers={"x-api-key": f"tmrds_doc001_{secret}"})
    assert resp.status_code == 200


def test_startup_posture_open_by_default_and_fail_closed_on_invalid_config(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """An explicitly configured invalid key file must never disable the key gate."""
    monkeypatch.delenv("TMRDS_API_KEYS_FILE", raising=False)
    posture = check_startup_posture()
    assert posture["auth"] == "open"
    assert posture["keys"] is None

    monkeypatch.setenv("TMRDS_API_KEYS_FILE", str(tmp_path / "nope.txt"))
    posture = check_startup_posture()
    assert posture["auth"] == "unavailable"
    assert posture["keys"] is None
    assert "warning" in posture
    assert str(tmp_path) not in posture["warning"]

    bad = tmp_path / "bad.txt"
    bad.write_text("garbage\n", encoding="utf-8")
    monkeypatch.setenv("TMRDS_API_KEYS_FILE", str(bad))
    posture = check_startup_posture()
    assert posture["auth"] == "unavailable"
    assert "warning" in posture

    monkeypatch.setenv("TMRDS_API_KEYS_FILE", str(_write_key_file(tmp_path)))
    posture = check_startup_posture()
    assert posture["auth"] == "key-gated"
    assert posture["keys"] == {"doc001": hashlib.sha256(b"s3cret-value_123").hexdigest()}


def test_invalid_key_configuration_returns_503_without_leaking_details() -> None:
    app = _mini_app()

    @app.get("/api/v1/research/health")
    async def protected() -> dict[str, str]:
        return {"status": "should-not-be-served"}

    app.add_middleware(ApiKeyConfigurationUnavailableMiddleware)
    client = TestClient(app)

    response = client.get("/api/v1/research/health")
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "AUTH_UNAVAILABLE"
    assert response.headers["cache-control"] == "no-store"
    assert "TMRDS_API_KEYS_FILE" not in response.text
    assert client.get("/ping").status_code == 200


def test_main_app_wires_ops_without_import_side_effects() -> None:
    # Importing api.main must not raise even with no keys configured.
    os.environ.pop("TMRDS_API_KEYS_FILE", None)
    from api import main as main_module

    assert isinstance(ops.metrics_enabled(), bool)
    assert isinstance(ops.rate_limiting_enabled(), bool)
    assert main_module.app.state.ops_posture["auth"] in {"open", "key-gated", "unavailable"}


def test_retry_after_parsing() -> None:
    class FakeExc:
        detail = "Rate limit exceeded: 20 per 1 minute"

    assert ops._retry_after_seconds(FakeExc()) == 60  # type: ignore[arg-type]

    class FakeExc2:
        detail = "Rate limit exceeded: 5 per 1 hour"

    assert ops._retry_after_seconds(FakeExc2()) == 3600  # type: ignore[arg-type]

    class FakeExc3:
        detail = "unparseable"

    assert ops._retry_after_seconds(FakeExc3()) == 60  # type: ignore[arg-type]


def test_api_key_gate_rejects_duplicate_case_insensitive_headers(tmp_path: Path) -> None:
    secret = "s3cret-value_123"
    keys = load_api_keys(str(_write_key_file(tmp_path, secret=secret)))
    client = TestClient(_gated_app(keys))
    valid = f"tmrds_doc001_{secret}"
    response = client.get(
        "/api/v1/research/health",
        headers=[("X-API-Key", valid), ("x-api-key", valid)],
    )
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "UNAUTHORIZED"


def test_api_key_gate_does_not_log_sensitive_path(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    secret = "s3cret-value_123"
    keys = load_api_keys(str(_write_key_file(tmp_path, secret=secret)))
    app = _gated_app(keys)

    @app.get("/api/private/{patient_identifier}")
    async def lookup(patient_identifier: str) -> dict[str, str]:
        return {"status": "ok"}

    client = TestClient(app)
    with caplog.at_level("INFO", logger="tmrds.auth"):
        response = client.get(
            "/api/private/synthetic-patient-identifier",
            headers={"X-API-Key": f"tmrds_doc001_{secret}"},
        )
    assert response.status_code == 200
    auth_messages = [record.getMessage() for record in caplog.records if record.name == "tmrds.auth"]
    assert any("auth allow key_id=doc001" in message for message in auth_messages)
    assert all("synthetic-patient-identifier" not in message for message in auth_messages)


def test_api_key_gate_rejects_oversized_credential(tmp_path: Path) -> None:
    keys = load_api_keys(str(_write_key_file(tmp_path)))
    response = TestClient(_gated_app(keys)).get(
        "/api/v1/research/health",
        headers={"X-API-Key": "tmrds_doc001_" + "a" * 1000},
    )
    assert response.status_code == 401
