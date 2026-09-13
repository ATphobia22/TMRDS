"""Standards metadata and non-PHI FHIR validation endpoints."""
from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from engines.fhir_interoperability import FHIRInteroperabilityConfig, FHIRResourceValidator
from engines.smart_security import SmartConfiguration

router = APIRouter(tags=["interoperability"])


class FHIRValidationRequest(BaseModel):
    resource: dict[str, Any]
    required_profile: str | None = Field(default=None, max_length=512)


def fhir_config() -> FHIRInteroperabilityConfig:
    return FHIRInteroperabilityConfig(
        fhir_version=os.getenv("TMRDS_FHIR_VERSION", "R4"),
        us_core_version=os.getenv("TMRDS_US_CORE_VERSION", "9.0.0"),
        terminology_version=os.getenv("TMRDS_TERMINOLOGY_VERSION", "unspecified"),
    )


@router.get("/.well-known/smart-configuration")
async def smart_configuration() -> dict[str, object]:
    base_url = os.getenv("TMRDS_BASE_URL", "http://localhost:8000").rstrip("/")
    return SmartConfiguration(
        issuer=base_url,
        authorization_endpoint=f"{base_url}/oauth/authorize",
        token_endpoint=f"{base_url}/oauth/token",
        jwks_uri=f"{base_url}/.well-known/jwks.json",
    ).as_dict()


@router.get("/api/v1/interoperability/status")
async def interoperability_status() -> dict[str, object]:
    config = fhir_config()
    return {
        "fhir_version": config.fhir_version,
        "us_core_version": config.us_core_version,
        "terminology_version": config.terminology_version,
        "smart_pkce": "S256",
        "backend_authentication": "private_key_jwt/JWKS when configured",
        "live_phi_exchange": False,
        "institutional_access": False,
    }


@router.post("/api/v1/interoperability/fhir/validate")
async def validate_fhir_resource(request: FHIRValidationRequest) -> dict[str, object]:
    config = fhir_config()
    if request.required_profile:
        resource_type = request.resource.get("resourceType")
        config = FHIRInteroperabilityConfig(
            fhir_version=config.fhir_version,
            us_core_version=config.us_core_version,
            terminology_version=config.terminology_version,
            required_profiles={str(resource_type): request.required_profile},
        )
    validator = FHIRResourceValidator(config)
    errors = validator.validate(request.resource)
    return {"valid": not errors, "errors": errors, "fhir_version": config.fhir_version, "us_core_version": config.us_core_version}
