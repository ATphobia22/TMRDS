"""Private, local-only research file adapters backed by real OSS libraries.

No network calls, no cloud storage, no patient identifiers in returned objects,
no diagnostic labels. These are data/geometry/chemistry *inspection* operations,
not validated image interpretation, genetic treatment, or a medical device.
"""
from __future__ import annotations

import csv
import importlib
import io
import math
import re
from pathlib import Path
from typing import Any

MAX_SCIENCE_FILE_BYTES = 128 * 1024 * 1024
MAX_DICOM_FILE_BYTES = 64 * 1024 * 1024
MAX_SEQUENCE_FILE_BYTES = 4 * 1024 * 1024
MAX_LOCAL_LAB_BYTES = 1024 * 1024
MAX_SEQUENCE_RECORDS = 128
MAX_LAB_RECORDS = 200
MAX_PIXEL_SAMPLES = 16_777_216
_VALID_LAB_CODE = re.compile(r"^[A-Za-z0-9_.:/-]{1,80}$")
_VALID_LAB_UNIT = re.compile(r"^[A-Za-z0-9_/.*%+^ -]{1,32}$")
_VALID_SMILES = re.compile(r"^[A-Za-z0-9@+\-#$%=()\[\]\\/.:*]{1,500}$")
_DNA = frozenset("ACGTN")


class FieldLabError(ValueError):
    """Fail closed when a local parser, format or privacy precondition is missing."""


def _load(module: str, package: str):
    try:
        return importlib.import_module(module)
    except (ImportError, OSError) as exc:
        raise FieldLabError(
            package + " not installed or platform wheel unavailable; install the offline FieldLab pack"
        ) from None


def _base_result(reader: str, fmt: str) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "execution_scope": "local_process_only",
        "reader": reader,
        "format": fmt,
        "patient_data_uploaded": False,
        "network_required": False,
        "clinical_interpretation": None,
        "clinical_promotion_allowed": False,
        "treatment_recommendations": False,
        "human_authority_final": True,
    }


def _bounded_file(path: Path, max_bytes: int) -> Path:
    # A symlink or Windows UNC path can redirect to uncontrolled storage/network.
    original = str(path)
    if original.startswith(("\\\\", "//")):
        raise FieldLabError("Network shares are not accepted by the offline adapter")
    if path.is_symlink() or not path.is_file():
        raise FieldLabError("Expected a regular, non-symlink local file")
    try:
        size = path.stat().st_size
    except OSError:
        raise FieldLabError("Unable to inspect local file metadata") from None
    if size < 1 or size > max_bytes:
        raise FieldLabError("Local source exceeds its format-specific byte bound")
    return path


def _finite_positive_number(value: Any) -> float | None:
    try:
        x = float(value)
        if math.isfinite(x) and 0 < x <= 10000:
            return x
    except (ValueError, TypeError, OverflowError):
        pass
    return None


