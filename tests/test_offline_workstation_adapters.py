"""No-network tests for *working* local TMRDS open-source biomedical integrations.

Package-specific tests run in the offline adapter CI job with pinned wheels.
The core CI exercises its standard-library FHIR/CSV/authorization boundary.
"""
from __future__ import annotations

import importlib.metadata
import json
import socket
from pathlib import Path

import pytest

from engines.offline_workstation_adapters import (
    OfflineWorkstationError, capability_report, inspect_local_file, molecule_descriptors,
)
from scripts.qrce_offline_workstation import _html_report, main


def pinned(name: str, version: str):
    try:
        actual = importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        pytest.skip("Optional " + name + " not installed in core test profile")
    if actual != version:
        pytest.skip(name + " version differs from tested offline pin")


def test_capability_report_is_not_a_catalog_and_never_claims_clinical_validation():
    data = capability_report()
    assert set(data["components"]) == {"dicom", "sequences", "chemistry", "papers"}
    assert data["network_required_for_analysis"] is False
    assert data["clinical_validation_completed"] is False
    for record in data["components"].values():
        assert record["enabled"] == (record["installed_version"] == record["expected_version"])
        assert record["tested_with_actual_local_file"] is False


def test_local_authorization_required_and_unsupported_files_fail_closed(tmp_path: Path):
    p = tmp_path / "secret-patient.csv"
    p.write_text("code,value,unit\n718-7,12,g/dL\n")
    with pytest.raises(OfflineWorkstationError, match="authorization"):
        inspect_local_file(p)
    with pytest.raises(OfflineWorkstationError, match="missing"):
        inspect_local_file(tmp_path / "notthere.exe", authorized_local=True)
    other = tmp_path / "other.exe"
    other.write_bytes(b"MZ")
    with pytest.raises(OfflineWorkstationError, match="reader"):
        inspect_local_file(other, authorized_local=True)
    link = tmp_path / "link.csv"
    try:
        link.symlink_to(p)
    except OSError:
        pytest.skip("Symlinks not supported on this filesystem")
    with pytest.raises(OfflineWorkstationError, match="unsafe"):
        inspect_local_file(link, authorized_local=True)


def test_fhir_patient_data_stays_local_and_lab_counts_are_real(tmp_path: Path):
    p = tmp_path / "clinical.json"
    data = {"resourceType": "Bundle", "type": "collection", "entry": [
        {"resource": {"resourceType": "Observation", "subject": {"reference": "Patient/Alice"},
                      "code": {"coding": [{"system": "http://loinc.org", "code": "718-7"}]},
                      "valueQuantity": {"value": 12.3, "unit": "g/dL"}}},
        {"resource": {"resourceType": "Observation", "patient_name": "Alice",
                      "code": {"coding": [{"system": "http://loinc.org", "code": "777-3"}]},
                      "valueQuantity": {"value": 44, "unit": "10*9/L"}}},
    ]}
    p.write_text(json.dumps(data))
    out = inspect_local_file(p, authorized_local=True)
    assert out["observations"] == 2 and out["loinc_system_declared"] == 2
    assert out["units_supplied"] == 2
    assert out["values_returned"] is False
    assert out["diagnosis_generated"] is False
    assert out["file_sha256_included"] is False
    assert not any(token in json.dumps(out) for token in ("Alice", "12.3", "Patient/", "718-7", "777-3"))


def test_local_csv_with_name_does_not_export_name_measurement_or_identifiers(tmp_path: Path):
    p = tmp_path / "private-lab.tsv"
    p.write_text("patient_name\tcode\tvalue\tunit\nAlice\t718-7\t13.2\tg/dL\n")
    out = inspect_local_file(p, authorized_local=True)
    assert out["rows"] == out["measurement_rows"] == out["rows_with_units"] == 1
    assert "Alice" not in json.dumps(out) and "13.2" not in json.dumps(out)
    assert out["network_calls"] == 0


