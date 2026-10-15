from __future__ import annotations

import pytest

from api.main import liveness


@pytest.mark.asyncio
async def test_liveness_reports_process_health_without_dependency_checks() -> None:
    assert await liveness() == {"status": "alive"}
