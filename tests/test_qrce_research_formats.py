"""Synthetic-only, no-network research-format inspector regression suite."""
import hashlib
import json
import pytest

from engines.qrce_research_formats import (
    SyntheticFormatError, format_capabilities, inspect_synthetic_fixture,
)


def inspect(ext, body, explicitly_synthetic=True):
    return inspect_synthetic_fixture(
        suffix=ext, data=body.encode("utf8") if isinstance(body, str) else body,
        explicitly_synthetic=explicitly_synthetic,
    )


def test_csv_and_tsv_keep_only_numeric_lab_facts_without_ranges_or_clinical_claims():
    csv = "code,value,unit\n718-7,13.4,g/dL\n"
    x = inspect(".csv", csv)
    assert x["status"] == "synthetic_fixture_inspected"
    assert x["record_count"] == 1
    assert x["records"][0]["code"] == "718-7"
    assert x["records"][0]["value"] == 13.4
    assert x["records"][0]["loinc_mapping_verified"] is False
    assert x["records"][0]["reference_range_available"] is False
    assert x["artifact_sha256"] == hashlib.sha256(csv.encode()).hexdigest()
    assert x["clinical_promotion_allowed"] is False
    assert inspect(".tsv", "code\tvalue\tunit\n777-3\t42\t10*9/L\n")["records"][0]["value"] == 42


def test_fhir_observation_accepts_synthetic_loinc_but_no_patient_ids_or_interpretation():
    observation = {
        "resourceType": "Observation",
        "code": {"coding": [{"system": "http://loinc.org", "code": "718-7"}]},
        "valueQuantity": {"value": 13.1, "unit": "g/dL"},
    }
    r = inspect(".json", json.dumps(observation))
    assert r["records"][0]["code"] == "718-7"
    assert r["coding_review_required"] is True
    bundle = {"resourceType": "Bundle", "type": "collection",
              "entry": [{"resource": observation}]}
    assert inspect(".json", json.dumps(bundle))["record_count"] == 1
    for prohibited in (
        dict(observation, subject={"reference": "Patient/123"}),
        dict(observation, patient_id="123"),
        dict(observation, name="Real User"),
    ):
        with pytest.raises(SyntheticFormatError):
            inspect(".json", json.dumps(prohibited))


def test_population_variant_vcf_rejects_genotype_columns():
    vcf = "##fileformat=VCFv4.3\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n1\t1234\trs777\tA\tG\t.\tPASS\t.\n"
    r = inspect(".vcf", vcf)
    assert r["record_count"] == 1
    assert r["records"][0]["position"] == 1234
    assert r["records"][0]["variant_id"] == "rs777"
    assert r["records"][0]["assembly"] == "UNSPECIFIED"
    with pytest.raises(SyntheticFormatError, match="Sample genotype"):
        inspect(".vcf", vcf.replace("\tFILTER\tINFO\n", "\tFILTER\tINFO\tFORMAT\tSAMPLE\n"))


def test_fasta_fastq_are_length_and_digest_only_not_sequence_export():
    r = inspect(".fasta", ">synthetic1\nACGTACGT\n>synthetic2\nNNNN\n")
    assert r["record_count"] == 2
    assert r["records"][0]["gc_fraction"] == 0.5
    assert "ACGTACGT" not in json.dumps(r)
    fastq = inspect(".fastq", "@synthetic1\nACGT\n+\nIIII\n")
    assert fastq["records"][0]["min_phred33"] == 40
    assert "ACGT" not in json.dumps(fastq)


def test_error_handling_rejects_real_data_binary_oversize_and_identifying_information():
    with pytest.raises(SyntheticFormatError, match="synthetic"):
        inspect(".csv", "code,value,unit\n718-7,12,g/dL\n", explicitly_synthetic=False)
    with pytest.raises(SyntheticFormatError, match="Personal identifiers"):
        inspect(".csv", "code,value,unit\n718-7,12,person@example.org\n")
    with pytest.raises(SyntheticFormatError, match="Patient identity"):
        inspect(".csv", "patient_id,code,value,unit\none,718-7,12,g/dL\n")
    with pytest.raises(SyntheticFormatError, match="256 KiB"):
        inspect(".json", b"x" * (262_144 + 1))
    with pytest.raises(SyntheticFormatError, match="Binary"):
        inspect(".csv", b"code,value,unit\x00")
    with pytest.raises(SyntheticFormatError):
        inspect(".xml", "<ClinicalDocument/>")
    for value in ("NaN", "Infinity", "1e999"):
        with pytest.raises(SyntheticFormatError):
            inspect(".csv", "code,value,unit\n718-7," + value + ",mg\n")


def test_format_contract_distinguishes_actual_synthetic_parser_from_optional_packages():
    caps = format_capabilities()
    states = {row["extension"]: row["state"] for row in caps}
    assert states[".vcf"] == "local_synthetic_text_reader"
    assert states[".json"] == "local_synthetic_text_reader"
    assert states[".bam"] == "external_reader_required"
    assert states[".dcm"] == "external_reader_required"
    assert states[".hl7"] == "external_reader_required"
    out = inspect(".dcm", b"not read")
    assert out["content_inspected"] is False
    assert out["clinical_promotion_allowed"] is False


def test_no_input_personal_data_in_json_namespaced_keys():
    for key in ("patientID", "birth_date", "fullName", "SubjectID", "medicalRecordNumber"):
        blob = json.dumps({"measurements": [
            {"code": "718-7", "value": 7, "unit": "g/dL", key: "SENSITIVE"}
        ]})
        with pytest.raises(SyntheticFormatError):
            inspect(".json", blob)
