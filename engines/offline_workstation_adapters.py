"""Real, local-only biomedical file and chemical adapters for a portable workstation.

No HTTP clients, model downloads, clinical inference, patient names or accessions
are returned. Every operation requires an explicitly authorized *local* source.
The public research gateway MUST NOT import this file or accept patient uploads.
"""
from __future__ import annotations

import csv
import hashlib
import importlib.metadata
import json
import math
import re
from pathlib import Path
from typing import Any

MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_DICOM_PIXELS = 4_000_000
MAX_RECORDS = 1000
MAX_PDF_PAGES = 32
_COMPONENTS = {
    "dicom": ("pydicom", "pydicom", "3.0.2", "MIT", "Part-10 CT/MR metadata and optional pixel QC"),
    "sequences": ("Bio", "biopython", "1.88", "Biopython License", "FASTA/FASTQ aggregate quality"),
    "chemistry": ("rdkit", "rdkit", "2026.9.2", "BSD-3-Clause", "SDF/SMILES molecular descriptors"),
    "papers": ("pypdf", "pypdf", "7.1.0", "BSD-3-Clause", "PDF text extraction availability and counts"),
}


class OfflineWorkstationError(ValueError):
    """A bounded offline reader could not safely process the requested input."""


def capability_report() -> dict[str, Any]:
    """Report *installed* packages, never equate catalog entries with installation."""
    components = {}
    for name, (_, package, expected, license_id, function) in _COMPONENTS.items():
        try:
            installed = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            installed = None
        components[name] = {
            "package": package, "expected_version": expected,
            "installed_version": installed, "enabled": installed == expected,
            "license_identity": license_id, "function": function,
            "tested_with_actual_local_file": False,
        }
    return {
        "version": "1.0", "mode": "explicit_local_authorized_only",
        "network_required_for_analysis": False,
        "on_device_model_inference_enabled": False,
        "clinical_validation_completed": False,
        "components": components,
        "not_installed_or_not_verified": [k for k, v in components.items() if not v["enabled"]],
    }


def _require(name: str):
    """Import a locally installed, version-pinned, known package only."""
    from importlib import import_module
    module, package, expected, _, _ = _COMPONENTS[name]
    try:
        installed = importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        raise OfflineWorkstationError(name + " offline adapter is not installed") from None
    if installed != expected:
        raise OfflineWorkstationError(name + " version has not passed the pinned workstation contract")
    return import_module(module)


def _dcm(path: Path, pixel_qc: bool) -> dict[str, Any]:
    _require("dicom")
    from pydicom import dcmread
    try:
        ds = dcmread(path, stop_before_pixels=True, force=False)
        transfer_uid = ds.file_meta.get("TransferSyntaxUID") if ds.file_meta else None
        rows, cols = int(ds.get("Rows", 0)), int(ds.get("Columns", 0))
        frames = int(ds.get("NumberOfFrames", 1))
        if not (0 < rows <= 8192 and 0 < cols <= 8192 and 0 < frames <= 10000):
            raise OfflineWorkstationError("DICOM image geometry is missing or unbounded")
        compressed = bool(transfer_uid and transfer_uid.is_compressed)
        result = {
            "format": "dicom", "adapter": "pydicom", "modality": str(ds.get("Modality", ""))[:12],
            "rows": rows, "columns": cols, "frames": frames,
            "transfer_syntax_declared": bool(transfer_uid),
            "compressed_transfer_syntax": compressed,
            "pixel_qc_requested": pixel_qc, "pixel_qc_performed": False,
            "warning": "Image statistics are not interpretation, segmentation or a radiologist report.",
        }
        if not pixel_qc:
            return result
        if compressed:
            result["pixel_qc_status"] = "compressed_codec_not_enabled_for_safe_local_qc"
            return result
        if rows * cols * frames > MAX_DICOM_PIXELS:
            result["pixel_qc_status"] = "pixel_budget_exceeded"
            return result
        bits = int(ds.get("BitsAllocated", 0))
        samples = int(ds.get("SamplesPerPixel", 1))
        if bits <= 0 or bits > 32 or samples != 1:
            result["pixel_qc_status"] = "unsupported_pixel_representation"
            return result
        ds = dcmread(path, force=False)
        import numpy as np
        pixels = np.asarray(ds.pixel_array, dtype="float64")
        if pixels.size > MAX_DICOM_PIXELS:
            raise OfflineWorkstationError("Decoded pixel count exceeded local budget")
        lut_used = False
        if str(ds.get("Modality", "")) == "CT":
            from pydicom.pixels import apply_modality_lut
            pixels = np.asarray(apply_modality_lut(ds.pixel_array, ds), dtype="float64")
            lut_used = True
        finite = pixels[np.isfinite(pixels)]
        if finite.size != pixels.size or finite.size == 0:
            raise OfflineWorkstationError("Nonfinite or empty decoded pixel array")
        result.update({
            "pixel_qc_performed": True, "pixel_qc_status": "numerical_quality_check_only",
            "pixel_count": int(finite.size), "modality_lut_applied": lut_used,
            "pixel_min": round(float(finite.min()), 4),
            "pixel_max": round(float(finite.max()), 4),
            "pixel_mean": round(float(finite.mean()), 4),
        })
        return result
    except OfflineWorkstationError:
        raise
    except Exception:
        raise OfflineWorkstationError("Unable to decode local DICOM file safely") from None


