"""Bounded original-source periodic table API test. No drug or toxicology claims."""
import asyncio

import httpx
import pytest
from fastapi.testclient import TestClient

from api.public_gateway import app
from engines.pubchem_periodic_element import (
    PUBCHEM_PERIODIC_URL, extract_original_element, lookup_pubchem_element,
)


def table():
    return {"Table": {
        "Columns": {"Column": [
            "AtomicNumber", "Symbol", "Name", "AtomicWeight", "ElectronConfiguration",
            "Electronegativity", "OxidationStates", "StandardState", "GroupBlock",
        ]},
        "Row": [
            {"Cell": ["1", "H", "Hydrogen", "1.0080", "1s1", "2.2", "+1, -1", "Gas", "Nonmetal"]},
            {"Cell": ["26", "Fe", "Iron", "55.845", "[Ar]3d6 4s2", "1.83", "+2, +3", "Solid", "Transition metal"]},
        ],
    }}


def test_periodic_table_values_are_original_fields_not_invented_inferences():
    actual = extract_original_element(table(), "Fe")
    assert actual["atomic_number"] == 26
    assert actual["name"] == "Iron"
    assert actual["electron_configuration_reported"] == "[Ar]3d6 4s2"
    assert actual["atomic_weight_source_text"] == "55.845"
    assert actual["complete_table_cardinality_observed"] is False
    assert extract_original_element(table(), "U") == {}


def test_original_host_and_bound_result_no_redirects():
    requested = []
    def transport(request: httpx.Request):
        requested.append(str(request.url))
        assert request.url.host == "pubchem.ncbi.nlm.nih.gov"
        assert request.url.path == "/rest/pug/periodictable/JSON"
        return httpx.Response(200, json=table())
    data = asyncio.run(lookup_pubchem_element("H", transport=httpx.MockTransport(transport)))
    assert requested == [PUBCHEM_PERIODIC_URL]
    assert data["element"]["name"] == "Hydrogen"
    assert data["status"] == "element_metadata"
    assert data["drug_efficacy_inferred"] is False
    assert data["toxicity_inferred"] is False
    assert data["clinical_promotion_allowed"] is False
    assert data["patent_freedom_to_operate"] == "NOT_DETERMINED"
    not_found = asyncio.run(lookup_pubchem_element("U", transport=httpx.MockTransport(transport)))
    assert not_found["status"] == "element_not_found"
    assert not_found["element"] is None


def test_invalid_elements_source_schema_and_large_responses_fail_with_no_facts():
    for term in ("http://evil", "fe", "H,Na", "OG", "", "../"):
        with pytest.raises(ValueError):
            asyncio.run(lookup_pubchem_element(term))
    for response in (
        httpx.Response(301, headers={"Location": "http://127.0.0.1/internal"}),
        httpx.Response(200, content=b"x" * 262145),
        httpx.Response(200, json={"Table": {"Columns": {"Column": ["Symbol"]}, "Row": [{"Cell": ["Fe"]}]}}),
        httpx.Response(200, content=b"notjson"),
    ):
        value = asyncio.run(lookup_pubchem_element(
            "Fe", transport=httpx.MockTransport(lambda _, r=response: r)))
        assert value["status"] == "source_unavailable"
        assert value["element"] is None


def test_element_route_no_shell_or_url_arguments():
    client = TestClient(app)
    assert client.get("/api/v1/research/periodic-element", params={"symbol": "http://evil"}).status_code == 422
    assert client.get("/api/v1/research/periodic-element", params={"symbol": "Fe3+"}).status_code == 422
    assert client.post("/api/v1/research/periodic-element", params={"symbol": "Fe"}).status_code == 405
