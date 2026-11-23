"""Contract-first checks for public research disease → target → compound links."""
from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from engines.governed_pathway import (
    PathwaySourceError,
    PathwaySourceClient,
    evaluate_license,
    evaluate_freshness,
    normalize_pathway,
    validate_reference_pathways,
    load_reference_pathways,
)

NOW = datetime(2026, 11, 23, tzinfo=timezone.utc)
FIXTURE = {
    "meta": {"dataVersion": {"year": 26, "month": 9, "iteration": 0}},
    "disease": {
        "id": "MONDO_0009061", "name": "cystic fibrosis",
        "associatedTargets": {"count": 2, "rows": [
            {"score": .93, "target": {"id": "ENSG00000001626", "approvedSymbol": "CFTR"}},
            {"score": .10, "target": {"id": "ENSG00000141510", "approvedSymbol": "TP53"}},
        ]},
        "drugAndClinicalCandidates": {"count": 2, "rows": [
            {"maxClinicalStage": "APPROVAL", "drug": {
                "id": "CHEMBL2010601", "name": "IVACAFTOR",
                "mechanismsOfAction": {"rows": [
                    {"actionType": "POTENTIATOR", "mechanismOfAction": "CFTR potentiator",
                     "targets": [{"id": "ENSG00000001626", "approvedSymbol": "CFTR"}]}
                ]}}},
            {"maxClinicalStage": "PHASE_2", "drug": {
                "id": "CHEMBL25", "name": "ASPIRIN",
                "mechanismsOfAction": {"rows": [
                    {"actionType": "INHIBITOR", "mechanismOfAction": "different target",
                     "targets": [{"id": "ENSG99999999999", "approvedSymbol": "OTHER"}]}
                ]}}},
        ]},
    },
}


def test_freshness_is_request_scoped_and_never_implies_upstream_release_is_current():
    fresh = evaluate_freshness(NOW.isoformat(), now=NOW + timedelta(hours=2), release="26.09")
    assert fresh["retrieval"] == "fresh"
    assert fresh["upstream_release"] == "observed_not_independently_verified"
    assert evaluate_freshness(None, now=NOW)["retrieval"] == "unknown"
    assert evaluate_freshness(NOW.isoformat(), now=NOW + timedelta(days=5))["retrieval"] == "stale"
    assert evaluate_freshness((NOW + timedelta(days=1)).isoformat(), now=NOW)["retrieval"] == "invalid_future_timestamp"


def test_license_review_never_equates_public_api_with_bulk_redistribution():
    known = evaluate_license("opentargets", now=NOW)
    assert known["metadata_display_allowed"] is True
    assert known["bulk_redistribution_allowed"] is False
    assert known["requires_human_license_review"] is True
    assert evaluate_license("unknown-provider")["metadata_display_allowed"] is False
    assert evaluate_license("chembl")["attribution_required"] is True
    assert evaluate_license("opentargets", now=NOW + timedelta(days=200))["review_state"] == "review_overdue"


def test_exact_identifiers_only_and_negative_controls():
    result = normalize_pathway("cystic fibrosis", FIXTURE, NOW.isoformat(), limit=4)
    assert result["status"] == "links_retrieved"
    assert result["disease"]["id"] == "MONDO_0009061"
    assert result["coverage"]["disease_target_total"] == 2
    assert result["coverage"]["compound_rows_total"] == 2
    assert result["coverage"]["truncated"] is False
    assert len(result["links"]) == 1
    link = result["links"][0]
    assert link["target"]["id"] == "ENSG00000001626"
    assert link["compound"]["id"] == "CHEMBL2010601"
    assert link["evidence_kind"] == "source_reported_drug_mechanism"
    assert link["clinical_efficacy_verified"] is False
    assert link["source_record_hash"]
    assert "CHEMBL25" not in str(result["links"])
    # A displayed molecule title or matching gene name must never create a link.
    other = copy.deepcopy(FIXTURE)
    other["disease"]["drugAndClinicalCandidates"]["rows"][0]["drug"]["mechanismsOfAction"]["rows"][0]["targets"] = []
    assert normalize_pathway("cystic fibrosis", other, NOW.isoformat())["links"] == []


def test_malformed_and_ambiguous_source_records_fail_visible():
    broken = copy.deepcopy(FIXTURE)
    broken["disease"]["associatedTargets"]["rows"][0]["target"]["id"] = "../no"
    with pytest.raises(PathwaySourceError):
        normalize_pathway("cystic fibrosis", broken, NOW.isoformat())
    broken = copy.deepcopy(FIXTURE)
    broken["disease"]["associatedTargets"]["rows"][0]["score"] = float("nan")
    with pytest.raises(PathwaySourceError):
        normalize_pathway("cystic fibrosis", broken, NOW.isoformat())


@pytest.mark.asyncio
async def test_fixed_host_no_redirect_and_graphql_error_fail_safely(monkeypatch):
    original = httpx.AsyncClient
    def respond(request):
        assert request.url.host == "api.platform.opentargets.org"
        assert request.url.path == "/api/v4/graphql"
        assert request.method == "POST"
        return httpx.Response(200, json={"errors": [{"message": "Not authorized"}], "data": {}})
    def mock_client(**kwargs):
        assert kwargs["follow_redirects"] is False
        return original(transport=httpx.MockTransport(respond), **kwargs)
    monkeypatch.setattr("engines.governed_pathway.httpx.AsyncClient", mock_client)
    with pytest.raises(PathwaySourceError):
        await PathwaySourceClient().search("cystic fibrosis", limit=4)


def test_independent_regulatory_anchor_contract_has_explicit_review_boundary():
    references = load_reference_pathways()
    assert references["schema_version"] == "1.0"
    assert references["independent_human_review_completed"] is False
    result = normalize_pathway("cystic fibrosis", FIXTURE, NOW.isoformat())
    validation = validate_reference_pathways(result, references)
    assert validation["expected_links_found"] == 1
    assert validation["negative_controls_passed"] == 1
    assert validation["technical_consistency"] == "pass"
    assert validation["external_live_validation"] is False
    assert validation["clinical_validation"] is False
    mutated = copy.deepcopy(result)
    mutated["links"] = []
    assert validate_reference_pathways(mutated, references)["technical_consistency"] == "fail"


def test_real_upstream_release_strings_and_nullable_mechanism_targets():
    """Observed Open Targets September 2026 metadata has string numbers and null iteration."""
    observed = copy.deepcopy(FIXTURE)
    observed["meta"]["dataVersion"] = {"year": "26", "month": "09", "iteration": None}
    observed["disease"]["drugAndClinicalCandidates"]["rows"][1]["drug"]["mechanismsOfAction"]["rows"][0]["targets"] = None
    result = normalize_pathway("MONDO_0009061", observed, NOW.isoformat())
    assert result["source_freshness"]["source_release"] == "26.09"
    assert result["source_freshness"]["upstream_release"] == "observed_not_independently_verified"
    assert result["links"][0]["compound"]["id"] == "CHEMBL2010601"


def test_null_and_bad_count_have_explicit_safe_handling():
    observed = copy.deepcopy(FIXTURE)
    observed["disease"]["drugAndClinicalCandidates"]["count"] = None
    with pytest.raises(PathwaySourceError):
        normalize_pathway("MONDO_0009061", observed, NOW.isoformat())
    observed["disease"]["drugAndClinicalCandidates"]["count"] = 2
    observed["disease"]["associatedTargets"]["count"] = "two"
    with pytest.raises(PathwaySourceError):
        normalize_pathway("MONDO_0009061", observed, NOW.isoformat())
