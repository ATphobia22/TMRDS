"""
Open-Source Medical Core adapters for TMRDS.
Local-first clinical stack integration points — no commercial EHR lock-in.

Components:
  - OpenEMR — open-source EHR / medical records
  - Orthanc — lightweight DICOM PACS
  - OHIF Viewer — zero-footprint web DICOM 2D/3D
  - OpenELIS — laboratory information system
  - Kiwix + WikiMed — offline clinical reference

These adapters record connection intent and health-check URLs;
production wiring is environment-specific.
"""
from __future__ import annotations

from typing import Any, Dict, Optional


DEFAULTS = {
    "openemr": {"base_url": "http://localhost:8300", "api": "/apis/default/fhir"},
    "orthanc": {"base_url": "http://localhost:8042", "api": "/instances"},
    "ohif": {"base_url": "http://localhost:3000", "viewer": "/viewer"},
    "openelis": {"base_url": "http://localhost:8080", "api": "/api"},
    "kiwix": {"base_url": "http://localhost:8081", "wikimed": "/wikimed"},
}


class OpenSourceMedicalCore:
    """Registry of local open-source clinical services for sovereign clinics."""

    def __init__(self, overrides: Optional[Dict[str, Dict[str, str]]] = None) -> None:
        self.services = {k: dict(v) for k, v in DEFAULTS.items()}
        if overrides:
            for k, v in overrides.items():
                if k in self.services:
                    self.services[k].update(v)

    def describe(self) -> Dict[str, Any]:
        return {
            "openemr": {
                "role": "Local EHR / FHIR R4 patient records",
                **self.services["openemr"],
            },
            "orthanc": {
                "role": "DICOM PACS — store/query/retrieve",
                **self.services["orthanc"],
            },
            "ohif": {
                "role": "Zero-footprint DICOM viewer (2D/3D)",
                **self.services["ohif"],
            },
            "openelis": {
                "role": "Laboratory information system / order tracking",
                **self.services["openelis"],
            },
            "kiwix_wikimed": {
                "role": "Offline WikiMed clinical reference via Kiwix",
                **self.services["kiwix"],
            },
        }

    def fhir_endpoint(self) -> str:
        emr = self.services["openemr"]
        return f"{emr['base_url'].rstrip('/')}{emr.get('api', '')}"

    def dicom_endpoint(self) -> str:
        return self.services["orthanc"]["base_url"].rstrip("/")

    def status(self) -> Dict[str, Any]:
        return {
            "node": "OpenSourceMedicalCore",
            "services": list(self.services.keys()),
            "fhir_endpoint": self.fhir_endpoint(),
            "dicom_endpoint": self.dicom_endpoint(),
            "mode": "local_sovereign",
            "status": "READY",
        }