def _sequences(path: Path, suffix: str) -> dict[str, Any]:
    _require("sequences")
    from Bio import SeqIO
    fmt = "fastq" if suffix in {".fq", ".fastq"} else "fasta"
    n = total = gc = low_quality = 0
    try:
        for record in SeqIO.parse(str(path), fmt):
            n += 1
            if n > MAX_RECORDS:
                raise OfflineWorkstationError("Sequence record budget exceeded")
            seq = str(record.seq).upper()
            if not seq or any(x not in "ACGTN" for x in seq):
                raise OfflineWorkstationError("Only DNA ACGTN alphabet accepted by this QC adapter")
            total += len(seq)
            gc += seq.count("G") + seq.count("C")
            if fmt == "fastq":
                qs = record.letter_annotations.get("phred_quality") or []
                low_quality += sum(q < 20 for q in qs)
        if not n:
            raise OfflineWorkstationError("No sequence records present")
        return {
            "format": fmt, "adapter": "biopython", "sequence_count": n, "base_count": total,
            "gc_fraction": round(gc / total, 6),
            "base_calls_below_q20": low_quality if fmt == "fastq" else None,
            "raw_sequences_returned": False,
            "warning": "Reference build, consent, contamination and clinical variants not evaluated.",
        }
    except OfflineWorkstationError:
        raise
    except Exception:
        raise OfflineWorkstationError("Unable to parse local FASTA/FASTQ safely") from None


def molecule_descriptors(smiles: str) -> dict[str, Any]:
    """Actual RDKit physics-adjacent descriptors; NOT predicted affinity or efficacy."""
    _require("chemistry")
    if not isinstance(smiles, str) or not 1 <= len(smiles) <= 300 or any(ord(c) < 32 for c in smiles):
        raise OfflineWorkstationError("SMILES structural input invalid or too long")
    from rdkit import Chem
    from rdkit.Chem import Descriptors, Crippen, Lipinski, rdMolDescriptors
    mol = Chem.MolFromSmiles(smiles)
    if mol is None or mol.GetNumAtoms() > 200:
        raise OfflineWorkstationError("SMILES is invalid or exceeds molecular atom budget")
    return {
        "format": "smiles", "adapter": "rdkit",
        "atom_count": mol.GetNumAtoms(),
        "molecular_weight": round(float(Descriptors.MolWt(mol)), 4),
        "calculated_logp": round(float(Crippen.MolLogP(mol)), 4),
        "h_bond_donors": int(Lipinski.NumHDonors(mol)),
        "h_bond_acceptors": int(Lipinski.NumHAcceptors(mol)),
        "polar_surface_area": round(float(rdMolDescriptors.CalcTPSA(mol)), 4),
        "raw_structure_returned": False, "binding_affinity_calculated": False,
        "toxicity_predicted": False, "therapeutic_efficacy_predicted": False,
        "warning": "Molecular descriptors alone do not establish binding, ADMET, toxicity, safety or efficacy.",
    }


