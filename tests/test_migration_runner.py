from __future__ import annotations

import hashlib
from unittest.mock import AsyncMock

import pytest

from engines import migration_runner
from engines.migration_runner import MigrationError, discover_migrations


def test_discover_migrations_orders_numeric_versions_and_hashes_content(tmp_path) -> None:
    (tmp_path / "004_quantum.sql").write_text("SELECT 4;\n", encoding="utf-8")
    (tmp_path / "001_core.sql").write_text("SELECT 1;\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("ignored", encoding="utf-8")

    migrations = discover_migrations(tmp_path)

    assert [migration.version for migration in migrations] == [1, 4]
    assert migrations[0].name == "001_core.sql"
    assert migrations[0].sha256 == hashlib.sha256(b"SELECT 1;\n").hexdigest()


def test_discover_migrations_rejects_duplicate_versions(tmp_path) -> None:
    (tmp_path / "001_core.sql").write_text("SELECT 1;", encoding="utf-8")
    (tmp_path / "001_other.sql").write_text("SELECT 2;", encoding="utf-8")

    with pytest.raises(MigrationError, match="duplicate migration version"):
        discover_migrations(tmp_path)


def test_discover_migrations_rejects_invalid_sql_migration_names(tmp_path) -> None:
    (tmp_path / "migration.sql").write_text("SELECT 1;", encoding="utf-8")

    with pytest.raises(MigrationError, match="invalid migration filename"):
        discover_migrations(tmp_path)


def test_repository_migrations_have_unique_numeric_versions() -> None:
    from engines.migration_runner import BASELINE_SENTINELS, MIGRATIONS_DIR

    migrations = discover_migrations(MIGRATIONS_DIR)
    versions = [migration.version for migration in migrations]

    assert versions == sorted(set(versions))
    assert {1, 2, 3, 4}.issubset(set(versions))
    assert BASELINE_SENTINELS[3] == "data_fabric_sources"



@pytest.mark.asyncio
async def test_production_migration_status_is_read_only_and_does_not_need_write_opt_in(monkeypatch) -> None:
    connection = object()
    connect = AsyncMock(return_value=connection)
    monkeypatch.setattr(migration_runner.asyncpg, "connect", connect)
    monkeypatch.setenv("TMRDS_DATABASE_URL", "postgresql://example.invalid/tmrds")
    monkeypatch.setenv("TMRDS_ENV", "production")
    monkeypatch.delenv("TMRDS_ALLOW_PRODUCTION_MIGRATIONS", raising=False)

    assert await migration_runner._connect() is connection
    connect.assert_awaited_once()


@pytest.mark.asyncio
async def test_production_migration_writes_require_explicit_opt_in(monkeypatch) -> None:
    connect = AsyncMock()
    monkeypatch.setattr(migration_runner.asyncpg, "connect", connect)
    monkeypatch.setenv("TMRDS_DATABASE_URL", "postgresql://example.invalid/tmrds")
    monkeypatch.setenv("TMRDS_ENV", "production")
    monkeypatch.delenv("TMRDS_ALLOW_PRODUCTION_MIGRATIONS", raising=False)

    with pytest.raises(MigrationError, match="production migration target blocked"):
        await migration_runner._connect(require_production_opt_in=True)
    connect.assert_not_awaited()
