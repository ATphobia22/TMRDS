"""Unit tests for QRCE exact-ID metadata matching and FDA patent source claims."""
from __future__ import annotations

import asyncio
import re
from datetime import datetime, timezone

import httpx
from fastapi.testclient import TestClient

from api.public_gateway import app
from api.public_crosscheck_routes import (
    _parse_orangebook_response, lookup_fda_patent_metadata, validate_public_query,
)
from engines.federated_evidence_search import SourceResult
from engines.qrce_public_crosscheck import build_crosscheck


def envelope(source, stable, **extra):
    return {"stable_id": source + ":" + stable, "source": source,
            "is_mock": False, "title": "A real publication", "record_hash": "b" * 64,
            "retrieved_at": "2026-11-23T06:00:00Z", **extra}


def test_exact_doi_and_pmid_link_two_sources_but_not_replication():
    results = [
        SourceResult(source="europe_pmc", ok=True, count=1,
                     envelopes=[envelope("europe_pmc", "one", doi="https://doi.org/10.1000/xyz",
                                         pmid="38718835", abstract="licensed full-text")]),
        SourceResult(source="pubmed", ok=True, count=1,
                     envelopes=[envelope("pubmed", "two", pmid="38718835")]),
        SourceResult(source="crossref", ok=True, count=1,
                     envelopes=[envelope("crossref", "three", doi="10.1000/xyz")]),
    ]
    value = build_crosscheck("AlphaFold", results, expected_sources=("europe_pmc", "pubmed", "crossref"))
    assert value["group_count"] == 1
    assert value["record_count"] == 3
    group = value["groups"][0]
    assert group["exact_identifiers"] == ["doi:10.1000/xyz", "pmid:38718835"]
    assert group["sources"] == ["crossref", "europe_pmc", "pubmed"]
    assert group["independent_replication_verified"] is False
    assert group["interpretation"] == "cross_index_metadata_overlap_only"
    assert all("abstract" not in row for row in group["source_records"])
    assert value["clinical_promotion_allowed"] is False
    assert value["openmi_inspired_exchange"]["conformance"] == "NOT_CONFORMANCE_TESTED"
    assert value["openmi_inspired_exchange"]["clinical_data_included"] is False
    assert len(value["snapshot_sha256"]) == 64


def test_disagreements_outages_fake_records_and_fuzzy_title_match_are_not_collapsed():
    results = [
        SourceResult("pubmed", ok=True, count=2, envelopes=[
            envelope("pubmed", "one", pmid="123", title="Shared title", published="2022"),
            envelope("pubmed", "two", pmid="456", title="Shared title", published="2023"),
            envelope("pubmed", "fake", pmid="777", is_mock=True),
        ]),
        SourceResult("crossref", ok=False, warning="source error",
                     envelopes=[envelope("crossref", "bad", pmid="123")]),
    ]
    # Replacing the is_mock field is intentional: fake records must be discarded.
    result = build_crosscheck("example", results, expected_sources=("pubmed", "crossref", "uniprot"))
    assert result["group_count"] == 2
    assert result["record_count"] == 2
    assert result["metadata_overlap_groups"] == 0
    assert result["source_status"]["crossref"]["state"] == "source_unavailable"
    assert result["source_status"]["uniprot"]["state"] == "not_queried"
    assert result["openmi_inspired_exchange"]["items"][0]["unit"] == "1"


def test_malformed_source_ids_and_claimed_physical_quantum_sources_rejected():
    result = build_crosscheck("test", [
        SourceResult("pubmed", ok=True, count=3, envelopes=[
            {"stable_id": "other:wrong", "source": "pubmed", "pmid": "1"},
            {"stable_id": "pubmed:fake", "source": "pubmed", "is_mock": True},
            envelope("pubmed", "real", pmid="not_a_pmid", doi="not-a-doi"),
        ]),
    ], expected_sources=("pubmed",))
    assert result["record_count"] == 1
    assert result["groups"][0]["exact_identifiers"] == []
    assert result["patent_freedom_to_operate"] == "not_determined"