def _sdf(path: Path) -> dict[str, Any]:
    _require("chemistry")
    from rdkit import Chem
    from rdkit.Chem import Descriptors
    count = bad = 0
    weights: list[float] = []
    try:
        supplier = Chem.SDMolSupplier(str(path), sanitize=True, removeHs=True)
        for mol in supplier:
            count += 1
            if count > MAX_RECORDS:
                raise OfflineWorkstationError("Molecular record budget exceeded")
            if mol is None or mol.GetNumAtoms() > 200:
                bad += 1
                continue
            weights.append(float(Descriptors.MolWt(mol)))
    except OfflineWorkstationError:
        raise
    except Exception:
        raise OfflineWorkstationError("Unable to read local SDF molecules safely") from None
    if not count:
        raise OfflineWorkstationError("Empty SDF molecule collection")
    return {"format": "sdf", "adapter": "rdkit", "molecules": count,
            "parsed_molecules": len(weights), "invalid_molecules": bad,
            "mean_molecular_weight": round(sum(weights) / len(weights), 4) if weights else None,
            "structures_returned": False, "binding_affinity_calculated": False,
            "warning": "No docking, target assignment or treatment prediction performed."}


def _pdf(path: Path) -> dict[str, Any]:
    _require("papers")
    from pypdf import PdfReader
    try:
        reader = PdfReader(str(path), strict=True)
        if reader.is_encrypted or not 0 < len(reader.pages) <= MAX_PDF_PAGES:
            raise OfflineWorkstationError("Encrypted, empty or oversized PDF not supported")
        extractable = 0
        total = 0
        for page in reader.pages:
            body = page.extract_text() or ""
            if body.strip():
                extractable += 1
            total += len(body)
            if total > 2_000_000:
                raise OfflineWorkstationError("PDF extracted text budget exceeded")
        return {
            "format": "pdf", "adapter": "pypdf", "pages": len(reader.pages),
            "text_pages": extractable, "extracted_character_count": total,
            "text_returned": False, "ocr_performed": False,
            "scientific_claims_reviewed": False,
            "warning": "Image-only PDFs require separate local OCR; reading text does not verify a paper.",
        }
    except OfflineWorkstationError:
        raise
    except Exception:
        raise OfflineWorkstationError("Unable to read local PDF safely") from None


def _lab_json(path: Path) -> dict[str, Any]:
    """Read real local FHIR Observation counts WITHOUT exporting subject or values."""
    try:
        root = json.loads(path.read_text(encoding="utf8"))
    except (OSError, UnicodeError, ValueError):
        raise OfflineWorkstationError("Invalid local FHIR JSON") from None
    if not isinstance(root, dict):
        raise OfflineWorkstationError("FHIR input must be a structured resource")
    kind = root.get("resourceType")
    if kind == "Observation":
        records = [root]
    elif kind == "Bundle" and root.get("type") in {"collection", "transaction", "batch"}:
        entries = root.get("entry")
        if not isinstance(entries, list) or len(entries) > MAX_RECORDS:
            raise OfflineWorkstationError("FHIR Bundle entries invalid or exceed record budget")
        records = [x.get("resource") for x in entries if isinstance(x, dict)]
    else:
        raise OfflineWorkstationError("Only local FHIR Observation and bounded Bundles supported")
    if not records or len(records) > MAX_RECORDS or any(not isinstance(r, dict) or r.get("resourceType") != "Observation" for r in records):
        raise OfflineWorkstationError("FHIR Bundle contains unsupported or missing resources")
    loinc = units = 0
    for record in records:
        code = record.get("code")
        if isinstance(code, dict) and isinstance(code.get("coding"), list):
            loinc += int(any(isinstance(x, dict) and x.get("system") == "http://loinc.org" for x in code["coding"]))
        quantity = record.get("valueQuantity")
        if isinstance(quantity, dict) and isinstance(quantity.get("unit"), str):
            units += 1
    return {
        "format": "fhir_json", "adapter": "stdlib_fhir_structure", "observations": len(records),
        "loinc_system_declared": loinc, "units_supplied": units,
        "values_returned": False, "patient_identifiers_returned": False,
        "reference_ranges_verified": False, "loinc_codes_validated": False,
        "warning": "Declared LOINC codes, units, ranges and clinical significance require clinical validation.",
    }


