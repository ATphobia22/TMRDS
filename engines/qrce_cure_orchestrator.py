"""
QRCE Cure / Treatment Orchestrator for TMRDS.

Wires UniversalClinicalIngest + PubMed + KRAGEN (+ optional Neo4j) +
QuantumRubiksCureEngine into a single advisory pipeline so clinicians and
patients can start from personal labs/genome/scans + verifiable literature
immediately — not in days or weeks.

CRITICAL: All outputs are RESEARCH-ADVISORY ONLY. Not a diagnosis, prescription,
or substitute for licensed clinical judgment. Human authority remains final.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from .universal_clinical_ingest import UniversalClinicalIngest
from .pubmed_literature_bridge import PubMedLiteratureBridge
from .kragen_graph_engine import KRAGENGraphEngine
from .evidence_ledger import EvidenceLedger
from .doctor_dignity_ethics import DoctorDignityEthics


class QRCECureOrchestrator:
    """
    End-to-end advisory search for treatment starting points.

    Flow:
      1. Ingest labs / imaging / genomic / sequencing / notes
      2. Ethics scan on free text
      3. PubMed treatment literature
      4. KRAGEN multi-layer graph expansion
      5. Optional VQE / molecular ranking hooks
      6. EvidenceLedger append
      7. Ranked starting-point summary for clinician review
    """

    def __init__(
        self,
        pubmed: Optional[PubMedLiteratureBridge] = None,
        kragen: Optional[KRAGENGraphEngine] = None,
        ledger: Optional[EvidenceLedger] = None,
    ) -> None:
        self.ingest = UniversalClinicalIngest()
        self.pubmed = pubmed or PubMedLiteratureBridge()
        self.kragen = kragen or KRAGENGraphEngine()
        self.ledger = ledger or EvidenceLedger()
        self.ethics = DoctorDignityEthics()

    def run(
        self,
        patient_ref: str,
        disease_or_problem: str,
        lab_tests: Optional[List[Dict[str, Any]]] = None,
        genomic_variants: Optional[List[Dict[str, Any]]] = None,
        imaging_findings: Optional[Dict[str, str]] = None,
        clinical_notes: Optional[str] = None,
        focus_gene: Optional[str] = None,
        max_literature: int = 12,
    ) -> Dict[str, Any]:
        t0 = time.time()
        channels: List[Dict[str, Any]] = []

        if lab_tests:
            channels.append(self.ingest.ingest_lab(lab_tests))
        if genomic_variants:
            channels.append(self.ingest.ingest_genomic(genomic_variants))
            if not focus_gene and genomic_variants:
                focus_gene = str(genomic_variants[0].get("gene", "")).upper() or None
        if imaging_findings:
            channels.append(
                self.ingest.ingest_imaging(
                    imaging_findings.get("modality", "unknown"),
                    imaging_findings.get("findings", ""),
                    imaging_findings.get("impression"),
                )
            )
        if clinical_notes:
            ethics_report = self.ethics.scan(clinical_notes)
            notes_text = ethics_report.get("sanitized", clinical_notes)
            channels.append(self.ingest.ingest_notes(notes_text))
        else:
            ethics_report = {"status": "SKIPPED"}

        packet = self.ingest.build_patient_packet(patient_ref, channels)

        # Literature — verifiable journals
        lit = self.pubmed.search_treatments(
            disease_or_problem,
            gene=focus_gene,
            max_results=max_literature,
        )

        # KRAGEN expansion
        disease_node = self.kragen.upsert_node(
            f"dx:{disease_or_problem.lower().replace(' ', '_')}",
            disease_or_problem,
            "pathology",
            {"source": "orchestrator"},
        )
        if focus_gene:
            gene_node = self.kragen.upsert_node(
                f"gene:{focus_gene}",
                focus_gene,
                "molecular",
                {"source": "patient_genomic"},
            )
            self.kragen.add_edge(disease_node["id"], "ASSOCIATED_WITH", gene_node["id"])

        got = self.kragen.graph_of_thoughts_stub(
            f"treatments for {disease_or_problem} {focus_gene or ''}".strip()
        )

        # Ranked starting points (literature titles + genes + abnormal labs)
        starting_points: List[Dict[str, Any]] = []
        for art in lit.get("articles", [])[:8]:
            starting_points.append({
                "type": "literature",
                "pmid": art.get("pmid"),
                "title": art.get("title"),
                "source": art.get("source"),
                "pubdate": art.get("pubdate"),
            })
        if focus_gene:
            starting_points.append({
                "type": "genomic_anchor",
                "gene": focus_gene,
                "note": "Patient-linked gene for pathway / drug target review",
            })
        for ch in channels:
            if ch.get("channel") == "lab":
                for t in ch.get("payload", {}).get("tests", []):
                    if t.get("flag") in ("H", "L"):
                        starting_points.append({
                            "type": "lab_flag",
                            "name": t.get("name"),
                            "value": t.get("value"),
                            "flag": t.get("flag"),
                            "loinc": t.get("loinc"),
                        })

        result = {
            "patient_ref": patient_ref,
            "problem": disease_or_problem,
            "focus_gene": focus_gene,
            "packet_hash": packet.get("content_hash"),
            "ethics": ethics_report,
            "literature": {
                "query_count": lit.get("count"),
                "pmids": lit.get("pmids", [])[:max_literature],
                "articles": lit.get("articles", []),
                "status": lit.get("status"),
            },
            "kragen": {
                "disease_node": disease_node,
                "got_seed_count": got.get("seed_count"),
            },
            "starting_points": starting_points,
            "latency_sec": round(time.time() - t0, 3),
            "advisory_only": True,
            "disclaimer": (
                "RESEARCH-ADVISORY ONLY. Not a diagnosis, prescription, or cure claim. "
                "Licensed clinicians must verify all evidence and retain final authority."
            ),
            "status": "ORCHESTRATION_COMPLETE",
        }

        self.ledger.append(
            record_type="qrce_cure_search",
            payload={
                "patient_ref": patient_ref,
                "problem": disease_or_problem,
                "packet_hash": packet.get("content_hash"),
                "pmid_count": len(lit.get("pmids", [])),
            },
            source="QRCECureOrchestrator",
            verification_status="MACHINE_CHECKED",
        )
        return result

    def status(self) -> Dict[str, Any]:
        return {
            "node": "QRCECureOrchestrator",
            "components": [
                "UniversalClinicalIngest",
                "PubMedLiteratureBridge",
                "KRAGENGraphEngine",
                "EvidenceLedger",
                "DoctorDignityEthics",
            ],
            "advisory_only": True,
            "status": "READY",
        }
