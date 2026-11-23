"""Real offline open-source parser integration; fixtures only, no hospital network."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from engines.fieldlab_local import (
    FieldLabError, inspect_local_file, molecular_descriptors, runtime_capabilities
)


def test_real_rdkit_molecule_descriptor_values_and_invalid_smiles():
    mol = molecular_descriptors("CCO")
    assert mol["source_library"] == "RDKit"
    assert 46.0 < mol["molecular_weight"] < 46.2
    assert mol["hydrogen_bond_donors"] == 1
    assert mol["hydrogen_bond_acceptors"] == 1
    assert mol["rotatable_bonds"] == 0
    assert mol["drug_efficacy_inferred"] is False
    assert mol["binding_prediction_executed"] is False
    assert "CCO" not in json.dumps(mol)
    with pytest.raises(FieldLabError):
        molecular_descriptors("C1C1C1C1(")
    with pytest.raises(FieldLabError):
        molecular_descriptors("X" * 600)


def test_biopython_fasta_and_fastq_are_really_decoded_without_identifiers(tmp_path):
    fasta = tmp_path / "synthetic.fa"
    fasta.write_text(">synthetic-sequence-PRIVATE\nACGTACGT\n>synthetic2\nNNNN\n")
    result = inspect_local_file(fasta, private_local=True)
    assert result["reader"] == "Bio.SeqIO"
    assert result["format"] == "fasta"
    assert result["records"] == 2
    assert result["min_length"] == 4 and result["max_length"] == 8
    assert result["total_bases"] == 12
    assert result["sequence_data_released"] is False
    assert "PRIVATE" not in json.dumps(result)
    fastq = tmp_path / "synthetic.fastq"
    fastq.write_text("@private-read\nACGT\n+\nIIII\n")
    fq = inspect_local_file(fastq, private_local=True)
    assert fq["format"] == "fastq"
    assert fq["records"] == 1
    assert fq["quality_encoding"] == "phred+33 as parsed by Biopython"
    assert fq["min_quality"] == 40


def test_pydicom_reads_real_dicom_headers_and_pixels_locally_without_phi(tmp_path):
    import pydicom
    from pydicom.dataset import Dataset, FileDataset, FileMetaDataset
    from pydicom.uid import ExplicitVRLittleEndian, SecondaryCaptureImageStorage, generate_uid

    file_meta = FileMetaDataset()
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    file_meta.MediaStorageSOPClassUID = SecondaryCaptureImageStorage
    file_meta.MediaStorageSOPInstanceUID = generate_uid()
    file_meta.ImplementationClassUID = generate_uid()
    ds = FileDataset(str(tmp_path / "synthetic.dcm"), {}, file_meta=file_meta, preamble=b"\x00" * 128)
    ds.is_little_endian = True
    ds.is_implicit_VR = False
    ds.PatientName = "RESTRICTED^PERSON"
    ds.PatientID = "very-secret-patient-123"
    ds.StudyInstanceUID = generate_uid()
    ds.SeriesInstanceUID = generate_uid()
    ds.SOPClassUID = SecondaryCaptureImageStorage
    ds.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
    ds.Modality = "CT"
    ds.Rows = 2
    ds.Columns = 2
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = "MONOCHROME2"
    ds.BitsAllocated = 16
    ds.BitsStored = 16
    ds.HighBit = 15
    ds.PixelRepresentation = 1
    ds.RescaleSlope = "1"
    ds.RescaleIntercept = "-1024"
    ds.RescaleType = "HU"
    ds.PixelData = np.array([[1024, 1025], [800, 1600]], dtype="<i2").tobytes()
    ds.save_as(tmp_path / "synthetic.dcm", enforce_file_format=True)

    limited = inspect_local_file(tmp_path / "synthetic.dcm", private_local=True)
    assert limited["reader"] == "pydicom"
    assert limited["image_modality"] == "CT"
    assert limited["rows"] == 2 and limited["columns"] == 2
    assert limited["pixel_summary_computed"] is False
    assert "Patient" not in json.dumps(limited)
    assert "RESTRICTED" not in json.dumps(limited)
    assert "very-secret" not in json.dumps(limited)
    full = inspect_local_file(tmp_path / "synthetic.dcm", private_local=True, include_pixel_summary=True)
    assert full["pixel_summary_computed"] is True
    assert full["pixel_min"] == -224.0
    assert full["pixel_max"] == 576.0
    assert full["pixel_scaling"] == "dicom_modality_lut"
    assert full["image_modality"] == "CT"
    assert full["clinical_interpretation"] is None


def test_nibabel_inspects_offline_nifti_geometry_without_exposing_voxels(tmp_path):
    import nibabel as nib
    path = tmp_path / "private.nii.gz"
    image = nib.Nifti1Image(np.zeros((4, 5, 6), dtype=np.int16), np.diag([2.0, 2.5, 3.0, 1.0]))
    nib.save(image, str(path))
    result = inspect_local_file(path, private_local=True)
    assert result["reader"] == "nibabel"
    assert result["shape"] == [4, 5, 6]
    assert result["voxel_spacing"] == [2.0, 2.5, 3.0]
    assert result["voxel_data_loaded"] is False
    assert "private" not in json.dumps(result)


def test_private_local_is_required_and_no_sensitive_origin_information_leaks(tmp_path):
    path = tmp_path / "patient-name.csv"
    path.write_text("code,value,unit\n718-7,12,g/dL\n")
    with pytest.raises(FieldLabError, match="explicit"):
        inspect_local_file(path)
    result = inspect_local_file(path, private_local=True)
    assert result["reader"] == "Python CSV"
    assert result["record_count"] == 1
    assert result["results"][0]["code"] == "718-7"
    assert result["results"][0]["value"] == 12
    assert result["clinical_interpretation"] is None
    assert "patient-name" not in json.dumps(result)
    assert "patient_ref" not in json.dumps(result)
    with pytest.raises(FieldLabError):
        inspect_local_file(tmp_path / "missing.dcm", private_local=True)
    with pytest.raises(FieldLabError):
        inspect_local_file(path, private_local=True, include_pixel_summary=True)
    shortcut = tmp_path / "alias.csv"
    shortcut.symlink_to(path)
    with pytest.raises(FieldLabError):
        inspect_local_file(shortcut, private_local=True)


def test_readers_bound_records_bytes_and_cannot_make_medical_claims(tmp_path):
    bad = tmp_path / "test.docx"
    bad.write_bytes(b"not a real document")
    with pytest.raises(FieldLabError):
        inspect_local_file(bad, private_local=True)
    bad_seq = tmp_path / "sample.fa"
    bad_seq.write_text(">bad-sequence\nACGTX\n")
    with pytest.raises(FieldLabError):
        inspect_local_file(bad_seq, private_local=True)
    many = tmp_path / "many.fa"
    many.write_text("".join(">r%d\nA\n" % i for i in range(129)))
    with pytest.raises(FieldLabError):
        inspect_local_file(many, private_local=True)
    caps = runtime_capabilities()
    assert caps["network_required"] is False
    assert caps["patient_data_uploaded"] is False
    assert caps["clinical_validation_established"] is False
    assert caps["libraries"]["RDKit"]["loaded"] is True
    assert caps["libraries"]["Biopython"]["loaded"] is True
    assert caps["libraries"]["pydicom"]["loaded"] is True
    assert caps["libraries"]["nibabel"]["loaded"] is True
