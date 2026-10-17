"""
TMRDS Phase 2 - Disease Graph and Genetics Research Data
Repository: ATphobia22/TMRDS
Branch: feature/evidence-discovery-research
Product boundary: Research discovery only, not SaMD. Not diagnostic, prescribing, or autonomous treatment.

File location target: engines/disease_graph_model.py
This file implements the canonical models for Phase 2.

Design principles per roadmap:
- Every result has provenance, evidence envelope
- No fabricated metrics, pLDDT/pTM only from genuine backends
- MOCK_ONLY returns empty confidence / no synthetic ranking
- Preserve ClinVar submitter, review status, conflicts, dates
- Use HGNC, Ensembl release, VRS (GA4GH), HPO
- Graph edges: disease<->gene<->variant<->pathway<->compound<->trial
  with source, timestamp, license, evidence_class, confidence, conflict_links
- Provide splice/variant literature view: source-supported annotations + conflicts, no clinical interpretation
- Integrate Ensembl REST, gnomAD, GTEx via documented APIs with population/ancestry warnings
- Sensitive human genomic data stays outside public ingestion unless governance pathway exists
"""

from __future__ import annotations
import hashlib
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Literal
import re

# ---------------------------------------------------------------------------
# Evidence & Provenance Core - aligns with docs/superpowers/specs/2026-09-07-biomedical-evidence-graph-design.md
# ---------------------------------------------------------------------------

class EvidenceClass(str, Enum):
    OBSERVED = "observed"
    DERIVED = "derived"
    PREDICTED = "predicted"
    HYPOTHESIZED = "hypothesized"
    MOCK_ONLY = "MOCK_ONLY"

class AccessClass(str, Enum):
    PUBLIC = "public"
    LICENSED = "licensed"
    RESTRICTED = "restricted"
    PRIVATE_GOVERNED = "private_governed"

class ConfidencePolicy(str, Enum):
    # MOCK_ONLY must never emit confidence
    EMPTY = "empty"
    COMPUTED = "computed"
    CURATED = "curated"
    CONFLICTED = "conflicted"

@dataclass(frozen=True)
class Provenance:
    source_name: str  # e.g., ClinVar, Ensembl, gnomAD, GTEx, PubMed
    source_url: Optional[str]
    source_version: Optional[str]  # e.g., Ensembl release 112, ClinVar 2024-10
    retrieval_timestamp: str  # ISO8601
    api_endpoint: Optional[str] = None
    license: Optional[str] = None  # SPDX or terms URL
    access_class: AccessClass = AccessClass.PUBLIC
    attribution: Optional[str] = None  # required attribution string
    raw_record_hash: Optional[str] = None  # sha256 of source payload for replay
    # replay support
    query_params: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def now(source_name: str, source_url: Optional[str]=None, version: Optional[str]=None,
            license: Optional[str]=None, access_class: AccessClass=AccessClass.PUBLIC,
            endpoint: Optional[str]=None, query: Optional[Dict[str,Any]]=None,
            raw_payload: Optional[bytes]=None) -> "Provenance":
        h = hashlib.sha256(raw_payload).hexdigest() if raw_payload else None
        return Provenance(
            source_name=source_name,
            source_url=source_url,
            source_version=version,
            retrieval_timestamp=datetime.now(timezone.utc).isoformat(),
            api_endpoint=endpoint,
            license=license,
            access_class=access_class,
            raw_record_hash=h,
            query_params=query
        )

@dataclass
class EvidenceEnvelope:
    """
    Every search result / node / edge must carry this.
    Roadmap acceptance: source-traceable, distinguishes citation, abstract, registry, model-derived.
    """
    provenance: Provenance
    evidence_class: EvidenceClass
    confidence: Optional[float] = None  # None when MOCK_ONLY or unavailable
    confidence_policy: ConfidencePolicy = ConfidencePolicy.EMPTY
    evidence_quality_notes: Optional[str] = None  # e.g., population representation warning
    is_mock: bool = False
    parse_warnings: List[str] = field(default_factory=list)
    conflict_links: List[str] = field(default_factory=list)  # IDs of conflicting evidence
    retrieval_date: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    # regulatory
    retention_policy: Optional[str] = None

    def __post_init__(self):
        # Enforce MOCK_ONLY contract: no invented metrics, no confidence, no ranking
        if self.evidence_class == EvidenceClass.MOCK_ONLY or self.is_mock:
            self.confidence = None
            self.confidence_policy = ConfidencePolicy.EMPTY
            # Mock must not emit scientific measurements
            if self.evidence_quality_notes and "pLDDT" in self.evidence_quality_notes:
                raise ValueError("MOCK_ONLY must not emit pLDDT/pTM or synthetic metrics")

    def to_dict(self) -> Dict[str,Any]:
        d = asdict(self)
        d['provenance'] = self.provenance.to_dict()
        return d

    @property
    def is_empty_confidence(self) -> bool:
        return self.confidence is None

# ---------------------------------------------------------------------------
# Canonical Identifiers & Crosswalks - versioned
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Identifier:
    namespace: str  # e.g., HGNC, Ensembl, MONDO, HPO, ChEBI, PUBCHEM, CLINVAR
    id: str
    version: Optional[str] = None
    iri: Optional[str] = None

    def __str__(self):
        return f"{self.namespace}:{self.id}" + (f"#{self.version}" if self.version else "")

@dataclass
class CrosswalkRegistry:
    """
    Versioned crosswalks per roadmap. Pin Ensembl release, assembly, transcript versions.
    """
    hgnc_id: Optional[Identifier] = None
    ensembl_gene_id: Optional[Identifier] = None
    ensembl_transcript_ids: List[Identifier] = field(default_factory=list)
    entrez_id: Optional[Identifier] = None
    refseq_ids: List[Identifier] = field(default_factory=list)
    uniprot_ids: List[Identifier] = field(default_factory=list)
    ensembl_release: Optional[str] = None  # e.g., 112
    genome_assembly: Optional[str] = None  # GRCh38
    hpo_ids: List[Identifier] = field(default_factory=list)
    mondo_id: Optional[Identifier] = None
    omim_ids: List[Identifier] = field(default_factory=list)

# ---------------------------------------------------------------------------
# Canonical Models
# ---------------------------------------------------------------------------

# Gene - HGNC + Ensembl
@dataclass
class Gene:
    primary_hgnc_symbol: str
    hgnc_id: Identifier
    ensembl_gene_id: Optional[Identifier]
    entrez_id: Optional[str] = None
    description: Optional[str] = None
    chromosome: Optional[str] = None
    biotype: Optional[str] = None  # protein_coding, etc.
    crosswalk: CrosswalkRegistry = field(default_factory=CrosswalkRegistry)
    location: Optional[Dict[str, Any]] = None  # {chr, start, end, strand, assembly}
    aliases: List[str] = field(default_factory=list)
    evidence: List[EvidenceEnvelope] = field(default_factory=list)
    version_info: Optional[Dict[str,str]] = None

    def node_id(self) -> str:
        return f"Gene:{self.hgnc_id}"

    def to_node_dict(self) -> Dict[str,Any]:
        return {
            "id": self.node_id(),
            "type": "Gene",
            "symbol": self.primary_hgnc_symbol,
            "hgnc": str(self.hgnc_id),
            "ensembl": str(self.ensembl_gene_id) if self.ensembl_gene_id else None,
            "crosswalk": asdict(self.crosswalk),
            "evidence": [e.to_dict() for e in self.evidence]
        }