def _inspect_dicom(path: Path, *, include_pixel_summary: bool) -> dict[str, Any]:
    _bounded_file(path, MAX_DICOM_FILE_BYTES)
    pydicom = _load("pydicom", "pydicom")
    np = _load("numpy", "numpy")
    try:
        ds = pydicom.dcmread(path, force=False, stop_before_pixels=not include_pixel_summary)
        if "PixelData" not in ds and include_pixel_summary:
            raise FieldLabError("No DICOM pixel array available for local inspection")
        def bounded_int(name: str, default: int | None = None) -> int | None:
            value = getattr(ds, name, None)
            if value is None:
                return default
            try:
                parsed = int(value)
            except (ValueError, TypeError, OverflowError):
                raise FieldLabError("Invalid DICOM dimension value") from None
            if not 1 <= parsed <= 4096:
                raise FieldLabError("Invalid or excessive DICOM dimensions")
            return parsed
        rows, cols = bounded_int("Rows"), bounded_int("Columns")
        if (rows is None) != (cols is None):
            raise FieldLabError("Incomplete image dimensions in DICOM source")
        frames = bounded_int("NumberOfFrames", 1 if rows is not None else None)
        channels = bounded_int("SamplesPerPixel")
        if rows is not None and cols is not None:
            if include_pixel_summary and (frames is None or channels is None):
                raise FieldLabError("Missing image dimensions required for pixel processing")
            if (frames is not None and frames > 64) or (channels is not None and channels > 4):
                raise FieldLabError("DICOM frame or channel count exceeds bound")
            if rows * cols * (frames or 1) * (channels or 1) > MAX_PIXEL_SAMPLES:
                raise FieldLabError("DICOM pixel count exceeds bounded local analysis limit")
        elif include_pixel_summary:
            raise FieldLabError("No image geometry available for pixel processing")
        modality = str(getattr(ds, "Modality", "") or "")
        if not re.fullmatch(r"[A-Z]{2,6}", modality):
            modality = "UNSPECIFIED"
        result = _base_result("pydicom", "DICOM Part 10")
        result.update({
            "image_modality": modality, "rows": rows, "columns": cols,
            "frames": frames, "samples_per_pixel": channels,
            "pixel_summary_computed": False,
            "patient_tags_exported": False,
            "source_identifiers_exported": False,
            "study_uid_exported": False,
            "pixel_decoder_status": "not_required" if not include_pixel_summary else "pending",
        })
        spacing = getattr(ds, "PixelSpacing", None)
        if spacing is not None and len(spacing) == 2:
            zooms = [_finite_positive_number(x) for x in spacing]
            if all(x is not None for x in zooms):
                result["pixel_spacing_reported_mm"] = zooms
        if include_pixel_summary:
            from pydicom.pixels import apply_modality_lut
            try:
                array = ds.pixel_array
                if int(array.size) > MAX_PIXEL_SAMPLES:
                    raise FieldLabError("Excessive decoded image dimensions")
                scaled = apply_modality_lut(array, ds)
                if not np.all(np.isfinite(scaled)):
                    raise FieldLabError("Decoded DICOM contains non-finite values")
                result["pixel_min"] = float(np.min(scaled))
                result["pixel_max"] = float(np.max(scaled))
                result["pixel_summary_computed"] = True
                result["pixel_decoder_status"] = "decoded_locally"
                result["pixel_scaling"] = (
                    "dicom_modality_lut"
                    if ("ModalityLUTSequence" in ds or "RescaleSlope" in ds or "RescaleIntercept" in ds)
                    else "none_reported"
                )
            except FieldLabError:
                raise
            except (RuntimeError, ValueError, OSError, NotImplementedError, AttributeError) as exc:
                raise FieldLabError(
                    "DICOM pixel decoder unavailable, incompatible or invalid; do not infer pixel values"
                ) from None
        return result
    except FieldLabError:
        raise
    except (ValueError, TypeError, OverflowError, OSError, AttributeError) as exc:
        raise FieldLabError("DICOM header malformed or inaccessible") from None


def _inspect_nifti(path: Path) -> dict[str, Any]:
    _bounded_file(path, MAX_SCIENCE_FILE_BYTES)
    nib = _load("nibabel", "nibabel")
    try:
        img = nib.load(str(path))
        shape = tuple(int(x) for x in img.shape)
        if not 2 <= len(shape) <= 5 or any(x < 1 or x > 4096 for x in shape):
            raise FieldLabError("Unsupported NIfTI voxel geometry")
        voxels = math.prod(shape)
        if voxels > 128_000_000:
            raise FieldLabError("NIfTI image dimensions exceed bounded local inspection")
        spacing = [_finite_positive_number(x) for x in img.header.get_zooms()[:3]]
        if any(x is None for x in spacing):
            raise FieldLabError("NIfTI voxel spacing missing or invalid")
        affine = img.affine
        if not bool(__import__("numpy").isfinite(affine).all()):
            raise FieldLabError("NIfTI affine contains nonfinite coordinates")
        result = _base_result("nibabel", "NIfTI")
        result.update({
            "shape": list(shape), "voxel_spacing": spacing,
            "voxel_data_loaded": False, "spatial_reference_review_required": True,
            "source_identifiers_exported": False,
            "segmentation_or_diagnosis_computed": False,
        })
        return result
    except FieldLabError:
        raise
    except (ValueError, TypeError, OSError, OverflowError, IndexError) as exc:
        raise FieldLabError("NIfTI header malformed or unsupported") from None


