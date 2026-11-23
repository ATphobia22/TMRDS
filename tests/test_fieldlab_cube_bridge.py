"""Independent offline tests: local data -> Rubik review-plan routing, no raw PHI."""
import json
import pytest

from engines.fieldlab_cube_bridge import create_offline_review_plan


@pytest.mark.parametrize(("reader","format_name","plane"), [
    ("pydicom","DICOM Part 10","disease_phenotype"),
    ("nibabel","NIfTI","disease_phenotype"),
    ("Bio.SeqIO","fasta","target_pathway"),
    ("Bio.SeqIO","fastq","target_pathway"),
    ("Python CSV","lab_csv","disease_phenotype"),
    ("RDKit","SMILES","molecule"),
])
def test_local_readers_route_into_real_grover_research_plan_without_medical_inference(reader, format_name, plane):
    report = {
        "schema_version":"1.0","execution_scope":"local_process_only",
        "reader":reader,"format":format_name,
        "network_required":False,"patient_data_uploaded":False,
        "clinical_promotion_allowed":False,
        "source_patient_name":"VERY_PRIVATE_PATIENT",
        "results":[{"code":"718-7","value":13.1,"unit":"g/dL"}],
    }
    output = create_offline_review_plan(report)
    assert output["queued_review_plane"] == plane
    assert output["review_status"] == "unreviewed_local_file_type_routing_only"
    assert output["raw_patient_records_exported"] is False
    assert output["external_research_queried"] is False
    assert output["clinical_promotion_allowed"] is False
    assert output["grover"]["backend"] == "classical_exact_statevector_simulator"
    assert output["grover"]["execution"]["quantum_hardware_used"] is False
    assert output["grover"]["governance"]["cure_claim"] is False
    assert output["grover"]["oracle"]["required"] == [plane]
    assert "VERY_PRIVATE_PATIENT" not in json.dumps(output)
    assert "718-7" not in json.dumps(output)
    assert "13.1" not in json.dumps(output)


def test_private_or_untrusted_source_reports_cannot_create_fake_cube_evidence():
    base={"schema_version":"1.0","execution_scope":"local_process_only",
          "reader":"pydicom","format":"DICOM Part 10",
          "patient_data_uploaded":False,"network_required":False,"clinical_promotion_allowed":False}
    for bad in (
        {**base,"patient_data_uploaded":True},
        {**base,"clinical_promotion_allowed":True},
        {**base,"execution_scope":"public_cloud"},
        {**base,"reader":"unknown"},
        {**base,"format":"unknown"},
        {"schema_version":"0.1",**{k:v for k,v in base.items() if k!="schema_version"}},
    ):
        with pytest.raises(ValueError):
            create_offline_review_plan(bad)
