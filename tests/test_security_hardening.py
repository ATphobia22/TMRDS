from __future__ import annotations

import os

import pytest

from engines.hipaa_security_controls import HIPAASecurityControls
from engines.security_configuration import SecurityConfiguration


def test_production_configuration_requires_database_and_hmac(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TMRDS_ENV", "production")
    monkeypatch.delenv("TMRDS_DATABASE_URL", raising=False)
    monkeypatch.delenv("TMRDS_HMAC_SECRET", raising=False)
    with pytest.raises(RuntimeError, match="TMRDS_DATABASE_URL"):
        SecurityConfiguration.from_environment()


def test_production_configuration_rejects_weak_hmac(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TMRDS_ENV", "production")
    monkeypatch.setenv("TMRDS_DATABASE_URL", "postgresql://user:pass@db/tmrds")
    monkeypatch.setenv("TMRDS_HMAC_SECRET", "short")
    with pytest.raises(ValueError, match="TMRDS_HMAC_SECRET"):
        SecurityConfiguration.from_environment()


def test_password_hash_is_scrypt_and_round_trips() -> None:
    controls = HIPAASecurityControls(audit_path="/tmp/tmrds-security-test.jsonl", hmac_secret="x" * 32)
    encoded = controls._hash_password("correct horse battery staple")
    assert encoded.startswith("scrypt$")
    assert controls._verify_password("correct horse battery staple", encoded)
    assert not controls._verify_password("wrong", encoded)


def test_legacy_pbkdf2_hash_remains_verifiable() -> None:
    controls = HIPAASecurityControls(audit_path="/tmp/tmrds-security-test.jsonl", hmac_secret="x" * 32)
    legacy = "pbkdf2_sha256$600000$" + "00" * 16 + "$" + "00" * 32
    assert not controls._verify_password("anything", legacy)


def test_no_environment_password_means_no_configured_human_users(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TMRDS_CLINICIAN_PASSWORD", raising=False)
    monkeypatch.delenv("TMRDS_EMERGENCY_PIN", raising=False)
    controls = HIPAASecurityControls(audit_path="/tmp/tmrds-security-test.jsonl", hmac_secret="x" * 32)
    assert controls.status()["configured_users"] == []


def test_security_configuration_uses_explicit_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TMRDS_ENV", "production")
    monkeypatch.setenv("TMRDS_DATABASE_URL", "postgresql://user:pass@db/tmrds")
    monkeypatch.setenv("TMRDS_HMAC_SECRET", "x" * 32)
    config = SecurityConfiguration.from_environment()
    assert config.database_url == os.environ["TMRDS_DATABASE_URL"]