def _inspect_sequences(path: Path, *, kind: str) -> dict[str, Any]:
    _bounded_file(path, MAX_SEQUENCE_FILE_BYTES)
    seq_io = _load("Bio.SeqIO", "Biopython")
    records, total_bases, gc, min_length, max_length = 0, 0, 0, None, 0
    min_quality: int | None = None
    try:
        with path.open("r", encoding="utf-8") as handle:
            for record in seq_io.parse(handle, kind):
                records += 1
                if records > MAX_SEQUENCE_RECORDS:
                    raise FieldLabError("Sequence record count exceeds bounded local analysis")
                seq = str(record.seq).upper()
                if not seq or any(base not in _DNA for base in seq):
                    raise FieldLabError("Unsupported sequence alphabet; no DNA interpretation performed")
                total_bases += len(seq)
                gc += seq.count("G") + seq.count("C")
                min_length = len(seq) if min_length is None else min(min_length, len(seq))
                max_length = max(max_length, len(seq))
                if kind == "fastq":
                    quality = record.letter_annotations.get("phred_quality")
                    if not quality or len(quality) != len(seq):
                        raise FieldLabError("FASTQ quality field missing or malformed")
                    min_quality = min(quality) if min_quality is None else min(min_quality, min(quality))
        if records == 0:
            raise FieldLabError("No complete sequence records found")
        result = _base_result("Bio.SeqIO", kind)
        result.update({
            "records": records, "total_bases": total_bases,
            "min_length": min_length, "max_length": max_length,
            "gc_fraction": round(gc / total_bases, 6),
            "sequence_data_released": False, "source_sequence_ids_exported": False,
            "genome_reference_verified": False,
            "gene_editing_prediction_executed": False,
        })
        if kind == "fastq":
            result["min_quality"] = min_quality
            result["quality_encoding"] = "phred+33 as parsed by Biopython"
        return result
    except FieldLabError:
        raise
    except (ValueError, UnicodeError, OSError, KeyError, TypeError, IndexError) as exc:
        raise FieldLabError("FASTA/FASTQ reader rejected an invalid or truncated input") from None


def _inspect_lab_csv(path: Path) -> dict[str, Any]:
    _bounded_file(path, MAX_LOCAL_LAB_BYTES)
    normalized = []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = csv.DictReader(handle, strict=True)
            if rows.fieldnames is None or set(rows.fieldnames) != {"code", "value", "unit"}:
                raise FieldLabError(
                    "Local lab CSV accepts only code,value,unit; patient identifiers and free-text columns rejected"
                )
            for row in rows:
                if len(normalized) >= MAX_LAB_RECORDS or None in row:
                    raise FieldLabError("Lab CSV exceeds record or schema bounds")
                code = row.get("code")
                unit = row.get("unit")
                try:
                    value = float(row.get("value"))
                except (ValueError, TypeError, OverflowError):
                    raise FieldLabError("Lab value must be a finite number") from None
                if not (isinstance(code, str) and _VALID_LAB_CODE.fullmatch(code)
                        and isinstance(unit, str) and _VALID_LAB_UNIT.fullmatch(unit)
                        and math.isfinite(value) and abs(value) < 1e30):
                    raise FieldLabError("Invalid local lab code, unit or numeric value")
                normalized.append({"code": code, "value": value, "unit": unit,
                                   "loinc_code_verified": False, "reference_interval_verified": False})
        result = _base_result("Python CSV", "lab_csv")
        result.update({"record_count": len(normalized), "results": normalized,
                       "local_private_data_may_be_present": True})
        return result
    except FieldLabError:
        raise
    except (UnicodeError, csv.Error, OSError) as exc:
        raise FieldLabError("Lab CSV reader rejected a malformed or unreadable file") from None


