from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from api import main


class FakeConnection:
    def __init__(self, schema_ready: bool) -> None:
        self.schema_ready = schema_ready

    async def fetchval(self, _query: str) -> bool:
        return self.schema_ready


class FakeAcquire:
    def __init__(self, connection: FakeConnection) -> None:
        self.connection = connection

    async def __aenter__(self) -> FakeConnection:
        return self.connection

    async def __aexit__(self, *_args: object) -> None:
        return None


class FakePool:
    def __init__(self, schema_ready: bool) -> None:
        self.connection = FakeConnection(schema_ready)

    def acquire(self) -> FakeAcquire:
        return FakeAcquire(self.connection)


@pytest.mark.asyncio
async def test_liveness_does_not_require_external_dependencies() -> None:
    assert await main.liveness() == {"status": "alive"}


@pytest.mark.asyncio
async def test_readiness_requires_evidence_schema(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(main.evidence_repository, "_pool", AsyncMock(return_value=FakePool(False)))

    with pytest.raises(HTTPException) as exc_info:
        await main.readiness()

    assert exc_info.value.status_code == 503
    assert "evidence_sources" not in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_readiness_returns_ready_when_evidence_schema_exists(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(main.evidence_repository, "_pool", AsyncMock(return_value=FakePool(True)))

    assert await main.readiness() == {"status": "ready"}


@pytest.mark.asyncio
async def test_readiness_sanitizes_database_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        main.evidence_repository, "_pool",
        AsyncMock(side_effect=RuntimeError("secret database connection detail")),
    )

    with pytest.raises(HTTPException) as exc_info:
        await main.readiness()

    assert exc_info.value.status_code == 503
    assert "secret database connection detail" not in str(exc_info.value.detail)