def test_no_remote_network_calls_even_with_fhir_data(tmp_path: Path, monkeypatch):
    p = tmp_path / "example.json"
    p.write_text(json.dumps({"resourceType": "Observation", "subject": {"reference": "Patient/789"},
                             "code": {"coding": []}, "valueQuantity": {"value": 12}}))
    def forbid(*args, **kwargs):
        raise AssertionError("Network invocation prohibited by offline contract")
    monkeypatch.setattr(socket.socket, "connect", forbid)
    out = inspect_local_file(p, authorized_local=True)
    assert out["network_calls"] == 0 and out["observations"] == 1


def test_biopython_real_fasta_and_fastq_parser(tmp_path: Path):
    pinned("biopython", "1.88")
    fasta = tmp_path / "private.fasta"
    fasta.write_text(">Patient/Alice\nACGTACGTNN\n")
    result = inspect_local_file(fasta, authorized_local=True)
    assert result["sequence_count"] == 1 and result["base_count"] == 10
    assert result["gc_fraction"] == 0.4
    assert "Patient/" not in json.dumps(result)
    fastq = tmp_path / "private.fastq"
    fastq.write_text("@patient-identifier\nACGT\n+\nIIII\n")
    q = inspect_local_file(fastq, authorized_local=True)
    assert q["sequence_count"] == 1 and q["base_calls_below_q20"] == 0
    assert "patient-identifier" not in json.dumps(q)


def test_rdkit_real_chemical_descriptor_and_sdf(tmp_path: Path):
    pinned("rdkit", "2026.9.2")
    data = molecule_descriptors("CCO")
    assert data["atom_count"] == 3
    assert data["molecular_weight"] == pytest.approx(46.069, abs=.02)
    assert data["therapeutic_efficacy_predicted"] is False
    assert data["binding_affinity_calculated"] is False
    with pytest.raises(OfflineWorkstationError):
        molecule_descriptors("C(C)(")
    from rdkit import Chem
    writer = Chem.SDWriter(str(tmp_path / "molecules.sdf"))
    writer.write(Chem.MolFromSmiles("CCO"))
    writer.write(Chem.MolFromSmiles("CC"))
    writer.close()
    out = inspect_local_file(tmp_path / "molecules.sdf", authorized_local=True)
    assert out["molecules"] == out["parsed_molecules"] == 2
    assert not out["binding_affinity_calculated"]


def test_pydicom_real_synthetic_mr_pixels_no_patient_tags(tmp_path: Path):
    pinned("pydicom", "3.0.2")
    from scripts.imaging_synthetic_demo import generate
    directory = tmp_path / "synthetic"
    generate(directory)
    result = inspect_local_file(directory / "synthetic-mr.dcm",
                                authorized_local=True, pixel_qc=True)
    assert result["modality"] == "MR"
    assert result["rows"] == result["columns"] == 16
    assert result["pixel_count"] == 256
    assert result["pixel_qc_performed"] is True
    assert result["diagnosis_generated"] is False
    for blocked in ("SYNTHETIC^TMRDS", "PatientID", "StudyInstanceUID", "SOPInstanceUID"):
        assert blocked not in json.dumps(result)


def test_pypdf_real_local_document_parser_no_text_leak(tmp_path: Path):
    pinned("pypdf", "7.1.0")
    from pypdf import PdfWriter
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=300)
    path = tmp_path / "private.pdf"
    with path.open("wb") as f:
        writer.write(f)
    out = inspect_local_file(path, authorized_local=True)
    assert out["pages"] == 1 and out["text_pages"] == 0
    assert out["ocr_performed"] is False
    assert out["scientific_claims_reviewed"] is False


def test_escaped_static_html_report_and_cli(tmp_path: Path, capsys):
    report = {"danger": "<img src='https://not-a-valid-clinical-site.invalid'>", "status": "local_only"}
    rendered = _html_report(report)
    assert "<img" not in rendered
    assert "&lt;img" in rendered
    assert "default-src 'none'" in rendered
    assert "<script" not in rendered
    p = tmp_path / "fresh.html"
    assert main(["cube", "--html-report", str(p)]) == 0
    assert p.is_file()
    assert "diagnosis" in p.read_text()
    assert main(["cube", "--html-report", str(p)]) == 2
    assert main(["inspect", str(tmp_path / "sensitive.json")]) == 2
    assert "authorization" in capsys.readouterr().err
