import httpx
import pytest
from engines.source_telemetry import SourceMonitor

@pytest.mark.asyncio
async def test_missing_credentials_and_unknown_balance(monkeypatch):
    monkeypatch.delenv('TAMARIND_API_KEY', raising=False)
    monitor = SourceMonitor()
    assert monitor.snapshot()['upstream_sources']['tamarind']['status'] == 'not_checked'
    assert (await monitor.probe('tamarind'))['status'] == 'auth_blocked'
    assert (await monitor.probe('patsnap'))['status'] == 'not_configured'

@pytest.mark.asyncio
async def test_circuit_and_no_credential_leak(monkeypatch):
    original = httpx.AsyncClient
    calls = []
    def respond(request):
        calls.append(request)
        assert str(request.url) == 'https://app.tamarind.bio/api/tools'
        return httpx.Response(503, text='must never be returned')
    monkeypatch.setenv('TAMARIND_API_KEY', 'synthetic-test-value')
    monkeypatch.setattr('engines.source_telemetry.httpx.AsyncClient', lambda **kw: original(transport=httpx.MockTransport(respond), **kw))
    monitor = SourceMonitor()
    for _ in range(3):
        assert (await monitor.probe('tamarind'))['status'] == 'degraded'
    assert (await monitor.probe('tamarind'))['status'] == 'circuit_open'
    assert len(calls) == 3
    assert 'synthetic-test-value' not in str(monitor.snapshot())
    assert 'must never' not in str(monitor.snapshot())

def test_catalog_route_and_schema():
    from api.main import app
    from fastapi.testclient import TestClient
    from engines.source_telemetry import SourceCatalog
    import json
    from pathlib import Path
    with TestClient(app) as client:
        result = client.get('/api/v1/sources/catalog')
        assert result.status_code == 200
        assert result.json()['telemetry_scope'] == 'process_local'
        assert client.post('/api/v1/sources/unknown/probe').status_code == 422
    assert json.loads(Path('config/source_catalog.json').read_text()) == SourceCatalog.model_json_schema()
