"""Synthetic-only interoperability contracts. Never ingest authentic patient data."""
from __future__ import annotations

from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from api.main import app
from engines.medical_research_workbench import (
    synthetic_imaging_index, synthetic_lab_trends,
)
from engines.medical_stack_catalog import CONTRACT, PROJECTS, medical_stack_catalog


def observation(identity: str = "synthetic-first", result: float = 5.1, when: str = "2026-01-01T10:00:00Z") -> dict:
    return {
        "resourceType": "Observation",
        "id": identity,
        "meta": {"tag": [{"system": "urn:tmrds:data-classification", "code": "synthetic"}]},
        "status": "final",
        "code": {"coding": [{"system": "http://loinc.org", "code": "4548-4"}]},
        "effectiveDateTime": when,
        "valueQuantity": {
            "value": result, "system": "http://unitsofmeasure.org",
            "code": "%", "unit": "%",
        },
        "referenceRange": [{
            "low": {"value": 4.0, "system": "http://unitsofmeasure.org", "code": "%", "unit": "%"},
            "high": {"value": 6.0, "system": "http://unitsofmeasure.org", "code": "%", "unit": "%"},
        }],
    }


def imaging_study() -> dict:
    return {
        "resourceType": "ImagingStudy", "id": "synthetic-study",
        "meta": {"tag": [{"system": "urn:tmrds:data-classification", "code": "synthetic"}]},
        "status": "available", "started": "2026-01-01T12:30:00Z",
        "series": [{
            "modality": {"system": "http://dicom.nema.org/resources/ontology/DCM", "code": "DX"},
            "numberOfInstances": 2,
        }],
    }


def test_medical_project_catalog_has_realistic_deployment_states() -> None:
    result = medical_stack_catalog()
    assert len(PROJECTS) >= 30
    assert result["clinical_promotion_allowed"] is False
    assert result["real_patient_data_enabled"] is False
    assert any(p["state"] == CONTRACT for p in result["projects"])
    assert medical_stack_catalog("laboratory")["projects"][0]["project_id"] == "openelis"
    with pytest.raises(ValueError):
        medical_stack_catalog("patient_care_autonomous")


def test_lab_organizes_synthetic_results_without_interpretation() -> None:
    data = synthetic_lab_trends([
        observation("synthetic-second", 5.5, "2026-02-01T12:00:00Z"),
        observation(),
    ])
    assert data["diagnosis_performed"] is False
    assert data["external_data_transmitted"] is False
    series = data["trends"][0]
    assert series["loinc"] == "4548-4"
    assert series["ucum_code"] == "%"
    assert series["arithmetic_delta"] == pytest.approx(0.4)
    assert series["measurements"][0]["value"] == 5.1
    assert series["reference_intervals_are_unverified"] is True
    assert "term=hemoglobin%20A1c" in series["literature_lookup"]
    assert series["delta_interpretation"] == "NOT_EVALUATED"


@pytest.mark.parametrize("edit", [
    lambda x: x.update(subject={"reference": "Patient/real"}),
    lambda x: x.update(patient_name="Real Person"),
    lambda x: x.update(meta={"tag": [{"system": "urn:tmrds:data-classification", "code": "real"}]}),
    lambda x: x.update(id="patient-42"),
    lambda x: x.update(valueQuantity={"value": 5.0}),
    lambda x: x["valueQuantity"].update(value=float("nan")),
    lambda x: x["valueQuantity"].update(code="mg/dL"),
    lambda x: x.update(effectiveDateTime="2026-01-01"),
    lambda x: x.update(code={"coding": [{"system": "http://invalid", "code": "4548-4"}]}),
    lambda x: x.update(status="entered-in-error"),
])
def test_lab_rejects_unsafe_fields_or_missing_metadata(edit) -> None:
    obj = observation()
    edit(obj)
    with pytest.raises((ValueError, TypeError)):
        synthetic_lab_trends([obj])


def test_lab_rejects_duplicate_ids() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        synthetic_lab_trends([observation(), observation()])


