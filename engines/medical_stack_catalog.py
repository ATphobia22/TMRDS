"""Open-source medical stack inventory, with intentionally truthful integration states.

Catalog metadata is not proof a package has been installed, assessed, licensed,
or configured. TMRDS continues to exclude real PHI and diagnostic inference.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

IN_REPO = "EXISTING_RESEARCH_PIPELINE"
CONTRACT = "INTEGRATION_CONTRACT_READY"
REFERENCE = "REFERENCE_ONLY"
RESTRICTED = "REQUIRES_SEPARATE_VALIDATION"


@dataclass(frozen=True, slots=True)
class MedicalProject:
    project_id: str
    category: str
    name: str
    repository: str
    interface: str
    state: str
    purpose: str
    caution: str = ""


PROJECTS: tuple[MedicalProject, ...] = (
    MedicalProject("hapi_fhir", "interoperability", "HAPI FHIR", "https://github.com/hapifhir/hapi-fhir", "FHIR R4 REST", CONTRACT, "FHIR server target", "No patient exchange enabled."),
    MedicalProject("openelis", "laboratory", "OpenELIS Global", "https://github.com/DIGI-UW/OpenELIS-Global-2", "FHIR R4 / institution-specific APIs", CONTRACT, "LIS and final lab reports", "Verify institutional interface and permissions."),
    MedicalProject("openemr", "ehr", "OpenEMR", "https://github.com/openemr/openemr", "FHIR R4 / REST", CONTRACT, "EHR reference target", "Standalone security and license review required."),
    MedicalProject("bahmni", "ehr", "Bahmni", "https://github.com/Bahmni", "FHIR / REST", REFERENCE, "Integrated hospital workflows", "Copyleft and instance-specific APIs."),
    MedicalProject("openmrs", "ehr", "OpenMRS", "https://github.com/openmrs/openmrs-core", "FHIR / REST", REFERENCE, "EHR interoperability reference"),
    MedicalProject("gnu_health", "ehr", "GNU Health", "https://codeberg.org/gnuhealth", "FHIR / implementation-specific", REFERENCE, "Sovereign healthcare information system"),
    MedicalProject("orthanc", "imaging", "Orthanc", "https://github.com/jodogne/OrthancMirror", "DICOMweb / REST", CONTRACT, "DICOM archive index", "No PACS connection or image transfer enabled."),
    MedicalProject("ohif", "imaging", "OHIF Viewer", "https://github.com/OHIF/Viewers", "DICOMweb", CONTRACT, "Browser-based DICOM viewing", "Viewer is not embedded in TMRDS."),
    MedicalProject("cornerstone3d", "imaging", "Cornerstone3D", "https://github.com/cornerstonejs/cornerstone3D", "JavaScript imaging", REFERENCE, "DICOM image rendering libraries"),
    MedicalProject("slicer", "imaging", "3D Slicer", "https://github.com/Slicer/Slicer", "Local desktop / Python", RESTRICTED, "Research segmentation and anatomical visualization", "Not a clinical device."),
    MedicalProject("pydicom", "imaging", "pydicom", "https://github.com/pydicom/pydicom", "DICOM file parsing", RESTRICTED, "Offline DICOM metadata tooling", "Untrusted DICOM parsing and patient data out of scope."),
    MedicalProject("dcmtk", "imaging", "DCMTK", "https://github.com/DCMTK/dcmtk", "DICOM utilities", REFERENCE, "DICOM validation and transfer"),
    MedicalProject("itk", "imaging", "ITK", "https://github.com/InsightSoftwareConsortium/ITK", "Image processing SDK", RESTRICTED, "Registration and processing research"),
    MedicalProject("mitk", "imaging", "MITK", "https://github.com/MITK/MITK", "Desktop SDK", RESTRICTED, "Research image visualization"),
    MedicalProject("pyradiomics", "imaging_ai", "PyRadiomics", "https://github.com/AIM-Harvard/pyradiomics", "Python API", RESTRICTED, "Quantitative research features", "Feature validity depends on imaging protocol."),
    MedicalProject("tiatoolbox", "imaging_ai", "TIAToolbox", "https://github.com/TissueImageAnalytics/tiatoolbox", "Python SDK", RESTRICTED, "Digital pathology research"),
    MedicalProject("monai", "imaging_ai", "MONAI", "https://github.com/Project-MONAI/MONAI", "Python SDK", RESTRICTED, "Research-only model workflows", "Not validated for patient diagnosis."),
    MedicalProject("nnunet", "imaging_ai", "nnU-Net", "https://github.com/MIC-DKFZ/nnUNet", "Python CLI", RESTRICTED, "Segmentation research"),
    MedicalProject("torchio", "imaging_ai", "TorchIO", "https://github.com/TorchIO-project/torchio", "Python SDK", RESTRICTED, "Imaging data augmentation"),
    MedicalProject("omop", "research_data", "OHDSI OMOP CDM", "https://github.com/OHDSI/CommonDataModel", "OMOP SQL model", CONTRACT, "Observational research common data model", "ETL and governance not deployed."),
    MedicalProject("atlas", "research_data", "OHDSI ATLAS", "https://github.com/OHDSI/Atlas", "OHDSI WebAPI", REFERENCE, "Cohort definitions and observation analytics"),
    MedicalProject("data_quality_dashboard", "research_data", "OHDSI DataQualityDashboard", "https://github.com/OHDSI/DataQualityDashboard", "R / OMOP", REFERENCE, "OMOP data quality"),
    MedicalProject("usagi", "terminology", "OHDSI Usagi", "https://github.com/OHDSI/Usagi", "Vocabulary mapping", REFERENCE, "Local-to-standard clinical codes"),
    MedicalProject("white_rabbit", "research_data", "OHDSI WhiteRabbit", "https://github.com/OHDSI/WhiteRabbit", "ETL profiling", REFERENCE, "Source data inventory"),
    MedicalProject("snowstorm", "terminology", "Snowstorm", "https://github.com/IHTSDO/snowstorm", "FHIR terminology service", CONTRACT, "SNOMED CT lookup", "Terminology licensing applies."),
    MedicalProject("loinc", "terminology", "LOINC", "https://loinc.org/", "LOINC codes", CONTRACT, "Laboratory test identifiers", "Term content subject to license."),
    MedicalProject("rxnorm", "terminology", "RxNorm", "https://www.nlm.nih.gov/research/umls/rxnorm/", "RxNav", IN_REPO, "Medication name normalization", "Never infer interactions without evidence."),
    MedicalProject("pubmed", "literature", "PubMed", "https://www.ncbi.nlm.nih.gov/research/bionlp/", "NCBI E-utilities", IN_REPO, "Published biomedical literature"),
    MedicalProject("europe_pmc", "literature", "Europe PMC", "https://github.com/EuropePMC", "REST", IN_REPO, "Biomedical articles"),
    MedicalProject("clinical_trials", "clinical_trials", "ClinicalTrials.gov", "https://clinicaltrials.gov/data-api/api", "API v2", IN_REPO, "Trial records", "Registry entry is not clinical efficacy."),
    MedicalProject("openfda", "drugs", "openFDA", "https://github.com/FDA/openfda", "Public API", IN_REPO, "Drug labels and surveillance", "Adverse event reports cannot establish causality."),
    MedicalProject("ctakes", "nlp", "Apache cTAKES", "https://github.com/apache/ctakes", "Java NLP", RESTRICTED, "De-identification and note concepts", "No identifiable clinical notes may be sent to public pipelines."),
    MedicalProject("cqf", "decision_support", "HL7 Clinical Quality Framework", "https://github.com/HL7/cqf-recommendations", "FHIR Clinical Reasoning", RESTRICTED, "Guideline representation", "No executable patient-care recommendations."),
    MedicalProject("patient_level_prediction", "research_data", "OHDSI PatientLevelPrediction", "https://github.com/OHDSI/PatientLevelPrediction", "R / OMOP", RESTRICTED, "Model evaluation research"),
    MedicalProject("synthea", "synthetic_data", "Synthea", "https://github.com/synthetichealth/synthea", "Synthetic FHIR", CONTRACT, "Test data generation", "Synthetic data is never clinical evidence."),
)


def medical_stack_catalog(category: str | None = None) -> dict[str, object]:
    categories = {project.category for project in PROJECTS}
    if category is not None and category not in categories:
        raise ValueError("unsupported medical project category")
    matching = (item for item in PROJECTS if category is None or item.category == category)
    return {
        "status": "research-advisory",
        "human_authority_final": True,
        "clinical_promotion_allowed": False,
        "real_patient_data_enabled": False,
        "external_clinical_connectors_enabled": False,
        "category": category,
        "projects": [asdict(project) for project in matching],
    }