def _csv(path: Path, delimiter: str) -> dict[str, Any]:
    n = measured = units = 0
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f, delimiter=delimiter, strict=True)
            if not reader.fieldnames or len(reader.fieldnames) > 100:
                raise OfflineWorkstationError("Invalid CSV/TSV columns")
            for row in reader:
                n += 1
                if n > MAX_RECORDS or None in row:
                    raise OfflineWorkstationError("Tabular row budget/shape exceeded")
                measured += int(bool((row.get("value") or "").strip()))
                units += int(bool((row.get("unit") or "").strip()))
        return {
            "format": "tsv" if delimiter == "\t" else "csv",
            "adapter": "stdlib_csv", "rows": n, "measurement_rows": measured,
            "rows_with_units": units, "raw_values_returned": False,
            "patient_identifiers_returned": False,
            "warning": "No patient values, unit conversion or reference-range assessment exported.",
        }
    except OfflineWorkstationError:
        raise
    except Exception:
        raise OfflineWorkstationError("Unable to read local tabular lab data safely") from None


def inspect_local_file(path: Path | str, *, authorized_local: bool = False,
                       pixel_qc: bool = False, include_sha256: bool = False) -> dict[str, Any]:
    """Local-only no-PHI summary; explicit authorization is mandatory even for synthetic inputs."""
    if authorized_local is not True:
        raise OfflineWorkstationError("Explicit local authorization required; no public uploads")
    p = Path(path)
    try:
        if p.is_symlink() or not p.is_file() or not 0 < p.stat().st_size <= MAX_FILE_BYTES:
            raise OfflineWorkstationError("Local file missing, unsafe or exceeds 64 MiB limit")
    except OSError:
        raise OfflineWorkstationError("Unable to access local file") from None
    suffix = p.suffix.lower()
    if suffix in {".dcm", ".dicom"}:
        outcome = _dcm(p, pixel_qc)
    elif suffix in {".fa", ".fasta", ".fq", ".fastq"}:
        outcome = _sequences(p, suffix)
    elif suffix == ".sdf":
        outcome = _sdf(p)
    elif suffix == ".pdf":
        outcome = _pdf(p)
    elif suffix == ".json":
        outcome = _lab_json(p)
    elif suffix in {".csv", ".tsv"}:
        outcome = _csv(p, "\t" if suffix == ".tsv" else ",")
    else:
        raise OfflineWorkstationError("No locally validated reader for this extension")
    outcome.update({
        "mode": "authorized_local_file_only", "network_calls": 0,
        "patient_identifiers_returned": False,
        "diagnosis_generated": False, "treatment_recommended": False,
        "human_review_required": True, "clinical_validation_completed": False,
        "file_size_bytes": p.stat().st_size, "file_sha256_included": bool(include_sha256),
    })
    if include_sha256:
        # A content digest of identifiable data can itself be sensitive: local use only.
        with p.open("rb") as handle:
            digest = hashlib.sha256()
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        outcome["file_sha256"] = digest.hexdigest()
        outcome["digest_warning"] = "A patient-file digest may be identifying; never share publicly."
    return outcome