def test_lab_rejects_mixed_reference_range_units() -> None:
    obj = observation()
    obj["referenceRange"][0]["low"]["code"] = "mg/dL"
    with pytest.raises(ValueError, match="reference range unit"):
        synthetic_lab_trends([obj])


def test_lab_rejects_unbounded_resources() -> None:
    with pytest.raises(ValueError):
        synthetic_lab_trends([observation()] * 101)


def test_study_index_has_no_pixels_and_rejects_patient_identifiers() -> None:
    result = synthetic_imaging_index([imaging_study()])
    assert result["image_transfer_enabled"] is False
    assert result["studies"][0]["dicom_pixels_loaded"] is False
    obj = imaging_study()
    obj["subject"] = {"reference": "Patient/42"}
    with pytest.raises(ValueError):
        synthetic_imaging_index([obj])


def test_study_index_rejects_untrusted_pixel_metadata() -> None:
    obj = imaging_study()
    obj["series"][0]["pixelData"] = "unsafe"
    with pytest.raises(ValueError):
        synthetic_imaging_index([obj])


def test_medical_discovery_routes_accurately_report_no_live_connection() -> None:
    client = TestClient(app)
    status = client.get("/api/v1/medical/integration-status")
    assert status.status_code == 200
    assert status.json()["external_clinical_services_connected"] is False
    assert status.json()["clinical_promotion_allowed"] is False
    assert client.get("/api/v1/medical/stack?category=imaging").status_code == 200
    assert client.get("/api/v1/medical/stack?category=bad").status_code == 422
    assert client.get("/api/v1/medical/research-providers?domain=genomics").status_code == 200


def test_demo_opt_in_disabled_by_default(monkeypatch) -> None:
    monkeypatch.setenv("TMRDS_ENV", "development")
    monkeypatch.setenv("TMRDS_SERVICE_AUTH_REQUIRED", "false")
    monkeypatch.delenv("TMRDS_SYNTHETIC_WORKBENCH_ENABLED", raising=False)
    response = TestClient(app).post(
        "/api/v1/medical/synthetic/labs/trends", json={"resources": [observation()]},
    )
    assert response.status_code == 403


def test_demo_enabled_in_dev_only(monkeypatch) -> None:
    monkeypatch.setenv("TMRDS_ENV", "development")
    monkeypatch.setenv("TMRDS_SERVICE_AUTH_REQUIRED", "false")
    monkeypatch.setenv("TMRDS_SYNTHETIC_WORKBENCH_ENABLED", "true")
    client = TestClient(app)
    assert client.post(
        "/api/v1/medical/synthetic/labs/trends", json={"resources": [observation()]},
    ).status_code == 200
    assert client.post(
        "/api/v1/medical/synthetic/imaging/index", json={"studies": [imaging_study()]},
    ).status_code == 200
    assert client.post(
        "/api/v1/medical/synthetic/labs/trends",
        json={"resources": [dict(observation(), subject={"reference": "Patient/123"})]},
    ).status_code == 422
    assert client.post(
        "/api/v1/medical/synthetic/labs/trends", json={"resources": [observation()], "patient": "name"},
    ).status_code == 422
    assert "post" in client.get("/openapi.json").json()["paths"]["/api/v1/medical/synthetic/labs/trends"]


def test_demo_stays_disabled_in_production_even_when_flagged(monkeypatch) -> None:
    from api.medical_workbench_routes import _require_synthetic_demo
    from fastapi import HTTPException
    monkeypatch.setenv("TMRDS_ENV", "production")
    monkeypatch.setenv("TMRDS_SYNTHETIC_WORKBENCH_ENABLED", "true")
    with pytest.raises(HTTPException) as exc:
        _require_synthetic_demo()
    assert exc.value.status_code == 403

def test_static_synthetic_research_demo_is_served() -> None:
    response = TestClient(app).get("/research/medical-demo")
    assert response.status_code == 200
    assert "SYNTHETIC DATA ONLY" in response.text
    assert "patient" in response.text.lower()
