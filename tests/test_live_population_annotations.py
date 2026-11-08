from __future__ import annotations

import hashlib
import json
from typing import Any

import pytest
import requests

import engines.disease_graph_model as model
from engines.disease_graph_model import (
    GnomADAdapter,
    GnomADLookupError,
    GTExAdapter,
    GTExLookupError,
)


class FakeResponse:
    def __init__(self, payload: Any, status_code: int = 200) -> None:
        self.payload = payload
        self.status_code = status_code
        self.content = json.dumps(payload, sort_keys=True).encode("utf-8")
        self.text = self.content.decode("utf-8")

    def json(self) -> Any:
        return self.payload


def test_gnomad_fetch_returns_source_backed_callsets_and_provenance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = {
        "data": {
            "variant": {
                "variant_id": "1-55516888-G-A",
                "chrom": "1",
                "pos": 55516888,
                "ref": "G",
                "alt": "A",
                "rsids": ["rs11591147"],
                "exome": {
                    "ac": 1234,
                    "an": 250000,
                    "af": 0.004936,
                    "populations": [{"id": "nfe", "ac": 1000, "an": 150000}],
                },
                "genome": {
                    "ac": 456,
                    "an": 150000,
                    "af": 0.00304,
                    "populations": [{"id": "afr", "ac": 40, "an": 10000}],
                },
            }
        }
    }
    captured: list[tuple[str, dict[str, Any]]] = []

    def fake_post(url: str, **kwargs: Any) -> FakeResponse:
        captured.append((url, kwargs))
        return FakeResponse(payload)

    monkeypatch.setattr(requests, "post", fake_post)
    annotation, provenance = GnomADAdapter().fetch("1-55516888-G-A")

    assert annotation.status == "AVAILABLE"
    assert annotation.dataset_id == "gnomad_r4"
    assert annotation.reference_assembly == "GRCh38"
    assert annotation.exome["af"] == pytest.approx(0.004936)
    assert annotation.genome["af"] == pytest.approx(0.00304)
    assert annotation.populations[0]["id"] == "nfe"
    assert annotation.populations[0]["af"] == pytest.approx(1000 / 150000)
    assert annotation.populations[0]["callset"] == "exome"
    assert annotation.allele_frequency is None  # Do not collapse exome and genome into one number.
    assert provenance.source_version == "gnomad_r4"
    assert provenance.raw_record_hash == hashlib.sha256(FakeResponse(payload).content).hexdigest()
    assert captured[0][0] == GnomADAdapter.BASE
    assert captured[0][1]["allow_redirects"] is False
    assert captured[0][1]["json"]["variables"]["variantId"] == "1-55516888-G-A"


@pytest.mark.parametrize(
    "variant_id",
    [
        "NC_000017.11:41196312:G:T",
        "17:g.41196312G>T",
        "rs11591147",
        "../1-55516888-G-A",
        "1-0-G-A",
    ],
)
def test_gnomad_rejects_noncanonical_or_invalid_ids_without_network(
    variant_id: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        requests,
        "post",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("unexpected request")),
    )
    with pytest.raises(ValueError, match="normalized GRCh38 gnomAD ID"):
        GnomADAdapter().fetch(variant_id)


def test_gnomad_rejects_grch37_without_network(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        requests,
        "post",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("unexpected request")),
    )
    with pytest.raises(ValueError, match="gnomad_r4 is GRCh38"):
        GnomADAdapter().fetch("1-55516888-G-A", assembly="GRCh37")


def test_gnomad_graphql_errors_and_missing_variants_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = [
        FakeResponse({"errors": [{"message": "schema mismatch"}]}),
        FakeResponse({"data": {"variant": None}}),
    ]
    monkeypatch.setattr(requests, "post", lambda *args, **kwargs: responses.pop(0))
    with pytest.raises(GnomADLookupError, match="GraphQL query failed"):
        GnomADAdapter().fetch("1-55516888-G-A")
    with pytest.raises(GnomADLookupError, match="was not found"):
        GnomADAdapter().fetch("1-55516888-G-A")


def test_gtex_fetch_returns_observed_rows_and_paging_state(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "data": [
            {
                "gencodeId": "ENSG00000141510.18",
                "geneSymbol": "TP53",
                "variantId": "chr17_7676154_G_A_b38",
                "tissueSiteDetailId": "Whole_Blood",
                "pValue": 1e-8,
                "nes": 0.25,
                "datasetId": "gtex_v10",
            }
        ],
        "paging_info": {
            "numberOfPages": 3,
            "page": 0,
            "maxItemsPerPage": 100,
            "totalNumberOfItems": 250,
        },
    }
    captured: list[tuple[str, dict[str, Any]]] = []

    def fake_get(url: str, **kwargs: Any) -> FakeResponse:
        captured.append((url, kwargs))
        return FakeResponse(payload)

    monkeypatch.setattr(requests, "get", fake_get)
    annotation, provenance = GTExAdapter().fetch_eqtl(
        "ENSG00000141510.18", tissue_ids=["Whole_Blood"], max_results=100
    )

    assert annotation.status == "PARTIAL"
    assert annotation.is_partial is True
    assert annotation.total_results == 250
    assert annotation.dataset_id == "gtex_v10"
    assert annotation.gene_id.id == "ENSG00000141510"
    assert annotation.gene_id.version == "18"
    assert annotation.tissue_eqtls[0]["pValue"] == pytest.approx(1e-8)
    assert provenance.source_version == "gtex_v10"
    assert provenance.raw_record_hash == hashlib.sha256(FakeResponse(payload).content).hexdigest()
    assert captured[0][0] == f"{GTExAdapter.BASE}/association/independentEqtl"
    assert captured[0][1]["allow_redirects"] is False
    assert captured[0][1]["params"]["gencodeId"] == "ENSG00000141510.18"
    assert captured[0][1]["params"]["tissueSiteDetailId"] == ["Whole_Blood"]


def test_gtex_requires_versioned_gene_id_and_valid_dataset_without_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        requests,
        "get",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("unexpected request")),
    )
    with pytest.raises(ValueError, match="versioned GTEx GENCODE ID"):
        GTExAdapter().fetch_eqtl("ENSG00000141510")
    with pytest.raises(ValueError, match="dataset_id"):
        GTExAdapter().fetch_eqtl("ENSG00000141510.18", dataset_id="gtex_v99")


def test_gtex_errors_and_malformed_data_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = [
        FakeResponse({"detail": "invalid query"}),
        FakeResponse({"data": [None], "paging_info": {"numberOfPages": 1, "totalNumberOfItems": 1}}),
    ]
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: responses.pop(0))
    with pytest.raises(GTExLookupError, match="missing data or paging metadata"):
        GTExAdapter().fetch_eqtl("ENSG00000141510.18")
    with pytest.raises(GTExLookupError, match="malformed eQTL record"):
        GTExAdapter().fetch_eqtl("ENSG00000141510.18")


def test_literature_view_does_not_return_placeholder_annotations_by_default() -> None:
    variant = model.Variant(
        vrs_allele=model.VRSAllele(
            id="ga4gh:VA.test",
            location=model.VRSLocation(sequence_id="ga4gh:SQ.test", start=1, end=2),
            state={"type": "LiteralSequenceExpression", "sequence": "A"},
            digest="test-variant",
        ),
        spdi="NC_000017.11:41196312:G:T",
    )

    view = model.DiseaseGraphBuilder().create_literature_view(variant)

    assert view.gnomad is None
    assert view.gtex is None
    assert any("were not queried" in item for item in view.disclaimers)