def test_fda_response_returns_reported_pediatric_extension_without_legal_clearance():
    payload = {"meta": {"last_updated": "2026-11-20"}, "results": [{
        "approval_date": "20120202",
        "products": [{
            "application_number": "202270", "application_type": "N",
            "brand_name": "JANUMET XR",
            "active_ingredients": [{"name": "METFORMIN HYDROCHLORIDE"}],
        }],
        "patents": [
            {"patent_number": "7326708", "expiration_date": "20261124"},
            {"patent_number": "7326708*PED", "expiration_date": "20270524"},
        ],
    }]}
    output = _parse_orangebook_response(payload, "METFORMIN", limit=3, as_of="2026-11-23",
                                        retrieved_at="2026-11-23T07:00:00+00:00")
    assert output["source_updated_at"] == "2026-11-20"
    assert output["record_count"] == 1
    patents = output["records"][0]["patents"]
    assert patents[0]["date_relation"] == "listed_date_follows_lookup"
    assert patents[1]["pediatric_extension_marker"] is True
    assert patents[1]["legal_status"] == "UNVERIFIED"
    assert output["patent_freedom_to_operate"] == "NOT_DETERMINED"
    assert output["expired_public_domain_claim"] is False
    assert output["federal_patent_database_checked"] is False


def test_fda_fixed_upstream_origin_and_missing_source_are_distinguished():
    captured = []
    def response(request: httpx.Request):
        captured.append(str(request.url))
        assert request.url.host == "api.fda.gov"
        assert request.url.path == "/drug/orangebook.json"
        return httpx.Response(200, json={"meta": {"last_updated": "2026-11-20"}, "results": []})
    data = asyncio.run(lookup_fda_patent_metadata("Metformin", transport=httpx.MockTransport(response)))
    assert data["status"] == "no_relevant_records_on_page"
    assert len(captured) == 1
    assert "products.active_ingredients.name" in captured[0]
    no_matches = asyncio.run(lookup_fda_patent_metadata(
        "Metformin", transport=httpx.MockTransport(lambda _: httpx.Response(404))))
    assert no_matches["status"] == "no_matches_reported_by_fda"
    unavailable = asyncio.run(lookup_fda_patent_metadata(
        "Metformin", transport=httpx.MockTransport(
            lambda _: httpx.Response(302, headers={"location": "http://127.0.0.1:80/secret"}))))
    assert unavailable["status"] == "source_unavailable"
    assert unavailable["records"] == []


def test_oversized_and_bad_patent_upstream_data_are_rejected():
    for raw in (b"x" * (1_048_576 + 1), b'{"results": "not-an-array"}', b"no-json"):
        response = lambda request, body=raw: httpx.Response(200, content=body)
        result = asyncio.run(lookup_fda_patent_metadata(
            "metformin", transport=httpx.MockTransport(response)))
        assert result["status"] == "source_unavailable"
    for input_value in ("..", "http://example.com", "METFORMIN:evil", "test@domain.com", "M" * 80):
        try:
            asyncio.run(lookup_fda_patent_metadata(input_value))
        except ValueError:
            pass
        else:
            raise AssertionError("unexpected acceptance of invalid term")


def test_public_routes_are_read_only_and_phrases_reject_pii():
    client = TestClient(app)
    for val in ("123-45-6789", "test@example.org"):
        try:
            validate_public_query(val)
        except ValueError:
            pass
        else:
            raise AssertionError("personal identifier accepted for public query")
    assert client.get("/api/v1/research/patent-landscape", params={"ingredient": "../user"}).status_code == 422
    assert client.get("/api/v1/research/cross-check", params={"query": "test@example.org"}).status_code == 422
    for route in app.routes:
        if route.path.startswith("/api/v1/research/"):
            assert getattr(route, "methods", set()) <= {"GET", "HEAD"}


def test_12_source_crosscheck_is_fully_wired_with_per_source_status(monkeypatch):
    queried = []
    async def mocked_guard(self, source, coro):
        coro.close()
        queried.append(source)
        if source == "europe_pmc":
            return SourceResult(source, True, envelopes=[envelope(source, "record", pmid="123")], count=1)
        return SourceResult(source, False, warning="unavailable in unit test")
    monkeypatch.setattr("api.public_crosscheck_routes.FederatedEvidenceSearch._guard", mocked_guard)
    client = TestClient(app)
    response = client.get("/api/v1/research/cross-check", params={"query": "ALS", "limit": 1})
    assert response.status_code == 200
    data = response.json()
    assert len(set(queried)) == 12
    assert data["status"] == "records_retrieved"
    assert data["group_count"] == 1
    assert data["source_status"]["pubmed"]["state"] == "source_unavailable"
    assert data["source_status"]["europe_pmc"]["state"] == "responding"
    assert data["source_licensing"]["crossref"]["bulk_redistribution_allowed"] is False
    assert data["human_authority_final"] is True
