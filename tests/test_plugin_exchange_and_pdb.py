from datetime import datetime, timezone
import httpx
import pytest
from fastapi.testclient import TestClient
from engines.plugin_record_exchange import preview_records
from engines.rcsb_pipeline import RCSBPipeline


def example(**overrides):
    row = dict(provider_id='amass', source_id='synthetic-record', source_url='https://example.org/record',
               retrieved_at=datetime.now(timezone.utc).isoformat(), summary='Synthetic public research metadata',
               clinical_promotion_allowed=False, human_authority_final=True)
    row.update(overrides)
    return row


def test_exchange_preserves_provenance_without_persistence():
    result = preview_records([example()])
    assert result['persisted'] is False and result['source_truth_verified'] is False
    assert len(result['records'][0]['record_sha256']) == 64
    assert result['records'][0]['status'] == 'UNREVIEWED_SOURCE_RECORD'


@pytest.mark.parametrize('record', [example(provider_id='health'), example(source_url='https://example.org/?token=synthetic'),
                                    example(source_url='https://example.org/#private'), example(api_key='synthetic'),
                                    example(patient_identifier='synthetic')])
def test_exchange_rejects_unsafe_metadata(record):
    with pytest.raises(ValueError):
        preview_records([record])


def test_duplicates_rejected():
    with pytest.raises(ValueError):
        preview_records([example(), example()])


@pytest.mark.asyncio
async def test_pdb_identity_and_experimental_metadata(monkeypatch):
    original = httpx.AsyncClient
    def response(request):
        assert str(request.url) == 'https://data.rcsb.org/rest/v1/core/entry/4HHB'
        return httpx.Response(200, json={'rcsb_id':'4HHB','struct':{'title':'Synthetic fixture'},'exptl':[{'method':'X-RAY DIFFRACTION'}]})
    monkeypatch.setattr('engines.rcsb_pipeline.httpx.AsyncClient', lambda **kw: original(transport=httpx.MockTransport(response), **kw))
    result = await RCSBPipeline().entry('4hhb')
    assert result['experimental_methods'] == ['X-RAY DIFFRACTION']
    assert result['clinical_promotion_allowed'] is False
    with pytest.raises(ValueError):
        await RCSBPipeline().entry('AF_PREDICTED')


@pytest.mark.asyncio
async def test_pdb_mismatched_record_rejected(monkeypatch):
    original = httpx.AsyncClient
    monkeypatch.setattr('engines.rcsb_pipeline.httpx.AsyncClient', lambda **kw: original(transport=httpx.MockTransport(lambda r: httpx.Response(200,json={'rcsb_id':'OTHER'})), **kw))
    with pytest.raises(ValueError):
        await RCSBPipeline().entry('4HHB')


def test_api_catalog_covers_requested_plugins_and_preview():
    from api.main import app
    with TestClient(app) as client:
        catalog = client.get('/api/v1/medical/plugin-capabilities').json()
        assert len(catalog['providers']) == 30
        assert all(p['free_backend_access'] == 'not_verified' for p in catalog['providers'])
        assert all(not p['automatic_execution_enabled'] for p in catalog['providers'])
        response = client.post('/api/v1/medical/research-records/preview',json={'public_research_metadata_only':True,'records':[example()]})
        assert response.status_code == 200 and not response.json()['persisted']
        assert client.post('/api/v1/medical/research-records/preview',json={'public_research_metadata_only':False,'records':[example()]}).status_code == 422