def molecular_descriptors(smiles: str) -> dict[str, Any]:
    """RDKit structural descriptors; not docking, affinity, toxicity or efficacy."""
    if not isinstance(smiles, str) or not _VALID_SMILES.fullmatch(smiles):
        raise FieldLabError("Molecule must be a bounded, valid public research SMILES")
    _load("rdkit", "RDKit")
    chem = _load("rdkit.Chem", "RDKit")
    rd_base = _load("rdkit.rdBase", "RDKit")
    desc = _load("rdkit.Chem.Descriptors", "RDKit")
    lip = _load("rdkit.Chem.Lipinski", "RDKit")
    try:
        with rd_base.BlockLogs():
            mol = chem.MolFromSmiles(smiles, sanitize=True)
        if mol is None or mol.GetNumAtoms() > 256:
            raise FieldLabError("RDKit structure invalid or molecule exceeds atom cap")
        result = _base_result("RDKit", "SMILES")
        result.update({
            "source_library": "RDKit",
            "atom_count": int(mol.GetNumAtoms()),
            "molecular_weight": round(float(desc.MolWt(mol)), 5),
            "logp_fragment_model": round(float(desc.MolLogP(mol)), 5),
            "hydrogen_bond_donors": int(lip.NumHDonors(mol)),
            "hydrogen_bond_acceptors": int(lip.NumHAcceptors(mol)),
            "rotatable_bonds": int(lip.NumRotatableBonds(mol)),
            "tpsa_angstrom_squared": round(float(desc.TPSA(mol)), 5),
            "smiles_echoed": False, "binding_prediction_executed": False,
            "drug_efficacy_inferred": False, "toxicity_inferred": False,
            "assay_validation_executed": False,
        })
        return result
    except FieldLabError:
        raise
    except (ValueError, RuntimeError, OverflowError, TypeError, AttributeError) as exc:
        raise FieldLabError("RDKit could not sanitize or calculate bounded molecular descriptors") from None


def inspect_local_file(
    path: str | Path,
    *,
    private_local: bool = False,
    include_pixel_summary: bool = False,
) -> dict[str, Any]:
    """Never call an HTTP transport, log the path, or return original patient IDs."""
    if private_local is not True:
        raise FieldLabError("The explicitly private local-file flag is required")
    if not isinstance(path, (str, Path)):
        raise FieldLabError("Expected a local path")
    path = Path(path)
    if path.name.lower().endswith((".nii.gz", ".nii")):
        if include_pixel_summary:
            raise FieldLabError("NIfTI voxel metrics are not implemented")
        return _inspect_nifti(path)
    suffix = path.suffix.lower()
    if suffix in (".dcm", ".dicom"):
        return _inspect_dicom(path, include_pixel_summary=include_pixel_summary)
    if include_pixel_summary:
        raise FieldLabError("Pixel summaries are only available for bounded DICOM Part 10")
    if suffix in (".fa", ".fasta", ".fna"):
        return _inspect_sequences(path, kind="fasta")
    if suffix in (".fastq", ".fq"):
        return _inspect_sequences(path, kind="fastq")
    if suffix == ".csv":
        return _inspect_lab_csv(path)
    raise FieldLabError("File extension is not implemented by the offline adapter")


def runtime_capabilities() -> dict[str, Any]:
    """Inspect *actual imported modules*, not catalog membership."""
    from importlib import metadata
    configured = (
        ("RDKit", "rdkit", "rdkit"),
        ("Biopython", "Bio", "biopython"),
        ("pydicom", "pydicom", "pydicom"),
        ("nibabel", "nibabel", "nibabel"),
    )
    libraries = {}
    for name, module, distribution in configured:
        try:
            importlib.import_module(module)
            version = metadata.version(distribution)
            libraries[name] = {"loaded": True, "version": version, "source": "actual_local_import"}
        except (ImportError, OSError, metadata.PackageNotFoundError):
            libraries[name] = {"loaded": False, "version": None, "source": "not_installed_or_unloadable"}
    return {
        "schema_version": "1.0",
        "execution": "offline_local_cli",
        "network_required": False,
        "patient_data_uploaded": False,
        "clinical_validation_established": False,
        "no_patient_data_egress": "no HTTP or network calls implemented in these functions",
        "no_imaging_diagnosis": True,
        "molecular_binding_prediction": False,
        "quantum_hardware": False,
        "libraries": libraries,
    }
