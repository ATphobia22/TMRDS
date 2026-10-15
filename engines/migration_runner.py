"""Explicit, checksummed PostgreSQL migration runner.

Never runs on application import/startup. Existing untracked schemas require an
operator-reviewed baseline; migration files are never rewritten by this runner.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import asyncpg

MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"
MIGRATION_NAME = re.compile(r"(?P<version>[0-9]{3,})_[a-zA-Z0-9_-]+\.sql\Z")
LOCK_KEY = 7_419_220_261
LEDGER_TABLE = "tmrds_schema_migrations"
# These sentinels are deliberately minimal. Baseline is an operator assertion
# after checking the full schema, not an automatic schema-equivalence claim.
BASELINE_SENTINELS = {1: "evidence_sources", 2: "ai_models", 4: "quantum_job_submissions"}


class MigrationError(RuntimeError):
    """Safe, actionable migration failure."""


@dataclass(frozen=True, slots=True)
class MigrationFile:
    version: int
    name: str
    path: Path
    sha256: str


def discover_migrations(directory: Path = MIGRATIONS_DIR) -> list[MigrationFile]:
    """Return valid SQL migrations ordered by numeric version with checksums."""
    if not directory.is_dir():
        raise MigrationError(f"migration directory not found: {directory}")
    migrations: list[MigrationFile] = []
    versions: set[int] = set()
    for path in sorted(directory.iterdir(), key=lambda item: item.name):
        if path.is_dir():
            continue
        if path.suffix != ".sql":
            continue
        match = MIGRATION_NAME.fullmatch(path.name)
        if match is None:
            raise MigrationError(f"invalid migration filename: {path.name}")
        version = int(match.group("version"))
        if version in versions:
            raise MigrationError(f"duplicate migration version: {version}")
        versions.add(version)
        content = path.read_bytes()
        migrations.append(MigrationFile(
            version=version,
            name=path.name,
            path=path,
            sha256=hashlib.sha256(content).hexdigest(),
        ))
    return sorted(migrations, key=lambda migration: migration.version)


async def _connect() -> asyncpg.Connection:
    dsn = os.getenv("TMRDS_DATABASE_URL", "").strip()
    if not dsn:
        raise MigrationError("TMRDS_DATABASE_URL is required; no implicit database target is permitted")
    if os.getenv("TMRDS_ENV", "").casefold() == "production":
        if os.getenv("TMRDS_ALLOW_PRODUCTION_MIGRATIONS") != "true":
            raise MigrationError(
                "production migration target blocked; use the reviewed release procedure and explicit opt-in"
            )
    try:
        return await asyncpg.connect(dsn, timeout=10, command_timeout=60)
    except (OSError, asyncpg.PostgresError, TimeoutError) as exc:
        raise MigrationError("database connection failed; verify target and connectivity") from exc


async def _ensure_ledger(conn: asyncpg.Connection) -> None:
    await conn.execute(
        f"""CREATE TABLE IF NOT EXISTS {LEDGER_TABLE} (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            checksum_sha256 CHAR(64) NOT NULL
                CHECK (checksum_sha256 ~ '^[0-9a-f]{{64}}$'),
            applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )"""
    )


async def _table_exists(conn: asyncpg.Connection, table_name: str) -> bool:
    return bool(await conn.fetchval("SELECT to_regclass($1) IS NOT NULL", f"public.{table_name}"))


async def _read_applied(conn: asyncpg.Connection) -> dict[int, tuple[str, str]]:
    rows = await conn.fetch(
        f"SELECT version, name, checksum_sha256 FROM {LEDGER_TABLE} ORDER BY version"
    )
    return {int(row["version"]): (str(row["name"]), str(row["checksum_sha256"]).strip()) for row in rows}


async def status() -> int:
    migrations = discover_migrations()
    conn = await _connect()
    try:
        exists = await _table_exists(conn, LEDGER_TABLE)
        applied = await _read_applied(conn) if exists else {}
        known_versions = {migration.version for migration in migrations}
        unknown = sorted(set(applied) - known_versions)
        if unknown:
            raise MigrationError(f"ledger contains unknown migration versions: {unknown}")
        for migration in migrations:
            recorded = applied.get(migration.version)
            if recorded and recorded != (migration.name, migration.sha256):
                raise MigrationError(f"checksum/name drift detected for migration {migration.version}")
            state = "applied" if recorded else "pending"
            print(f"{migration.version:03d} {state} {migration.name}")
        if not exists and any([await _table_exists(conn, name) for name in BASELINE_SENTINELS.values()]):
            print("baseline_required: existing schema detected without a migration ledger")
        return 0
    finally:
        await conn.close()


async def upgrade() -> int:
    migrations = discover_migrations()
    conn = await _connect()
    lock_acquired = False
    try:
        await _ensure_ledger(conn)
        await conn.execute("SELECT pg_advisory_lock($1)", LOCK_KEY)
        lock_acquired = True
        applied = await _read_applied(conn)
        versions = {migration.version for migration in migrations}
        unknown = sorted(set(applied) - versions)
        if unknown:
            raise MigrationError(f"ledger contains unknown migration versions: {unknown}")
        for migration in migrations:
            recorded = applied.get(migration.version)
            if recorded is not None:
                if recorded != (migration.name, migration.sha256):
                    raise MigrationError(f"checksum/name drift detected for migration {migration.version}")
                continue
            if not applied:
                existing = [name for name in BASELINE_SENTINELS.values() if await _table_exists(conn, name)]
                if existing:
                    raise MigrationError(
                        "existing schema detected without migration history; inspect the full schema and "
                        "run the explicit baseline command before upgrade"
                    )
            async with conn.transaction():
                await conn.execute(migration.path.read_text(encoding="utf-8"))
                await conn.execute(
                    f"INSERT INTO {LEDGER_TABLE} (version, name, checksum_sha256) VALUES ($1, $2, $3)",
                    migration.version, migration.name, migration.sha256,
                )
            print(f"applied {migration.version:03d} {migration.name}")
            applied[migration.version] = (migration.name, migration.sha256)
        print("migration upgrade complete")
        return 0
    finally:
        if lock_acquired:
            try:
                await conn.execute("SELECT pg_advisory_unlock($1)", LOCK_KEY)
            except asyncpg.PostgresError:
                pass
        await conn.close()


async def baseline(through_version: int) -> int:
    """Record an operator-reviewed existing schema through a selected version."""
    migrations = discover_migrations()
    targets = [migration for migration in migrations if migration.version <= through_version]
    if not targets or targets[-1].version != through_version:
        raise MigrationError("baseline version must exactly match an existing migration")
    conn = await _connect()
    lock_acquired = False
    try:
        await _ensure_ledger(conn)
        await conn.execute("SELECT pg_advisory_lock($1)", LOCK_KEY)
        lock_acquired = True
        if await conn.fetchval(f"SELECT count(*) FROM {LEDGER_TABLE}"):
            raise MigrationError("baseline requires an empty migration ledger")
        missing = [
            name for version, name in BASELINE_SENTINELS.items()
            if version <= through_version and version in {migration.version for migration in targets}
            and not await _table_exists(conn, name)
        ]
        if missing:
            raise MigrationError(f"baseline schema sentinels missing: {missing}")
        print("WARNING: baseline records an operator assertion; verify every schema object and extension first.")
        for migration in targets:
            async with conn.transaction():
                await conn.execute(
                    f"INSERT INTO {LEDGER_TABLE} (version, name, checksum_sha256) VALUES ($1, $2, $3)",
                    migration.version, migration.name, migration.sha256,
                )
            print(f"baselined {migration.version:03d} {migration.name}")
        return 0
    finally:
        if lock_acquired:
            try:
                await conn.execute("SELECT pg_advisory_unlock($1)", LOCK_KEY)
            except asyncpg.PostgresError:
                pass
        await conn.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("status", help="show applied and pending migrations")
    subparsers.add_parser("upgrade", help="apply pending migrations in order")
    baseline_parser = subparsers.add_parser("baseline", help="record an operator-reviewed existing schema")
    baseline_parser.add_argument("--through", type=int, required=True, help="existing migration version to baseline")
    args = parser.parse_args(argv)
    try:
        if args.command == "status":
            return asyncio.run(status())
        if args.command == "upgrade":
            return asyncio.run(upgrade())
        return asyncio.run(baseline(args.through))
    except MigrationError as exc:
        print(f"migration error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
