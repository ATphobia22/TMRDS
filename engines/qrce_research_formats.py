"""Bounded local-only inspector for explicitly synthetic biomedical research fixtures.

Does NOT upload patient records, diagnose, interpret clinical tests, accept real
genomic samples, or grant unrestricted 'any format' parsing. Optional readers
for BAM/CRAM/DICOM/HL7 remain separate, authorized pipelines.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import re
from typing import Any

MAX_FILE_BYTES = 262_144
MAX_ROWS = 100
_ALLOWED_TEXT = {".csv", ".tsv", ".json", ".vcf", ".fa", ".fasta", ".fq", ".fastq"}
_UNSUPPORTED = {
    ".dcm": ("DICOM", "pydicom or DCMTK; authorized PACS data required"),
    ".dicom": ("DICOM", "pydicom or DCMTK; authorized PACS data required"),
    ".bam": ("BAM", "pysam/htslib; genome build and access approval required"),
    ".cram": ("CRAM", "pysam/htslib; matching reference genome required"),
    ".bcf": ("BCF", "bcftools/htslib binary parser required"),
    ".h5ad": ("AnnData", "anndata/scanpy; reference release and dataset access review"),
    ".parquet": ("Parquet", "pyarrow optional; data-governance review required"),
    ".xlsx": ("Excel", "openpyxl optional; no patient-level file ingestion"),
    ".hl7": ("HL7 v2", "hl7apy/HAPI integration; medical authorization required"),
    ".sdf": ("SDF", "RDKit chemistry reader; bonds/valences require validation"),
    ".cif": ("mmCIF", "gemmi or Biopython MMCIFParser; structure provenance required"),
    ".pdb": ("PDB", "Biopython/Gemmi structural parser; experimental vs predicted distinction"),
}
_PERSON_TOKENS = frozenset({
    "patient", "patientid", "subject", "subjectid", "name", "fullname",
    "birthdate", "birth_date", "dob", "phone", "email", "address",
    "mrn", "ssn", "socialsecuritynumber", "person", "personid",
    "medicalrecordnumber", "patientname", "firstname", "lastname", "identifier",
    "patientidentifier", "given", "family", "telecom", "account", "memberid", "policyid",
})
_LOINC = re.compile(r"^[0-9]{1,8}-[0-9]$")
_CODE = re.compile(r"^[A-Za-z0-9_.:/-]{1,80}$")
_BASES = frozenset("ACGTN")
_PII = re.compile(r"\b[0-9]{3}-[0-9]{2}-[0-9]{4}\b|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
_VCF_REF = re.compile(r"^[ACGTN]{1,100}$", re.I)


class SyntheticFormatError(ValueError):
    """Explicit fixture policy or structural validation failure."""


def _safe_scalar(value: Any, context: str) -> float:
    if isinstance(value, bool):
        raise SyntheticFormatError(context + " must be a finite numeric measurement")
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        raise SyntheticFormatError(context + " must be a finite numeric measurement") from None
    if not math.isfinite(number) or abs(number) > 1.0e30:
        raise SyntheticFormatError(context + " must be a finite numeric measurement")
    return number


def _normalized_record(code: Any, value: Any, unit: Any) -> dict[str, Any]:
    if not isinstance(code, str) or not _CODE.fullmatch(code):
        raise SyntheticFormatError("Synthetic lab code missing or malformed")
    if unit is not None and (not isinstance(unit, str) or len(unit) > 48 or
                             any(ord(c) < 32 for c in unit)):
        raise SyntheticFormatError("Unsupported unit metadata")
    return {
        "code": code, "value": _safe_scalar(value, "Synthetic result value"),
        "unit": unit or None,
        "loinc_pattern_matched": bool(_LOINC.fullmatch(code)),
        "loinc_mapping_verified": False,
        "reference_range_available": False,
        "clinical_interpretation_allowed": False,
    }


def _is_personal_field(key: str) -> bool:
    return key.lower().replace("_", "").replace("-", "") in _PERSON_TOKENS


def _reject_personal_keys(value: Any, *, depth: int = 0) -> None:
    if depth > 8:
        raise SyntheticFormatError("Excessively nested fixture")
    if isinstance(value, dict):
        if any(_is_personal_field(str(key)) for key in value):
            raise SyntheticFormatError("Patient or identity fields are not permitted in public research fixtures")
        for item in value.values():
            _reject_personal_keys(item, depth=depth + 1)
    elif isinstance(value, list):
        if len(value) > MAX_ROWS * 10:
            raise SyntheticFormatError("Fixture list too large")
        for item in value:
            _reject_personal_keys(item, depth=depth + 1)


def _read_tabular(body: str, delimiter: str) -> dict[str, Any]:
    reader = csv.DictReader(io.StringIO(body), delimiter=delimiter, strict=True)
    columns = reader.fieldnames or []
    if len(columns) > 24 or len(columns) != len(set(columns)):
        raise SyntheticFormatError("Duplicate or excessive columns")
    if any(_is_personal_field(x) for x in columns):
        raise SyntheticFormatError("Patient identity columns forbidden")
    if not {"value", "unit"} <= set(columns) or not ("code" in columns or "loinc" in columns):
        raise SyntheticFormatError("Synthetic tabular fixture must contain code/loinc,value,unit")
    results = []
    for row in reader:
        if len(results) >= MAX_ROWS:
            raise SyntheticFormatError("Too many synthetic observations")
        if None in row:
            raise SyntheticFormatError("Unexpected extra fields")
        results.append(_normalized_record(row.get("code") or row.get("loinc"),
                                           row.get("value"), row.get("unit")))
    return {"record_count": len(results), "records": results}


def _read_fhir_json(body: str) -> dict[str, Any]:
    obj = json.loads(body)
    _reject_personal_keys(obj)
    if isinstance(obj, dict) and obj.get("resourceType") == "Bundle":
        if obj.get("type") not in ("collection", "transaction", "batch"):
            raise SyntheticFormatError("FHIR Bundle type unsupported")
        entries = obj.get("entry") or []
        if not isinstance(entries, list):
            raise SyntheticFormatError("FHIR entries not a list")
        observations = [entry.get("resource") for entry in entries
                        if isinstance(entry, dict)]
    elif isinstance(obj, dict) and obj.get("resourceType") == "Observation":
        observations = [obj]
    elif isinstance(obj, dict) and isinstance(obj.get("measurements"), list):
        observations = obj["measurements"]
    else:
        raise SyntheticFormatError("Expected synthetic FHIR Observation/Bundle or measurements list")
    if len(observations) > MAX_ROWS:
        raise SyntheticFormatError("Too many synthetic observations")
    results = []
    for observation in observations:
        if not isinstance(observation, dict):
            raise SyntheticFormatError("Invalid synthetic observation")
        if observation.get("resourceType") not in (None, "Observation"):
            raise SyntheticFormatError("Non-Observation FHIR resource rejected")
        if observation.get("resourceType") == "Observation":
            codes = (observation.get("code") or {}).get("coding") or []
            if not isinstance(codes, list) or len(codes) != 1:
                raise SyntheticFormatError("Exactly one FHIR coding required")
            coding = codes[0]
            if not isinstance(coding, dict):
                raise SyntheticFormatError("FHIR code invalid")
            if coding.get("system") != "http://loinc.org":
                raise SyntheticFormatError("Only explicit LOINC system can be read as LOINC")
            quantity = observation.get("valueQuantity") or {}
            results.append(_normalized_record(coding.get("code"),
                                               quantity.get("value"),
                                               quantity.get("unit") or quantity.get("code")))
        else:
            results.append(_normalized_record(observation.get("code"), observation.get("value"),
                                               observation.get("unit")))
    return {"record_count": len(results), "records": results, "coding_review_required": True}


def _read_vcf(body: str) -> dict[str, Any]:
    lines = [line for line in body.splitlines() if line.strip()]
    if not lines or not lines[0].startswith("##fileformat=VCFv"):
        raise SyntheticFormatError("VCF fileformat header required")
    cols = [line for line in lines if line.startswith("#CHROM")]
    if len(cols) != 1:
        raise SyntheticFormatError("VCF required column header missing")
    header = cols[0].lstrip("#").split("\t")
    if header[:8] != ["CHROM", "POS", "ID", "REF", "ALT", "QUAL", "FILTER", "INFO"] or len(header) != 8:
        raise SyntheticFormatError("Sample genotype columns rejected; only 8-column public synthetic VCF accepted")
    variants = []
    for line in lines:
        if line.startswith("#"):
            continue
        fields = line.split("\t")
        if len(fields) != 8:
            raise SyntheticFormatError("Sample genotypes or malformed VCF row")
        if len(variants) >= MAX_ROWS:
            raise SyntheticFormatError("Too many synthetic variants")
        chrom, pos, variant_id, ref, alt = fields[:5]
        if not re.fullmatch(r"(?:[0-9]{1,2}|X|Y|MT)", chrom) or not pos.isdecimal() or not (1 <= int(pos) <= 500_000_000):
            raise SyntheticFormatError("VCF coordinates invalid")
        if not _VCF_REF.fullmatch(ref) or not all(_VCF_REF.fullmatch(a) for a in alt.split(",")):
            raise SyntheticFormatError("Only unambiguous ACGTN alleles supported")
        variants.append({
            "chromosome": chrom, "position": int(pos),
            "variant_id": variant_id if re.fullmatch(r"rs[0-9]{1,12}", variant_id) else None,
            "reference_length": len(ref), "alternate_allele_count": len(alt.split(",")),
            "assembly": "UNSPECIFIED", "allelic_consequence_verified": False,
        })
    return {"record_count": len(variants), "records": variants,
            "warning": "Reference genome, alleles and sample-free research origin require review"}


def _read_fasta(body: str) -> dict[str, Any]:
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    if not lines or not lines[0].startswith(">"):
        raise SyntheticFormatError("FASTA header required")
    counts: list[dict[str, Any]] = []
    sequence = ""
    for line in lines[1:] + [">end"]:
        if line.startswith(">"):
            if not sequence:
                raise SyntheticFormatError("FASTA empty sequence")
            if len(counts) >= MAX_ROWS:
                raise SyntheticFormatError("Too many synthetic sequences")
            if any(x not in _BASES for x in sequence):
                raise SyntheticFormatError("Only synthetic DNA alphabet ACGTN supported")
            counts.append({"sequence_length": len(sequence),
                           "gc_fraction": round((sequence.count("G") + sequence.count("C")) / len(sequence), 6),
                           "sequence_sha256": hashlib.sha256(sequence.encode()).hexdigest(),
                           "sequence_released": False})
            sequence = ""
        else:
            sequence += line.upper()
            if len(sequence) > 100_000:
                raise SyntheticFormatError("Sequence size cap exceeded")
    return {"record_count": len(counts), "records": counts}


def _read_fastq(body: str) -> dict[str, Any]:
    lines = body.splitlines()
    if len(lines) % 4 != 0:
        raise SyntheticFormatError("FASTQ must contain complete 4-line records")
    if len(lines) // 4 > MAX_ROWS:
        raise SyntheticFormatError("Too many synthetic reads")
    counts = []
    for i in range(0, len(lines), 4):
        header, sequence, plus, quality = lines[i:i + 4]
        sequence = sequence.upper()
        if not header.startswith("@") or not plus.startswith("+") or not sequence or \
                any(x not in _BASES for x in sequence) or len(sequence) != len(quality):
            raise SyntheticFormatError("Synthetic FASTQ structure invalid")
        if any(not 33 <= ord(c) <= 126 for c in quality):
            raise SyntheticFormatError("FASTQ quality encoding unsupported")
        counts.append({
            "read_length": len(sequence),
            "min_phred33": min(ord(c) - 33 for c in quality),
            "sequence_released": False,
        })
    return {"record_count": len(counts), "records": counts,
            "quality_encoding_assumed": "phred+33; independently verify upstream instrument"}


def inspect_synthetic_fixture(*, suffix: str, data: bytes, explicitly_synthetic: bool) -> dict[str, Any]:
    """Return sanitized counts and synthetic records; never return original body."""
    if explicitly_synthetic is not True:
        raise SyntheticFormatError("Only verified synthetic/public fixtures allowed; patient records require authorized service")
    if not isinstance(data, bytes) or len(data) > MAX_FILE_BYTES or len(data) == 0:
        raise SyntheticFormatError("Unsupported or oversized fixture (256 KiB max)")
    suffix = suffix.lower()
    if suffix not in _ALLOWED_TEXT:
        if suffix in _UNSUPPORTED:
            kind, prerequisite = _UNSUPPORTED[suffix]
            return {"status": "external_reader_required", "format": kind,
                    "prerequisite": prerequisite, "content_inspected": False,
                    "clinical_promotion_allowed": False}
        raise SyntheticFormatError("Unrecognized file format; no generic parser fallback")
    if b"\x00" in data:
        raise SyntheticFormatError("Binary contents not accepted by text inspector")
    try:
        body = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise SyntheticFormatError("UTF-8 text required") from exc
    if _PII.search(body):
        raise SyntheticFormatError("Personal identifiers detected; public fixture refused")
    try:
        if suffix == ".csv":
            parsed = _read_tabular(body, ",")
        elif suffix == ".tsv":
            parsed = _read_tabular(body, "\t")
        elif suffix == ".json":
            parsed = _read_fhir_json(body)
        elif suffix == ".vcf":
            parsed = _read_vcf(body)
        elif suffix in (".fa", ".fasta"):
            parsed = _read_fasta(body)
        else:
            parsed = _read_fastq(body)
    except (json.JSONDecodeError, csv.Error, UnicodeError) as exc:
        raise SyntheticFormatError("Malformed synthetic format") from exc
    return {
        "schema_version": "1.0", "status": "synthetic_fixture_inspected",
        "format": suffix.lstrip("."), "declared_synthetic": True,
        "artifact_sha256": hashlib.sha256(data).hexdigest(),
        "artifact_sha256_scope": "exact_input_bytes_not_authenticity",
        "patient_data_accepted": False, "clinical_promotion_allowed": False,
        "human_authority_final": True,
        **parsed,
    }


def format_capabilities() -> list[dict[str, str]]:
    rows = [{"extension": suffix, "state": "local_synthetic_text_reader",
             "patient_data_allowed": "false", "requires": "stdlib"}
            for suffix in sorted(_ALLOWED_TEXT)]
    rows.extend({"extension": suffix, "state": "external_reader_required",
                 "patient_data_allowed": "false", "requires": details[1]}
                for suffix, details in sorted(_UNSUPPORTED.items()))
    return rows