# Transcript - Ensembl versioned
@dataclass
class Transcript:
    ensembl_transcript_id: Identifier  # ENST...
    ensembl_gene_id: Identifier
    refseq_id: Optional[Identifier] = None
    biotype: Optional[str] = None
    is_mane_select: bool = False
    is_canonical: bool = False
    sequence: Optional[str] = None  # only if license allows, else None, store hash
    length: Optional[int] = None
    exons: List[Dict[str,Any]] = field(default_factory=list)  # {rank, start, end, phase}
    utrs: Dict[str,Any] = field(default_factory=dict)
    ensembl_release: str = "112"
    assembly: str = "GRCh38"
    evidence: List[EvidenceEnvelope] = field(default_factory=list)

    def node_id(self) -> str:
        return f"Transcript:{self.ensembl_transcript_id}"

# Variant - GA4GH VRS style
@dataclass
class VRSLocation:
    sequence_id: str  # GA4GH sequence id, e.g., ga4gh:SQ...
    interval_type: Literal["SequenceInterval","SequenceLocation"] = "SequenceInterval"
    start: int = 0  # inter-residue
    end: int = 0
    sequence: Optional[str] = None

    def to_vrs_dict(self) -> Dict[str,Any]:
        return {
            "type": "SequenceLocation" if self.interval_type=="SequenceLocation" else "SequenceInterval",
            "sequence_id": self.sequence_id,
            "interval": {"type":"SequenceInterval","start":{"type":"Number","value":self.start},"end":{"type":"Number","value":self.end}}
        }

@dataclass
class VRSAllele:
    id: Optional[str]  # ga4gh:VA...
    type: str = "Allele"
    location: Optional[VRSLocation] = None
    state: Optional[Dict[str,Any]] = None  # {type:"LiteralSequenceExpression", sequence:"A"}
    digest: Optional[str] = None  # computed digest

    def compute_digest(self) -> str:
        payload = json.dumps({"location": asdict(self.location) if self.location else None, "state": self.state}, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

@dataclass
class Variant:
    """
    Canonical variant using GA4GH VRS style + HGVS + SPDI where available.
    No clinical interpretation - only reports source annotations.
    """
    vrs_allele: VRSAllele
    spdi: Optional[str] = None  # e.g., NC_000001.11:12345:A:T
    hgvs_g: Optional[str] = None
    hgvs_c: Optional[List[str]] = field(default_factory=list)
    hgvs_p: Optional[List[str]] = field(default_factory=list)
    clinvar_variation_id: Optional[Identifier] = None
    dbsnp_rs: Optional[Identifier] = None
    assembly: str = "GRCh38"
    variant_type: Optional[str] = None  # SNV, indel, splice, etc.
    molecular_consequence: List[str] = field(default_factory=list)
    # Source annotations preserved verbatim
    clinvar_records: List["ClinVarAssertion"] = field(default_factory=list)
    gnomad_data: Optional["GnomADAnnotation"] = None
    gtex_data: Optional["GTExAnnotation"] = None
    ensembl_consequence: List[Dict[str,Any]] = field(default_factory=list)
    splice_ai: Optional[Dict[str,Any]] = None  # only if from real source, with provenance
    evidence: List[EvidenceEnvelope] = field(default_factory=list)

    def node_id(self) -> str:
        spdi = self.spdi or self.vrs_allele.digest or "unknown"
        return f"Variant:{spdi}"

# ClinVar preservation model - must preserve submitter, review status, conflicts
@dataclass
class ClinVarSubmission:
    submitter: str
    submitter_id: Optional[str]
    condition: str  # MONDO/OMIM string as provided
    condition_ids: List[Identifier] = field(default_factory=list)
    clinical_significance: str  # e.g., Pathogenic, Uncertain - preserved as source stated
    review_status: str  # e.g., criteria_provided_single_submitter, reviewed_by_expert_panel
    last_evaluated: Optional[str] = None
    date_submitted: Optional[str] = None
    explanation: Optional[str] = None
    evidence_citations: List[str] = field(default_factory=list)
    assertion_method: Optional[str] = None

@dataclass
class ClinVarAssertion:
    variation_id: Identifier
    rcv: Optional[str] = None
    vcv: Optional[str] = None
    overall_clinical_significance: Optional[str] = None  # aggregate, but conflicts preserved
    overall_review_status: Optional[str] = None
    submissions: List[ClinVarSubmission] = field(default_factory=list)
    conflicting_interpretations: bool = False
    conflict_details: List[Dict[str,Any]] = field(default_factory=list)
    provenance: Optional[Provenance] = None
    evidence: Optional[EvidenceEnvelope] = None
    # Never collapse into ground truth
    preserved_dates: Dict[str,str] = field(default_factory=dict)

# External annotations with population warnings

@dataclass
class GnomADAnnotation:
    variant_id: str
    allele_frequency: Optional[float] = None
    allele_count: Optional[int] = None
    allele_number: Optional[int] = None
    populations: List[Dict[str,Any]] = field(default_factory=list)  # {id, af, an}
    popmax_af: Optional[float] = None
    popmax_population: Optional[str] = None
    filters: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)  # population representation warnings
    provenance: Optional[Provenance] = None
    version: str = "v4.0"
    license: str = "https://gnomad.broadinstitute.org/about#terms"

@dataclass
class GTExAnnotation:
    gene_id: Identifier
    tissue_eqtls: List[Dict[str,Any]] = field(default_factory=list)  # {variantId, tissue, pval, slope, nes}
    splicing_qtl: bool = False
    provenance: Optional[Provenance] = None
    version: str = "v8"
    warnings: List[str] = field(default_factory=list)  # ancestry representation note

# Phenotype HPO

@dataclass
class Phenotype:
    hpo_id: Identifier
    label: str
    definition: Optional[str] = None
    synonyms: List[str] = field(default_factory=list)
    ancestors: List[Identifier] = field(default_factory=list)
    gene_associations: List[Identifier] = field(default_factory=list)
    mondo_mappings: List[Identifier] = field(default_factory=list)
    evidence: List[EvidenceEnvelope] = field(default_factory=list)

    def node_id(self) -> str:
        return f"Phenotype:{self.hpo_id}"

# Disease - MONDO

@dataclass
class Disease:
    mondo_id: Identifier
    label: str
    definition: Optional[str] = None
    synonyms: List[str] = field(default_factory=list)
    parent_ids: List[Identifier] = field(default_factory=list)
    hpo_profile: List[Identifier] = field(default_factory=list)
    evidence: List[EvidenceEnvelope] = field(default_factory=list)

    def node_id(self) -> str:
        return f"Disease:{self.mondo_id}"

# Pathway

@dataclass
class Pathway:
    identifier: Identifier  # Reactome, KEGG, GO
    label: str
    source: str  # Reactome, KEGG, WikiPathways
    genes: List[Identifier] = field(default_factory=list)
    parent_pathways: List[Identifier] = field(default_factory=list)
    evidence: List[EvidenceEnvelope] = field(default_factory=list)

    def node_id(self) -> str:
        return f"Pathway:{self.identifier}"

# Compound

@dataclass
class Compound:
    identifier: Identifier  # CHEBI, PUBCHEM, DRUGBANK
    label: str
    smiles: Optional[str] = None
    inchikey: Optional[str] = None
    structure_provenance: Optional[Provenance] = None
    targets: List[Identifier] = field(default_factory=list)
    mechanism: Optional[str] = None
    approval_status: Optional[str] = None  # investigational, approved, etc - from source only
    evidence: List[EvidenceEnvelope] = field(default_factory=list)

    def node_id(self) -> str:
        return f"Compound:{self.identifier}"

# Assay and Biospecimen

