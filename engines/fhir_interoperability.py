"""Governed FHIR R4 interoperability metadata and safety primitives."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from urllib.parse import urlparse


FHIR_ID_MAX = 64
FHIR_RESOURCE_TYPES = {
    "Account", "ActivityDefinition", "AdverseEvent", "AllergyIntolerance", "Appointment", "AuditEvent",
    "Basic", "Binary", "BiologicallyDerivedProduct", "BodyStructure", "Bundle", "CapabilityStatement",
    "CarePlan", "CareTeam", "CatalogEntry", "ChargeItem", "Claim", "ClaimResponse", "ClinicalImpression",
    "CodeSystem", "Communication", "CommunicationRequest", "CompartmentDefinition", "Composition", "ConceptMap",
    "Condition", "Consent", "Contract", "Coverage", "DetectedIssue", "Device", "DeviceDefinition",
    "DeviceMetric", "DeviceRequest", "DeviceUseStatement", "DiagnosticReport", "DocumentManifest", "DocumentReference",
    "EffectEvidenceSynthesis", "Encounter", "Endpoint", "EnrollmentRequest", "EnrollmentResponse", "EpisodeOfCare",
    "EventDefinition", "Evidence", "EvidenceVariable", "ExampleScenario", "ExplanationOfBenefit", "FamilyMemberHistory",
    "Flag", "Goal", "GraphDefinition", "Group", "GuidanceResponse", "HealthcareService", "ImagingStudy", "Immunization",
    "ImmunizationEvaluation", "ImmunizationRecommendation", "ImplementationGuide", "InsurancePlan", "Invoice", "Library",
    "Linkage", "List", "Location", "Measure", "MeasureReport", "Media", "Medication", "MedicationAdministration",
    "MedicationDispense", "MedicationKnowledge", "MedicationRequest", "MedicationStatement", "MedicinalProduct",
    "MedicinalProductAuthorization", "MedicinalProductContraindication", "MedicinalProductIndication", "MedicinalProductIngredient",
    "MedicinalProductInteraction", "MedicinalProductManufactured", "MedicinalProductPackaged", "MedicinalProductPharmaceutical",
    "MedicinalProductUndesirableEffect", "MessageDefinition", "MessageHeader", "MolecularSequence", "NamingSystem",
    "NutritionOrder", "Observation", "OperationDefinition", "OperationOutcome", "Organization", "OrganizationAffiliation",
    "Parameters", "Patient", "PaymentNotice", "PaymentReconciliation", "Person", "PlanDefinition", "Practitioner",
    "PractitionerRole", "Procedure", "Provenance", "Questionnaire", "QuestionnaireResponse", "RelatedPerson", "RequestGroup",
    "ResearchDefinition", "ResearchElementDefinition", "ResearchStudy", "ResearchSubject", "RiskAssessment", "RiskEvidenceSynthesis",
    "Schedule", "SearchParameter", "ServiceRequest", "Slot", "Specimen", "StructureDefinition", "StructureMap", "Subscription",
    "Substance", "SupplyDelivery", "SupplyRequest", "Task", "TerminologyCapabilities", "TestReport", "TestScript", "ValueSet",
    "VerificationResult", "VisionPrescription",
}


@dataclass(frozen=True, slots=True)
class FHIRInteroperabilityConfig:
    """Explicitly pinned interoperability settings."""

    fhir_version: str = "R4"
    us_core_version: str = "9.0.0"
    terminology_version: str = "unspecified"
    required_profiles: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.fhir_version.upper() != "R4":
            raise ValueError("TMRDS interoperability baseline is FHIR R4")
        if not self.us_core_version.strip():
            raise ValueError("US Core version must be explicit")


class FHIRResourceValidator:
    """Safe structural validator; full package conformance remains a deployment concern."""

    def __init__(self, config: FHIRInteroperabilityConfig) -> None:
        self.config = config

    def validate(self, resource: dict[str, object]) -> list[str]:
        errors: list[str] = []
        resource_type = resource.get("resourceType")
        if not isinstance(resource_type, str) or resource_type not in FHIR_RESOURCE_TYPES:
            errors.append("resourceType must be a recognized FHIR R4 resource type")
        resource_id = resource.get("id")
        if resource_id is not None:
            if not isinstance(resource_id, str) or not 1 <= len(resource_id) <= FHIR_ID_MAX:
                errors.append("id must be a FHIR id of 1-64 characters")
            elif any(char.isspace() or char in {"/", "?", "#"} for char in resource_id):
                errors.append("id contains invalid characters")
        if not isinstance(resource_type, str) or resource_type not in FHIR_RESOURCE_TYPES:
            return errors
        meta = resource.get("meta")
        if meta is not None and not isinstance(meta, dict):
            errors.append("meta must be an object")
        required_profile = self.config.required_profiles.get(resource_type)
        if required_profile:
            profiles = meta.get("profile", []) if isinstance(meta, dict) else []
            if required_profile not in profiles:
                errors.append(f"required profile missing: {required_profile}")
        return errors


def _reference(value: str) -> dict[str, str]:
    parsed = urlparse(value)
    if parsed.scheme or parsed.netloc:
        raise ValueError("FHIR references must be relative or resource references")
    if not value or len(value) > 512:
        raise ValueError("invalid FHIR reference")
    return {"reference": value}


def build_provenance(target_reference: str, agent_reference: str, request_id: str) -> dict[str, object]:
    return {"resourceType": "Provenance", "recorded": datetime.now(timezone.utc).isoformat(), "target": [_reference(target_reference)], "agent": [{"who": _reference(agent_reference)}], "entity": [{"role": "source", "what": {"identifier": {"system": "urn:tmrds:request", "value": request_id}}}]}


def build_audit_event(agent_reference: str, target_reference: str, action: str, request_id: str) -> dict[str, object]:
    if action not in {"read", "create", "update", "delete", "execute"}:
        raise ValueError("unsupported audit action")
    return {"resourceType": "AuditEvent", "recorded": datetime.now(timezone.utc).isoformat(), "action": action[0].upper(), "agent": [{"who": _reference(agent_reference), "requestor": True}], "source": {"observer": _reference(agent_reference)}, "entity": [{"what": _reference(target_reference)}], "extension": [{"url": "urn:tmrds:correlation-id", "valueString": request_id}]}


def security_label(system: str, code: str, display: str | None = None) -> dict[str, object]:
    if not system or not code:
        raise ValueError("security label system and code are required")
    coding: dict[str, str] = {"system": system, "code": code}
    if display:
        coding["display"] = display
    return {"meta": {"security": [coding]}}
