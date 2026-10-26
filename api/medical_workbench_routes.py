"""Research-only medical source discovery and opt-in synthetic interoperability demos.

This router NEVER accepts actual patient records, performs DICOM processing,
connects to a clinical server or records clinical decisions. Writes are
synthetic transforms only; the existing service-auth dependency is retained.
"""
from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from api.security_dependencies import require_service_identity
from engines.biomedical_provider_registry import list_providers
from engines.medical_research_workbench import (
    synthetic_imaging_index, synthetic_lab_trends,
)
from engines.medical_stack_catalog import medical_stack_catalog

router = APIRouter(prefix="/api/v1/medical", tags=["medical-research-workbench"])


class SyntheticLabRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    resources: list[dict[str, Any]] = Field(min_length=1, max_length=100)


class SyntheticImagingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    studies: list[dict[str, Any]] = Field(min_length=1, max_length=40)


def _require_synthetic_demo() -> None:
    environment = os.getenv("TMRDS_ENV", "development").strip().casefold()
    enabled = os.getenv("TMRDS_SYNTHETIC_WORKBENCH_ENABLED", "").strip().casefold() == "true"
    if environment in {"prod", "production"} or not enabled:
        raise HTTPException(
            status_code=403,
            detail="synthetic medical workbench is disabled; no patient data may be submitted",
        )


@router.get("/stack")
async def get_medical_stack(
    category: str | None = Query(default=None, max_length=64),
) -> dict[str, object]:
    try:
        return medical_stack_catalog(category)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="unknown medical stack category") from exc


@router.get("/research-providers")
async def get_biomedical_research_providers(
    domain: str | None = Query(default=None, max_length=64),
) -> dict[str, object]:
    try:
        return list_providers(domain)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="unknown biomedical research domain") from exc


@router.get("/integration-status")
async def get_medical_integration_status() -> dict[str, object]:
    """Static implementation state, not a network reachability or compliance claim."""
    return {
        "status": "research-advisory",
        "live_patient_exchange": False,
        "medical_imaging_processing": False,
        "diagnostic_analysis": False,
        "external_clinical_services_connected": False,
        "synthetic_demo_enabled": (
            os.getenv("TMRDS_SYNTHETIC_WORKBENCH_ENABLED", "").casefold() == "true"
            and os.getenv("TMRDS_ENV", "development").casefold() not in {"prod", "production"}
        ),
        "contracts": {
            "fhir": "R4 synthetic Observation/ImagingStudy subset",
            "lab": "LOINC identifier + UCUM unit + source status + date",
            "imaging": "DICOM coded modality metadata only; no images",
            "literature": "public PubMed/Europe PMC/trial/openFDA routes already in gateway",
            "omop": "existing research mapping; no institutional ETL connected",
            "ehr": "adapter target only; no live exchange",
            "ohif": "external viewer target, not embedded or running",
            "orthanc": "external DICOMweb server target, not connected",
            "clinical_review": "required before clinical use; not implemented",
        },
        "review_required": True,
        "human_authority_final": True,
        "clinical_promotion_allowed": False,
    }


@router.post(
    "/synthetic/labs/trends",
    dependencies=[Depends(require_service_identity)],
)
async def synthetic_lab_review(request: SyntheticLabRequest) -> dict[str, object]:
    _require_synthetic_demo()
    try:
        return synthetic_lab_trends(request.resources)
    except (ValueError, TypeError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post(
    "/synthetic/imaging/index",
    dependencies=[Depends(require_service_identity)],
)
async def synthetic_imaging_review(request: SyntheticImagingRequest) -> dict[str, object]:
    _require_synthetic_demo()
    try:
        return synthetic_imaging_index(request.studies)
    except (ValueError, TypeError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