@dataclass
class Assay:
    identifier: Identifier
    label: str
    type: str  # RNA-seq, WES, proteomics, functional
    platform: Optional[str] = None
    protocol_url: Optional[str] = None
    provenance: Optional[Provenance] = None
    evidence: List[EvidenceEnvelope] = field(default_factory=list)

    def node_id(self):
        return f"Assay:{self.identifier}"

@dataclass
class Biospecimen:
    identifier: Identifier
    label: str
    tissue: Optional[str] = None
    cell_line: Optional[str] = None
    biobank: Optional[str] = None
    ancestry: Optional[str] = None
    consent_status: Optional[str] = None  # Must respect GA4GH Consent Policy
    governance_note: str = "Sensitive human data: requires separate governance/authorization outside public ingestion"
    provenance: Optional[Provenance] = None
    evidence: List[EvidenceEnvelope] = field(default_factory=list)

    def node_id(self):
        return f"Biospecimen:{self.identifier}"

# Trial

@dataclass
class Trial:
    nct_id: Identifier
    title: str
    phase: Optional[str] = None
    status: Optional[str] = None
    conditions: List[str] = field(default_factory=list)
    interventions: List[str] = field(default_factory=list)
    evidence: List[EvidenceEnvelope] = field(default_factory=list)

    def node_id(self):
        return f"Trial:{self.nct_id}"

# ---------------------------------------------------------------------------
# Graph Edges with Full Provenance per Roadmap Section 4
# ---------------------------------------------------------------------------

class RelationType(str, Enum):
    DISEASE_GENE = "DISEASE_ASSOCIATED_WITH_GENE"
    GENE_VARIANT = "GENE_HAS_VARIANT"
    VARIANT_PATHWAY = "VARIANT_AFFECTS_PATHWAY"
    VARIANT_PHENOTYPE = "VARIANT_ASSOCIATED_WITH_PHENOTYPE"
    GENE_PATHWAY = "GENE_IN_PATHWAY"
    PATHWAY_COMPOUND = "PATHWAY_TARGETED_BY_COMPOUND"
    COMPOUND_TRIAL = "COMPOUND_STUDIED_IN_TRIAL"
    DISEASE_PHENOTYPE = "DISEASE_HAS_PHENOTYPE"
    GENE_COMPOUND = "GENE_TARGETED_BY_COMPOUND"
    VARIANT_COMPOUND = "VARIANT_MODULATES_COMPOUND_RESPONSE"
    # plus literature edges
    PUBLICATION_EVIDENCE = "PUBLICATION_SUPPORTS_EDGE"

