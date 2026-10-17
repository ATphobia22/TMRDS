from __future__ import annotations

from pathlib import Path

from scripts.check_dependency_lock import validate_dependency_locks, validate_pair


def _write_pair(root: Path, requirements: str, lock: str) -> None:
    (root / "requirements.txt").write_text(requirements, encoding="utf-8")
    (root / "requirements.lock").write_text(lock, encoding="utf-8")
    (root / "requirements-runtime.txt").write_text(requirements, encoding="utf-8")
    (root / "requirements-runtime.lock").write_text(lock, encoding="utf-8")
    (root / "requirements-lock.txt").write_text(lock, encoding="utf-8")
    (root / "requirements-runtime-lock.txt").write_text(lock, encoding="utf-8")


def test_dependency_locks_validate_when_pairs_and_aliases_match(tmp_path: Path) -> None:
    _write_pair(tmp_path, "fastapi>=0.100\n", "fastapi==0.115.0\n")
    assert validate_dependency_locks(tmp_path) == []


def test_dependency_lock_detects_missing_pin(tmp_path: Path) -> None:
    _write_pair(tmp_path, "fastapi>=0.100\nhttpx>=0.27\n", "fastapi==0.115.0\n")
    failures, _ = validate_pair(tmp_path, "requirements.txt", "requirements.lock")
    assert any("httpx is missing" in issue for issue in failures)


def test_dependency_lock_detects_pin_outside_declared_range(tmp_path: Path) -> None:
    _write_pair(tmp_path, "numpy>=2.5.0\n", "numpy==2.4.6\n")
    failures, _ = validate_pair(tmp_path, "requirements.txt", "requirements.lock")
    assert any("does not satisfy" in issue for issue in failures)


def test_dependency_lock_rejects_non_exact_duplicate_or_invalid_pin(tmp_path: Path) -> None:
    (tmp_path / "requirements.lock").write_text("fastapi>=0.1\nfastapi==0.115.0\n", encoding="utf-8")
    failures, _ = validate_pair(tmp_path, "requirements.txt", "requirements.lock")
    assert any("exact == pins" in issue for issue in failures)
    (tmp_path / "requirements.lock").write_text("fastapi==0.115.0\nFastAPI==0.116.0\n", encoding="utf-8")
    failures, _ = validate_pair(tmp_path, "requirements.txt", "requirements.lock")
    assert any("duplicate lock entry" in issue for issue in failures)


def test_dependency_lock_detects_stale_legacy_alias(tmp_path: Path) -> None:
    _write_pair(tmp_path, "fastapi>=0.100\n", "fastapi==0.115.0\n")
    (tmp_path / "requirements-lock.txt").write_text("fastapi==0.116.0\n", encoding="utf-8")
    failures = validate_dependency_locks(tmp_path)
    assert any("requirements-lock.txt must be byte-identical" in issue for issue in failures)


def test_dependency_lock_detects_shared_runtime_pin_mismatch(tmp_path: Path) -> None:
    _write_pair(tmp_path, "fastapi>=0.100\n", "fastapi==0.115.0\n")
    (tmp_path / "requirements-runtime.lock").write_text("fastapi==0.116.0\n", encoding="utf-8")
    (tmp_path / "requirements-runtime-lock.txt").write_text("fastapi==0.116.0\n", encoding="utf-8")
    failures = validate_dependency_locks(tmp_path)
    assert any("shared direct dependency fastapi differs" in issue for issue in failures)
