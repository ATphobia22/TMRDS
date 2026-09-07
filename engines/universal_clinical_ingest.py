"""
Universal Clinical Ingest for TMRDS.
Accepts labs, imaging reports, genomic VCF/panels, sequencing summaries,
and free-text clinical notes — normalizes to a single patient evidence packet
for immediate (not days/weeks) handoff to QuantumRubiksCureEngine.

Standards targeted: LOINC (Regenstrief), HL7 FHIR Observation/DiagnosticReport,
VCF 4.x, and discrete pharmacogenomic phenotype codes.
"""
from __future__ import annotations

import hashlib
import time
from typing import Any, Dict, List, Optional


class UniversalClinicalIngest:
    """
    On-the-spot multi-modal clinical data normalizer.

    Input channels:
      - lab_results: LOINC-coded or free-text lab panels
      - imaging: radiology/pathology report text or structured findings
      - genomic: VCF-like variant list or star-allele / phenotype summary
      - sequencing: NGS panel / WES / WGS summary metrics
      - notes: clinical free text
    """

    SUPPORTED_CHANNELS = ("lab", "imaging", "genomic", "sequencing", "notes", "vitals")

    def __init__(self) -> None:
        self._packets: List[Dict[str, Any]] = []

    def ingest_lab(
        self,
        tests: List[Dict[str, Any]],
        source: str = "local_lis",
    ) -> Dict[str, Any]:
        """
        tests item shape: {name, value, unit, loinc?, ref_low?, ref_high?, flag?}
        """
        normalized = []
        for t in tests:
            if "name" not in t or "value" not in t:
                continue
            normalized.append({
                "name": str(t["name"]),
                "value": t["value"],
                "unit": t.get("unit"),
                "loinc": t.get("loinc"),
                "ref_low": t.get("ref_low"),
                "ref_high": t.get("ref_high"),
                "flag": t.get("flag") or self._flag(t),
            })
        return self._packet("lab", {"tests": normalized, "count": len(normalized)}, source)

    def ingest_imaging(
        self,
        modality: str,
        findings: str,
        impression: Optional[str] = None,
        source: str = "pacs_report",
    ) -> Dict[str, Any]:
        return self._packet(
            "imaging",
            {
                "modality": modality,
                "findings": findings,
                "impression": impression or "",
            },
            source,
        )

    def ingest_genomic(
        self,
        variants: List[Dict[str, Any]],
        assembly: str = "GRCh38",
        source: str = "ngs_panel",
    ) -> Dict[str, Any]:
        """
        variants item: {gene, hgvs?, zygosity?, clinical_significance?, phenotype?}
        """
        clean = []
        for v in variants:
            if "gene" not in v:
                continue
            clean.append({
                "gene": str(v["gene"]).upper(),
                "hgvs": v.get("hgvs"),
                "zygosity": v.get("zygosity"),
                "clinical_significance": v.get("clinical_significance"),
                "phenotype": v.get("phenotype"),
            })
        return self._packet(
            "genomic",
            {"assembly": assembly, "variants": clean, "variant_count": len(clean)},
            source,
        )

    def ingest_sequencing_summary(
        self,
        assay: str,
        metrics: Dict[str, Any],
        source: str = "sequencer",
    ) -> Dict[str, Any]:
        return self._packet(
            "sequencing",
            {"assay": assay, "metrics": metrics},
            source,
        )

    def ingest_notes(self, text: str, source: str = "clinician") -> Dict[str, Any]:
        return self._packet("notes", {"text": text[:50000]}, source)

    def build_patient_packet(
        self,
        patient_ref: str,
        channel_results: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Merge channel packets into one evidence object for QRCE."""
        body = {
            "patient_ref": patient_ref,
            "channels": channel_results,
            "channel_types": [c.get("channel") for c in channel_results],
            "built_at": time.time(),
        }
        body["content_hash"] = hashlib.sha256(
            str(sorted(body.items())).encode()
        ).hexdigest()
        self._packets.append(body)
        return {
            **body,
            "status": "PACKET_READY",
            "latency_goal": "on_the_spot",
            "advisory": True,
        }

    def _packet(self, channel: str, payload: Dict[str, Any], source: str) -> Dict[str, Any]:
        return {
            "channel": channel,
            "source": source,
            "payload": payload,
            "ingested_at": time.time(),
            "content_hash": hashlib.sha256(
                str(payload).encode()
            ).hexdigest()[:16],
        }

    @staticmethod
    def _flag(t: Dict[str, Any]) -> Optional[str]:
        try:
            val = float(t["value"])
            lo, hi = t.get("ref_low"), t.get("ref_high")
            if lo is not None and val < float(lo):
                return "L"
            if hi is not None and val > float(hi):
                return "H"
        except (TypeError, ValueError):
            pass
        return None

    def status(self) -> Dict[str, Any]:
        return {
            "node": "UniversalClinicalIngest",
            "channels": list(self.SUPPORTED_CHANNELS),
            "packets_built": len(self._packets),
            "standards": ["LOINC", "FHIR Observation", "VCF", "PGx phenotype"],
            "status": "READY",
        }