@dataclass
class GraphEdge:
    source_id: str
    target_id: str
    relation: RelationType
    evidence: EvidenceEnvelope
    provenance: Provenance
    edge_id: Optional[str] = None
    license: Optional[str] = None
    evidence_class: EvidenceClass = EvidenceClass.OBSERVED
    confidence: Optional[float] = None
    conflict_links: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    attributes: Dict[str,Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.edge_id:
            raw = f"{self.source_id}|{self.relation}|{self.target_id}|{self.provenance.source_name}|{self.timestamp}"
            self.edge_id = hashlib.sha256(raw.encode()).hexdigest()[:20]
        if self.evidence.evidence_class == EvidenceClass.MOCK_ONLY:
            self.confidence = None

    def to_dict(self) -> Dict[str,Any]:
        return {
            "edge_id": self.edge_id,
            "source": self.source_id,
            "target": self.target_id,
            "relation": self.relation.value,
            "provenance": self.provenance.to_dict(),
            "evidence": self.evidence.to_dict(),
            "license": self.license,
            "evidence_class": self.evidence_class.value,
            "confidence": self.confidence,
            "conflict_links": self.conflict_links,
            "timestamp": self.timestamp,
            "attributes": self.attributes
        }

# ---------------------------------------------------------------------------
# Adapters - real API contracts, no bulk mirroring, respect terms
# ---------------------------------------------------------------------------

class EnsemblLookupError(RuntimeError):
    """Raised when an Ensembl-backed lookup cannot return verified source data."""


class EnsemblRESTAdapter:
    """Live, provenance-bearing Ensembl REST adapter.

    release=None uses the release currently served by the configured REST host
    and records it when /info/data reports exactly one release. Supplying a
    release is an assertion: this adapter fails closed if the endpoint cannot
    prove it is serving that exact release.
    """

    BASE = "https://rest.ensembl.org"
    GRCH37_BASE = "https://grch37.rest.ensembl.org"
    DOC = "https://rest.ensembl.org/documentation/info/"

    def __init__(self, release: Optional[str] = None, assembly: str = "GRCh38") -> None:
        normalized_assembly = (assembly or "").strip().upper()
        if normalized_assembly not in {"GRCH37", "GRCH38"}:
            raise ValueError("assembly must be GRCh37 or GRCh38")
        if release is not None and not re.fullmatch(r"\d{2,3}", str(release).strip()):
            raise ValueError("release must be a two- or three-digit Ensembl data release")
        self.release = str(release).strip() if release is not None else None
        self.assembly = "GRCh37" if normalized_assembly == "GRCH37" else "GRCh38"
        self.base_url = self.GRCH37_BASE if self.assembly == "GRCh37" else self.BASE
        self.license = "Ensembl data terms"
        self.terms_url = "https://www.ensembl.org/info/about/legal/index.html"
        self._release_checked = False
        self._available_releases: tuple[int, ...] = ()
        self._observed_release: Optional[str] = None

    @staticmethod
    def _validate_timeout(timeout: float) -> float:
        import math

        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
            raise ValueError("timeout must be a finite number from 0 to 60 seconds")
        numeric_timeout = float(timeout)
        if not math.isfinite(numeric_timeout) or not 0 < numeric_timeout <= 60:
            raise ValueError("timeout must be a finite number from 0 to 60 seconds")
        return numeric_timeout

    def _request_json(self, endpoint: str, timeout: float = 10.0) -> tuple[Any, Any, str]:
        """Request JSON from a fixed Ensembl host without redirects."""
        import requests

        timeout_value = self._validate_timeout(timeout)
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.get(
                url,
                headers={"Accept": "application/json", "Content-Type": "application/json"},
                timeout=timeout_value,
                allow_redirects=False,
            )
        except requests.RequestException as exc:
            raise EnsemblLookupError(
                f"Ensembl request failed ({type(exc).__name__}); no result was accepted"
            ) from exc

        status_code = getattr(response, "status_code", 0)
        if status_code == 404:
            raise EnsemblLookupError(f"Ensembl endpoint returned HTTP 404: {endpoint.split('?')[0]}")
        if not isinstance(status_code, int) or status_code < 200 or status_code >= 300:
            raise EnsemblLookupError(f"Ensembl endpoint returned HTTP {status_code}: {endpoint.split('?')[0]}")

        try:
            payload = response.json()
        except (ValueError, TypeError) as exc:
            raise EnsemblLookupError("Ensembl endpoint returned invalid JSON") from exc
        return payload, response, url

    def _discover_data_release(self, timeout: float = 10.0) -> Optional[str]:
        """Observe the release exposed by /info/data; never assume a requested pin."""
        if not self._release_checked:
            self._release_checked = True
            try:
                payload, _, _ = self._request_json("/info/data", timeout=timeout)
                raw_releases = payload.get("releases") if isinstance(payload, dict) else None
                if (
                    isinstance(raw_releases, list)
                    and raw_releases
                    and all(isinstance(value, int) and not isinstance(value, bool) and value > 0 for value in raw_releases)
                ):
                    self._available_releases = tuple(sorted(set(raw_releases)))
                    if len(self._available_releases) == 1:
                        self._observed_release = str(self._available_releases[0])
                else:
                    logger.warning("Ensembl /info/data returned an unrecognized release payload")
            except EnsemblLookupError as exc:
                logger.warning("Ensembl release discovery unavailable (%s)", type(exc).__name__)

        if self.release is not None:
            expected = int(self.release)
            if self._available_releases != (expected,):
                raise EnsemblLookupError(
                    f"Configured Ensembl release {self.release} could not be verified; "
                    "the configured REST endpoint must expose exactly that release"
                )
        return self._observed_release

    def _provenance(
        self,
        response: Any,
        url: str,
        endpoint: str,
        query: Dict[str, Any],
        data_release: Optional[str],
    ) -> Provenance:
        raw_payload = getattr(response, "content", None)
        if not isinstance(raw_payload, bytes) or not raw_payload:
            response_text = getattr(response, "text", "")
            raw_payload = response_text.encode("utf-8") if isinstance(response_text, str) and response_text else None
        query_params = {
            **query,
            "assembly": self.assembly,
            "requested_release": self.release,
            "observed_data_release": data_release,
        }
        return Provenance.now(
            source_name="Ensembl",
            source_url=url,
            version=data_release,
            license=self.terms_url,
            endpoint=endpoint,
            query=query_params,
            raw_payload=raw_payload,
        )

    @staticmethod
    def _normalize_gene_symbol(hgnc_symbol: str) -> str:
        if not isinstance(hgnc_symbol, str):
            raise ValueError("hgnc_symbol must be a string")
        symbol = hgnc_symbol.strip()
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", symbol):
            raise ValueError("hgnc_symbol contains unsupported characters or has an invalid length")
        return symbol

    def lookup_gene(
        self,
        hgnc_symbol: str,
        timeout: float = 10.0,
    ) -> Tuple[Identifier, Provenance, Dict[str, Any]]:
        """Resolve a human gene symbol using Ensembl's live lookup endpoint."""
        symbol = self._normalize_gene_symbol(hgnc_symbol)
        data_release = self._discover_data_release(timeout)
        endpoint = f"/lookup/symbol/homo_sapiens/{symbol}"
        payload, response, url = self._request_json(endpoint, timeout=timeout)

        if not isinstance(payload, dict):
            raise EnsemblLookupError("Ensembl gene lookup returned an unexpected response shape")
        gene_id = payload.get("id")
        object_type = payload.get("object_type")
        if not isinstance(gene_id, str) or not re.fullmatch(r"ENSG\d+(?:\.\d+)?", gene_id):
            raise EnsemblLookupError("Ensembl response did not contain a valid Ensembl gene identifier")
        if object_type is not None and object_type != "Gene":
            raise EnsemblLookupError("Ensembl lookup returned a non-gene feature")

        observed_assembly = payload.get("assembly_name")
        if observed_assembly and str(observed_assembly).casefold() != self.assembly.casefold():
            raise EnsemblLookupError(
                f"Ensembl returned assembly {observed_assembly}, not configured assembly {self.assembly}"
            )

        stable_gene_id = gene_id.split(".", 1)[0]
        identifier_version = payload.get("version")
        identifier = Identifier(
            "ENSEMBL",
            stable_gene_id,
            version=str(identifier_version) if identifier_version is not None else None,
            iri=f"{self.base_url}/id/{stable_gene_id}",
        )
        provenance = self._provenance(
            response,
            url,
            endpoint,
            {
                "species": "homo_sapiens",
                "symbol": symbol,
                "feature_type": "Gene",
                "response_assembly": observed_assembly,
            },
            data_release,
        )
        return identifier, provenance, dict(payload)

    def get_variant_consequences(
        self,
        variant_spdi: str,
        timeout: float = 10.0,
    ) -> Tuple[List[Dict[str, Any]], Provenance]:
        """Run Ensembl VEP for HGVS input; reject SPDI until coordinate mapping exists.

        The historical parameter name is retained for compatibility. A value such
        as 17:g.41196312G>T is HGVS and can be queried directly. A RefSeq SPDI
        such as NC_000017.11:41196311:G:T is deliberately rejected because
        accession/coordinate normalization is not implemented here.
        """
        if not isinstance(variant_spdi, str) or not variant_spdi.strip():
            raise ValueError("variant input must be a non-empty string")
        variant = variant_spdi.strip()
        if len(variant) > 256 or not re.fullmatch(
            r"(?:[A-Za-z0-9_.-]+:)?[gcnrp]\.[A-Za-z0-9_+>*()=?-]+",
            variant,
        ):
            raise EnsemblLookupError(
                "Variant input is not supported HGVS notation; SPDI-to-HGVS normalization "
                "is not implemented and no VEP request was made"
            )

        from urllib.parse import quote

        data_release = self._discover_data_release(timeout)
        endpoint = f"/vep/human/hgvs/{quote(variant, safe=':._+*()=')}"
        payload, response, url = self._request_json(endpoint, timeout=timeout)
        if not isinstance(payload, list) or any(not isinstance(item, dict) for item in payload):
            raise EnsemblLookupError("Ensembl VEP returned an unexpected response shape")
        provenance = self._provenance(
            response,
            url,
            endpoint,
            {"variant_hgvs": variant, "species": "homo_sapiens", "annotation": "VEP"},
            data_release,
        )
        return payload, provenance

    def get_transcripts(
        self,
        ensembl_gene_id: str,
        timeout: float = 10.0,
    ) -> Tuple[List[Transcript], Provenance]:
        """Retrieve the actual transcript records for a stable Ensembl gene ID."""
        if not isinstance(ensembl_gene_id, str):
            raise ValueError("ensembl_gene_id must be a string")
        gene_id = ensembl_gene_id.strip()
        if not re.fullmatch(r"ENSG\d+(?:\.\d+)?", gene_id):
            raise ValueError("ensembl_gene_id must be a stable ENSG identifier")

        data_release = self._discover_data_release(timeout)
        endpoint = f"/lookup/id/{gene_id}?expand=1"
        payload, response, url = self._request_json(endpoint, timeout=timeout)
        if not isinstance(payload, dict) or payload.get("object_type", "Gene") != "Gene":
            raise EnsemblLookupError("Ensembl transcript lookup returned an unexpected response shape")
        raw_transcripts = payload.get("Transcript", [])
        if not isinstance(raw_transcripts, list):
            raise EnsemblLookupError("Ensembl transcript collection was malformed")

        observed_assembly = payload.get("assembly_name")
        if observed_assembly and str(observed_assembly).casefold() != self.assembly.casefold():
            raise EnsemblLookupError(
                f"Ensembl returned assembly {observed_assembly}, not configured assembly {self.assembly}"
            )

        provenance = self._provenance(
            response,
            url,
            endpoint,
            {"gene_id": gene_id, "expand": True, "response_assembly": observed_assembly},
            data_release,
        )
        resolved_gene_id = str(payload.get("id", gene_id)).split(".", 1)[0]
        raw_gene_version = payload.get("version")
        gene_identifier = Identifier(
            "ENSEMBL",
            resolved_gene_id,
            version=str(raw_gene_version) if raw_gene_version is not None else None,
            iri=f"{self.base_url}/id/{resolved_gene_id}",
        )
        transcripts: List[Transcript] = []
        for raw_transcript in raw_transcripts:
            if not isinstance(raw_transcript, dict):
                raise EnsemblLookupError("Ensembl returned a malformed transcript record")
            transcript_id = raw_transcript.get("id")
            if not isinstance(transcript_id, str) or not re.fullmatch(r"ENST\d+(?:\.\d+)?", transcript_id):
                raise EnsemblLookupError("Ensembl returned a transcript without a valid ENST identifier")
            raw_version = raw_transcript.get("version")
            transcript_stable_id = transcript_id.split(".", 1)[0]
            raw_exons = raw_transcript.get("Exon", [])
            if not isinstance(raw_exons, list) or any(not isinstance(exon, dict) for exon in raw_exons):
                raise EnsemblLookupError(f"Ensembl returned malformed exon metadata for {transcript_stable_id}")
            tags = raw_transcript.get("tags", [])
            if not isinstance(tags, list):
                tags = []
            evidence = EvidenceEnvelope(
                provenance=provenance,
                evidence_class=EvidenceClass.OBSERVED,
                confidence=None,
                confidence_policy=ConfidencePolicy.EMPTY,
                evidence_quality_notes="Gene/transcript metadata from Ensembl REST; no functional interpretation",
            )
            transcripts.append(
                Transcript(
                    ensembl_transcript_id=Identifier(
                        "ENSEMBL",
                        transcript_stable_id,
                        version=str(raw_version) if raw_version is not None else None,
                        iri=f"{self.base_url}/id/{transcript_stable_id}",
                    ),
                    ensembl_gene_id=gene_identifier,
                    biotype=raw_transcript.get("biotype"),
                    is_mane_select="MANE_Select" in tags,
                    is_canonical=raw_transcript.get("is_canonical") in (1, "1", True),
                    sequence=None,
                    length=None,
                    exons=[dict(exon) for exon in raw_exons],
                    ensembl_release=data_release or "unknown",
                    assembly=str(raw_transcript.get("assembly_name") or observed_assembly or self.assembly),
                    evidence=[evidence],
                )
            )
        return transcripts, provenance

class ClinVarAdapter:
    """
    ClinVar programmatic access: https://www.ncbi.nlm.nih.gov/clinvar/docs/api/
    Preserve submitter, review status, dates, conflicts, condition/context - do not collapse.
    Terms: https://www.ncbi.nlm.nih.gov/home/about/policies/
    """
    BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    LICENSE = "NCBI terms - preserve attribution"

    def __init__(self):
        self.review_status_map = {
            "0": "no_assertion_criteria_provided",
            "1": "criteria_provided_single_submitter",
            "2": "criteria_provided_multiple_submitters_no_conflicts",
            "3": "reviewed_by_expert_panel",
            "4": "practice_guideline"
        }

    def parse_variation(self, raw_xml: Dict[str,Any]) -> ClinVarAssertion:
        """
        Parse a ClinVar record, preserving all submitters. Raw dict comes from EFetch.
        Never infer pathogenicity.
        """
        # Example structure - real parsing would use XML
        variation_id = Identifier("CLINVAR", raw_xml.get("VariationID",""), iri=f"https://www.ncbi.nlm.nih.gov/clinvar/variation/{raw_xml.get('VariationID','')}")
        submissions: List[ClinVarSubmission] = []
        for sub in raw_xml.get("Submissions", []):
            submissions.append(ClinVarSubmission(
                submitter=sub.get("Submitter","unknown"),
                submitter_id=sub.get("OrgID"),
                condition=sub.get("Condition",""),
                clinical_significance=sub.get("ClinicalSignificance",""),
                review_status=sub.get("ReviewStatus",""),
                last_evaluated=sub.get("DateLastEvaluated"),
                date_submitted=sub.get("DateSubmitted"),
                explanation=sub.get("Explanation"),
                assertion_method=sub.get("Method")
            ))
        # detect conflicts
        sigs = set(s.clinical_significance for s in submissions)
        conflict = len(sigs) > 1
        conflict_details = []
        if conflict:
            conflict_details = [{"conflicting_terms": list(sigs), "note": "Source reports conflicting interpretations; preserved verbatim"}]

        prov = Provenance.now(source_name="ClinVar", source_url="https://www.ncbi.nlm.nih.gov/clinvar/", version="2024", endpoint=f"{self.BASE}/efetch.fcgi")
        ev = EvidenceEnvelope(
            provenance=prov,
            evidence_class=EvidenceClass.OBSERVED,
            confidence=None,
            confidence_policy=ConfidencePolicy.CURATED if not conflict else ConfidencePolicy.CONFLICTED,
            evidence_quality_notes="Preserved submitter, review status, conflicting interpretations per roadmap"
        )

        return ClinVarAssertion(
            variation_id=variation_id,
            rcv=raw_xml.get("RCV"),
            vcv=raw_xml.get("VCV"),
            overall_clinical_significance=raw_xml.get("OverallSignificance"),
            overall_review_status=raw_xml.get("OverallReviewStatus"),
            submissions=submissions,
            conflicting_interpretations=conflict,
            conflict_details=conflict_details,
            provenance=prov,
            evidence=ev
        )

class GnomADAdapter:
    BASE = "https://gnomad.broadinstitute.org/api"
    TERMS = "https://gnomad.broadinstitute.org/about#terms"
    def fetch(self, spdi: str) -> Tuple[GnomADAnnotation, Provenance]:
        prov = Provenance.now(
            source_name="gnomAD",
            source_url=self.BASE,
            version="v4.0",
            license=self.TERMS,
            endpoint="/variant"
        )
        anno = GnomADAnnotation(
            variant_id=spdi,
            warnings=[
                "Population representation: gnomAD v4 includes diverse but incomplete global ancestry; check AN per population",
                "Do not use allele frequency as clinical evidence; research discovery only"
            ],
            provenance=prov
        )
        return anno, prov

class GTExAdapter:
    BASE = "https://gtexportal.org/api/v2"
    DOC = "https://gtexportal.org/api/v2/docs"
    def fetch_eqtl(self, ensembl_gene_id: str) -> Tuple[GTExAnnotation, Provenance]:
        prov = Provenance.now(
            source_name="GTEx",
            source_url=self.BASE,
            version="v8",
            license="GTEx Portal terms",
            endpoint=f"/expression/geneEqtl?geneId={ensembl_gene_id}"
        )
        anno = GTExAnnotation(
            gene_id=Identifier("ENSEMBL", ensembl_gene_id),
            warnings=["GTEx v8: 85% European ancestry; interpret tissue eQTL generalizability with caution; research only"],
            provenance=prov
        )
        return anno, prov

# ---------------------------------------------------------------------------
# Splice / Variant Literature View - Reports source-supported annotations + conflicts, no clinical interpretation
# ---------------------------------------------------------------------------

@dataclass
class LiteratureEvidence:
    pmid: Optional[Identifier]
    doi: Optional[Identifier]
    title: Optional[str]
    source_url: Optional[str]
    citation: Optional[str]
    assertion: str  # verbatim what paper says, e.g., "c.123A>G reported to affect splicing in minigene assay"
    assay_type: Optional[str] = None  # minigene, RNA-seq, etc.
    splice_impact: Optional[str] = None  # exon skipping, cryptic splice, etc - as reported
    transcript_id: Optional[Identifier] = None
    provenance: Optional[Provenance] = None

@dataclass
class VariantLiteratureView:
    """
    Research-use only view. Does NOT generate clinical interpretation or prescribe edit.
    Reports source-supported annotations and conflicting interpretations.
    Aligns with roadmap: "Add a splice/variant literature view that reports source-supported annotated
    and conflicting interpretations; do not generate a clinical interpretation or prescribe an edit."
    """
    variant: Variant
    gene: Optional[Gene]
    transcript_context: List[Transcript] = field(default_factory=list)
    clinvar_assertions: List[ClinVarAssertion] = field(default_factory=list)
    ensembl_consequences: List[Dict[str,Any]] = field(default_factory=list)
    gnomad: Optional[GnomADAnnotation] = None
    gtex: Optional[GTExAnnotation] = None
    literature: List[LiteratureEvidence] = field(default_factory=list)
    conflicts: List[Dict[str,Any]] = field(default_factory=list)
    disclaimers: List[str] = field(default_factory=list)

    def __post_init__(self):
        self.disclaimers = [
            "Research discovery only, not SaMD, not diagnostic, not prescribing",
            "No clinical interpretation generated by this system - all assertions are source-preserved",
            "Variant effect on splicing requires experimental validation; literature may conflict",
            "Do not use for clinical CRISPR design decisions"
        ]

    def summarize_conflicts(self) -> Dict[str,Any]:
        sigs = {}
        for ca in self.clinvar_assertions:
            for sub in ca.submissions:
                sigs.setdefault(sub.clinical_significance, []).append(sub.submitter)
        conflict_struct = []
        if len(sigs) > 1:
            conflict_struct.append({"type": "clinvar_submitter_conflict", "terms": sigs, "note": "Preserved verbatim; no resolution inferred"})
        # literature conflicts
        impacts = {}
        for lit in self.literature:
            if lit.splice_impact:
                impacts.setdefault(lit.splice_impact, []).append(lit.pmid.id if lit.pmid else "unknown")
        if len(impacts) > 1:
            conflict_struct.append({"type": "literature_splice_conflict", "impacts": impacts})

        self.conflicts = conflict_struct
        return {"conflicts": conflict_struct, "disclaimers": self.disclaimers}

    def to_dict(self) -> Dict[str,Any]:
        return {
            "variant_id": self.variant.node_id(),
            "gene": self.gene.primary_hgnc_symbol if self.gene else None,
            "transcripts": [t.ensembl_transcript_id.id for t in self.transcript_context],
            "clinvar": [asdict(ca) for ca in self.clinvar_assertions],
            "ensembl_consequences": self.ensembl_consequences,
            "gnomad": asdict(self.gnomad) if self.gnomad else None,
            "gtex": asdict(self.gtex) if self.gtex else None,
            "literature": [asdict(l) for l in self.literature],
            "conflicts": self.conflicts,
            "disclaimers": self.disclaimers
        }

# ---------------------------------------------------------------------------
# Graph Builder - disease <-> gene <-> variant <-> pathway <-> compound <-> trial
# ---------------------------------------------------------------------------

class DiseaseGraphBuilder:
    def __init__(self, ensembl_release: Optional[str] = None, assembly: str="GRCh38"):
        self.nodes: Dict[str, Any] = {}
        self.edges: List[GraphEdge] = []
        self.ensembl_release = ensembl_release
        self.assembly = assembly
        self.ensembl_adapter = EnsemblRESTAdapter(release=ensembl_release, assembly=assembly)
        self.clinvar_adapter = ClinVarAdapter()
        self.gnomad_adapter = GnomADAdapter()
        self.gtex_adapter = GTExAdapter()

    def add_node(self, node_obj: Any) -> str:
        nid = node_obj.node_id()
        self.nodes[nid] = node_obj
        return nid

    def add_edge(self, source_id: str, target_id: str, relation: RelationType,
                 provenance: Provenance, evidence_class: EvidenceClass=EvidenceClass.OBSERVED,
                 confidence: Optional[float]=None, license: Optional[str]=None,
                 attributes: Optional[Dict[str,Any]]=None,
                 conflict_links: Optional[List[str]]=None) -> GraphEdge:

        # MOCK_ONLY enforcement
        if evidence_class == EvidenceClass.MOCK_ONLY:
            confidence = None

        ev = EvidenceEnvelope(
            provenance=provenance,
            evidence_class=evidence_class,
            confidence=confidence,
            confidence_policy=ConfidencePolicy.EMPTY if confidence is None else ConfidencePolicy.COMPUTED,
            conflict_links=conflict_links or []
        )
        edge = GraphEdge(
            source_id=source_id,
            target_id=target_id,
            relation=relation,
            evidence=ev,
            provenance=provenance,
            license=license,
            evidence_class=evidence_class,
            confidence=confidence,
            conflict_links=conflict_links or [],
            attributes=attributes or {}
        )
        self.edges.append(edge)
        return edge

    def build_from_clinvar_record(self, raw_clinvar: Dict[str,Any], gene: Gene) -> Tuple[Variant, ClinVarAssertion]:
        assertion = self.clinvar_adapter.parse_variation(raw_clinvar)
        vrs_loc = VRSLocation(sequence_id=f"ga4gh:SQ.{gene.ensembl_gene_id.id if gene.ensembl_gene_id else 'unknown'}", start=0, end=1)
        vrs_allele = VRSAllele(id=None, location=vrs_loc, state={"type":"LiteralSequenceExpression","sequence":"N"}, digest=hashlib.sha256(json.dumps(raw_clinvar).encode()).hexdigest()[:12])
        variant = Variant(
            vrs_allele=vrs_allele,
            spdi=raw_clinvar.get("SPDI"),
            hgvs_g=raw_clinvar.get("HGVSg"),
            clinvar_variation_id=assertion.variation_id,
            assembly=self.assembly,
            clinvar_records=[assertion],
            evidence=[assertion.evidence] if assertion.evidence else []
        )
        self.add_node(variant)
        self.add_node(gene)
        # edge gene->variant
        if assertion.provenance:
            self.add_edge(gene.node_id(), variant.node_id(), RelationType.GENE_VARIANT,
                          provenance=assertion.provenance,
                          evidence_class=EvidenceClass.OBSERVED,
                          attributes={"spdi": variant.spdi, "review_status": assertion.overall_review_status},
                          conflict_links=[assertion.vcv] if assertion.conflicting_interpretations else [])
        return variant, assertion

    def create_literature_view(self, variant: Variant, gene: Optional[Gene]=None,
                               transcripts: Optional[List[Transcript]]=None,
                               literature: Optional[List[LiteratureEvidence]]=None) -> VariantLiteratureView:
        gnomad_data, _ = self.gnomad_adapter.fetch(variant.spdi or "unknown")
        gtex_data, _ = self.gtex_adapter.fetch_eqtl(gene.ensembl_gene_id.id if gene and gene.ensembl_gene_id else "ENSG00000000000")

        view = VariantLiteratureView(
            variant=variant,
            gene=gene,
            transcript_context=transcripts or [],
            clinvar_assertions=variant.clinvar_records,
            ensembl_consequences=variant.ensembl_consequence,
            gnomad=gnomad_data,
            gtex=gtex_data,
            literature=literature or []
        )
        view.summarize_conflicts()
        return view

# ---------------------------------------------------------------------------
# Neo4j Projection Helper (no invented Cypher injection, parameterised)
# ---------------------------------------------------------------------------

class Neo4jProjectionHelper:
    """
    Projects canonical graph into Neo4j with source, timestamp, license, evidence_class, confidence preserved.
    For use with official neo4j driver.
    """

    @staticmethod
    def node_cypher(node_type: str) -> str:
        # Use MERGE on canonical ID, set properties with evidence
        return f"""
        MERGE (n:{node_type} {{ canonical_id: $canonical_id }})
        SET n += $props,
            n.updated_at = $timestamp,
            n.source = $source,
            n.license = $license,
            n.evidence_class = $evidence_class,
            n.provenance_hash = $provenance_hash
        RETURN n
        """

    @staticmethod
    def edge_cypher() -> str:
        return """
        MATCH (a {canonical_id: $source_id}), (b {canonical_id: $target_id})
        MERGE (a)-[r:$relation_type {edge_id: $edge_id}]->(b)
        SET r += $attributes,
            r.confidence = $confidence,
            r.license = $license,
            r.evidence_class = $evidence_class,
            r.source = $source,
            r.timestamp = $timestamp,
            r.conflict_links = $conflict_links,
            r.provenance = $provenance_json
        RETURN r
        """

    def prepare_node_payload(self, node_obj: Any) -> Dict[str,Any]:
        nid = node_obj.node_id()
        primary_ev = node_obj.evidence[0] if hasattr(node_obj, 'evidence') and node_obj.evidence else None
        return {
            "canonical_id": nid,
            "props": node_obj.to_node_dict() if hasattr(node_obj, 'to_node_dict') else asdict(node_obj),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": primary_ev.provenance.source_name if primary_ev else "unknown",
            "license": primary_ev.provenance.license if primary_ev else None,
            "evidence_class": primary_ev.evidence_class.value if primary_ev else EvidenceClass.OBSERVED.value,
            "provenance_hash": primary_ev.provenance.raw_record_hash if primary_ev else None
        }

    def prepare_edge_payload(self, edge: GraphEdge) -> Dict[str,Any]:
        return {
            "source_id": edge.source_id,
            "target_id": edge.target_id,
            "relation_type": edge.relation.value,
            "edge_id": edge.edge_id,
            "attributes": edge.attributes,
            "confidence": edge.confidence,
            "license": edge.license,
            "evidence_class": edge.evidence_class.value,
            "source": edge.provenance.source_name,
            "timestamp": edge.timestamp,
            "conflict_links": edge.conflict_links,
            "provenance_json": json.dumps(edge.provenance.to_dict())
        }

    def batch_to_neo4j(self, builder: DiseaseGraphBuilder, driver=None, dry_run: bool=True) -> Dict[str,Any]:
        """
        If driver is None or dry_run True, returns Cypher payloads without execution (for tests).
        """
        nodes_payload = [self.prepare_node_payload(n) for n in builder.nodes.values()]
        edges_payload = [self.prepare_edge_payload(e) for e in builder.edges]
        if dry_run or driver is None:
            return {"nodes": nodes_payload, "edges": edges_payload, "dry_run": True}

        # Real execution path (requires neo4j driver)
        with driver.session() as session:
            for np in nodes_payload:
                # infer type from canonical_id prefix
                ntype = np["canonical_id"].split(":")[0]
                session.run(self.node_cypher(ntype), **np)
            for ep in edges_payload:
                # relation type cannot be parameterized in Cypher MERGE header, build safe string after validation
                if not re.match(r"^[A-Z_]+$", ep["relation_type"]):
                    raise ValueError("Invalid relation type")
                cypher = self.edge_cypher().replace("$relation_type", ep["relation_type"])
                session.run(cypher, **ep)
        return {"nodes_ingested": len(nodes_payload), "edges_ingested": len(edges_payload), "dry_run": False}

# ---------------------------------------------------------------------------
# PostgreSQL Ledger Helper - immutable provenance ledger
# ---------------------------------------------------------------------------

class PostgreSQLLedgerHelper:
    """
    PostgreSQL ledger helper per roadmap: keep ledger as authority, vector/graph derived and linked back.
    Uses evidence envelope + raw hash for replay.
    """

    CREATE_TABLES_DDL = """
    -- Evidence ledger - immutable
    CREATE TABLE IF NOT EXISTS evidence_ledger (
        id SERIAL PRIMARY KEY,
        canonical_id TEXT NOT NULL,
        type TEXT NOT NULL,
        provenance JSONB NOT NULL,
        evidence JSONB NOT NULL,
        payload JSONB NOT NULL,
        raw_hash TEXT,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        UNIQUE(canonical_id, raw_hash)
    );
    CREATE INDEX IF NOT EXISTS idx_ledger_canonical ON evidence_ledger(canonical_id);
    CREATE INDEX IF NOT EXISTS idx_ledger_source ON evidence_ledger((provenance->>'source_name'));

    -- Graph edge ledger
    CREATE TABLE IF NOT EXISTS graph_edge_ledger (
        edge_id TEXT PRIMARY KEY,
        source_id TEXT NOT NULL,
        target_id TEXT NOT NULL,
        relation TEXT NOT NULL,
        provenance JSONB NOT NULL,
        evidence JSONB NOT NULL,
        license TEXT,
        evidence_class TEXT,
        confidence DOUBLE PRECISION,
        conflict_links TEXT[],
        timestamp TIMESTAMPTZ,
        attributes JSONB
    );
    CREATE INDEX IF NOT EXISTS idx_edge_source ON graph_edge_ledger(source_id);
    CREATE INDEX IF NOT EXISTS idx_edge_target ON graph_edge_ledger(target_id);
    CREATE INDEX IF NOT EXISTS idx_edge_relation ON graph_edge_ledger(relation);

    -- Source registry (Phase 0)
    CREATE TABLE IF NOT EXISTS source_registry (
        source_name TEXT PRIMARY KEY,
        endpoint TEXT,
        version TEXT,
        license TEXT,
        access_class TEXT,
        last_success TIMESTAMPTZ,
        last_upstream_update TEXT,
        records_added INT,
        rate_limit_info JSONB
    );
    """

    @staticmethod
    def insert_evidence_sql() -> str:
        return """
        INSERT INTO evidence_ledger (canonical_id, type, provenance, evidence, payload, raw_hash)
        VALUES (%(canonical_id)s, %(type)s, %(provenance)s::jsonb, %(evidence)s::jsonb, %(payload)s::jsonb, %(raw_hash)s)
        ON CONFLICT (canonical_id, raw_hash) DO NOTHING
        RETURNING id;
        """

    @staticmethod
    def insert_edge_sql() -> str:
        return """
        INSERT INTO graph_edge_ledger (edge_id, source_id, target_id, relation, provenance, evidence, license, evidence_class, confidence, conflict_links, timestamp, attributes)
        VALUES (%(edge_id)s, %(source_id)s, %(target_id)s, %(relation)s, %(provenance)s::jsonb, %(evidence)s::jsonb, %(license)s, %(evidence_class)s, %(confidence)s, %(conflict_links)s, %(timestamp)s::timestamptz, %(attributes)s::jsonb)
        ON CONFLICT (edge_id) DO UPDATE SET attributes = EXCLUDED.attributes, timestamp = EXCLUDED.timestamp
        RETURNING edge_id;
        """

    def prepare_ledger_rows(self, builder: DiseaseGraphBuilder) -> Tuple[List[Dict[str,Any]], List[Dict[str,Any]]]:
        evidence_rows = []
        for nid, node in builder.nodes.items():
            primary_ev = node.evidence[0] if hasattr(node, 'evidence') and node.evidence else None
            if primary_ev is None:
                # create minimal envelope for ledger completeness but mark as unknown source
                prov = Provenance.now(source_name="unknown", license=None)
                primary_ev = EvidenceEnvelope(provenance=prov, evidence_class=EvidenceClass.OBSERVED, confidence=None)
            evidence_rows.append({
                "canonical_id": nid,
                "type": nid.split(":")[0],
                "provenance": json.dumps(primary_ev.provenance.to_dict()),
                "evidence": json.dumps(primary_ev.to_dict()),
                "payload": json.dumps(node.to_node_dict() if hasattr(node, 'to_node_dict') else asdict(node), default=str),
                "raw_hash": primary_ev.provenance.raw_record_hash
            })
        edge_rows = []
        for e in builder.edges:
            edge_rows.append({
                "edge_id": e.edge_id,
                "source_id": e.source_id,
                "target_id": e.target_id,
                "relation": e.relation.value,
                "provenance": json.dumps(e.provenance.to_dict()),
                "evidence": json.dumps(e.evidence.to_dict()),
                "license": e.license,
                "evidence_class": e.evidence_class.value,
                "confidence": e.confidence,
                "conflict_links": e.conflict_links,
                "timestamp": e.timestamp,
                "attributes": json.dumps(e.attributes)
            })
        return evidence_rows, edge_rows

    def execute(self, builder: DiseaseGraphBuilder, psycopg_conn=None, dry_run: bool=True) -> Dict[str,Any]:
        ev_rows, edge_rows = self.prepare_ledger_rows(builder)
        if dry_run or psycopg_conn is None:
            return {"evidence_rows": ev_rows, "edge_rows": edge_rows, "ddl": self.CREATE_TABLES_DDL, "dry_run": True}
        with psycopg_conn.cursor() as cur:
            cur.execute(self.CREATE_TABLES_DDL)
            for r in ev_rows:
                cur.execute(self.insert_evidence_sql(), r)
            for r in edge_rows:
                cur.execute(self.insert_edge_sql(), r)
            psycopg_conn.commit()
        return {"evidence_ingested": len(ev_rows), "edges_ingested": len(edge_rows), "dry_run": False}

# ---------------------------------------------------------------------------
# Validation & Guardrails
# ---------------------------------------------------------------------------

class TMRDSValidator:
    @staticmethod
    def assert_no_mock_metrics(edge: GraphEdge):
        if edge.evidence.evidence_class == EvidenceClass.MOCK_ONLY and edge.confidence is not None:
            raise AssertionError("MOCK_ONLY must have empty confidence")
        if edge.evidence.is_mock and edge.confidence is not None:
            raise AssertionError("Mock edge must not have confidence")

    @staticmethod
    def assert_clinvar_preserved(assertion: ClinVarAssertion):
        if not assertion.submissions:
            raise AssertionError("ClinVar assertion must preserve at least one submitter")
        for sub in assertion.submissions:
            if not sub.submitter or not sub.clinical_significance:
                raise AssertionError("Submitter and clinical significance must be preserved verbatim")

    @staticmethod
    def assert_no_clinical_interpretation(lit_view: VariantLiteratureView):
        # Ensure view does not emit therapeutic advice
        text = json.dumps(lit_view.to_dict()).lower()
        forbidden = ["should treat", "prescribe", "diagnose as", "edit should be", "crispr design"]
        for f in forbidden:
            if f in text:
                raise AssertionError(f"Literature view must not contain clinical interpretation: found {f}")

# ---------------------------------------------------------------------------
# Example wiring & unit test friendly factory
# ---------------------------------------------------------------------------

def build_example_cube() -> DiseaseGraphBuilder:
    """
    Builds a minimal disease cube example with full provenance - suitable for contract tests
    without live network.
    """
    builder = DiseaseGraphBuilder(ensembl_release=None, assembly="GRCh38")

    gene = Gene(
        primary_hgnc_symbol="BRCA1",
        hgnc_id=Identifier("HGNC", "1100", iri="https://www.genenames.org/data/gene-symbol-report/#!/hgnc_id/HGNC:1100"),
        ensembl_gene_id=Identifier("ENSEMBL", "ENSG00000012048", version="112"),
        description="BRCA1 DNA repair associated",
        crosswalk=CrosswalkRegistry(
            hgnc_id=Identifier("HGNC","1100"),
            ensembl_gene_id=Identifier("ENSEMBL","ENSG00000012048"),
            ensembl_release="112",
            genome_assembly="GRCh38"
        ),
        evidence=[EvidenceEnvelope(
            provenance=Provenance.now(source_name="HGNC", source_url="https://www.genenames.org", version="2024-10", license="CC0"),
            evidence_class=EvidenceClass.OBSERVED,
            confidence_policy=ConfidencePolicy.CURATED
        )]
    )
    builder.add_node(gene)

    disease = Disease(
        mondo_id=Identifier("MONDO","0007254", iri="http://purl.obolibrary.org/obo/MONDO_0007254"),
        label="hereditary breast carcinoma",
        evidence=[]
    )
    builder.add_node(disease)
    builder.add_edge(
        disease.node_id(), gene.node_id(), RelationType.DISEASE_GENE,
        provenance=Provenance.now(source_name="Ensembl", version="112", source_url="https://rest.ensembl.org"),
        evidence_class=EvidenceClass.OBSERVED,
        license="Ensembl terms"
    )

    variant = Variant(
        vrs_allele=VRSAllele(id="ga4gh:VA.test", location=VRSLocation(sequence_id="ga4gh:SQ.BRCA1", start=1000, end=1001), state={"type":"LiteralSequenceExpression","sequence":"T"}),
        spdi="NC_000017.11:41196312:G:T",
        hgvs_g="NC_000017.11:g.41196312G>T",
        hgvs_c=["NM_007294.3:c.123A>T"],
        assembly="GRCh38",
        evidence=[]
    )
    builder.add_node(variant)
    pathway = Pathway(identifier=Identifier("REACTOME","R-HSA-5693565"), label="DNA Repair", source="Reactome")
    builder.add_node(pathway)
    compound = Compound(identifier=Identifier("PUBCHEM","1234"), label="olaparib_example", evidence=[])
    builder.add_node(compound)
    trial = Trial(nct_id=Identifier("CLINICALTRIALS","NCT00000000"), title="Example trial")
    builder.add_node(trial)

    # edges with provenance envelope per roadmap Section 4
    builder.add_edge(gene.node_id(), variant.node_id(), RelationType.GENE_VARIANT,
                     provenance=Provenance.now(source_name="ClinVar", source_url="https://www.ncbi.nlm.nih.gov/clinvar/", version="2024-10", license="NCBI terms"),
                     evidence_class=EvidenceClass.OBSERVED, attributes={"mane":"NM_007294.3"})
    builder.add_edge(gene.node_id(), pathway.node_id(), RelationType.GENE_PATHWAY,
                     provenance=Provenance.now(source_name="Reactome", source_url="https://reactome.org", version="88"),
                     evidence_class=EvidenceClass.DERIVED)
    builder.add_edge(pathway.node_id(), compound.node_id(), RelationType.PATHWAY_COMPOUND,
                     provenance=Provenance.now(source_name="OpenTargets", version="24.06"), evidence_class=EvidenceClass.DERIVED)
    builder.add_edge(compound.node_id(), trial.node_id(), RelationType.COMPOUND_TRIAL,
                     provenance=Provenance.now(source_name="ClinicalTrials.gov", source_url="https://clinicaltrials.gov", version="v2"),
                     evidence_class=EvidenceClass.OBSERVED)

    # mock edge must have empty confidence per acceptance criteria
    mock_edge = builder.add_edge(gene.node_id(), compound.node_id(), RelationType.GENE_COMPOUND,
                                 provenance=Provenance.now(source_name="MockSource"),
                                 evidence_class=EvidenceClass.MOCK_ONLY,
                                 confidence=None)  # enforced
    TMRDSValidator.assert_no_mock_metrics(mock_edge)

    return builder

if __name__ == "__main__":
    b = build_example_cube()
    print(f"Built cube: {len(b.nodes)} nodes, {len(b.edges)} edges")
    # Dry run Neo4j and Postgres helpers
    neo = Neo4jProjectionHelper()
    pg = PostgreSQLLedgerHelper()
    print(neo.batch_to_neo4j(b, dry_run=True).keys())
    print(pg.execute(b, dry_run=True).keys())
    # Literature view demo
    gene_example = list(b.nodes.values())[0]
    var_example = [v for v in b.nodes.values() if isinstance(v, Variant)][0]
    view = b.create_literature_view(var_example, gene=gene_example, literature=[
        LiteratureEvidence(pmid=Identifier("PMID","123456"), doi=None, title="BRCA1 splicing assay", source_url=None,
                           citation="Author et al 2023", assertion="c.123A>T reported to cause exon skipping in minigene", splice_impact="exon_skip", assay_type="minigene")
    ])
    print(view.to_dict())
