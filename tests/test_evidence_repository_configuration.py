from __future__ import annotations

import pytest

from engines.evidence_graph_repository import EvidenceGraphRepository


def test_repository_can_be_imported_without_database_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TMRDS_DATABASE_URL", raising=False)
    repository = EvidenceGraphRepository()
    assert repository.dsn is None


@pytest.mark.asyncio
async def test_repository_fails_closed_when_connecting_without_database_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TMRDS_DATABASE_URL", raising=False)
    repository = EvidenceGraphRepository()
    with pytest.raises(RuntimeError, match="TMRDS_DATABASE_URL"):
        await repository.connect()
