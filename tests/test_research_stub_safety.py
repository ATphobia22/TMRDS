"""Synthetic safety regressions for intentionally unconfigured research adapters."""
from __future__ import annotations

import pytest

from engines.monai_vision_node import MONAIVisionNode
from engines.precision_medicine_engine import PrecisionMedicineEngine


def test_imaging_loader_does_not_fabricate_volume_or_echo_path() -> None:
    result = MONAIVisionNode().load_3d_volume("/synthetic/subject-123/scan.dcm")
    assert result["status"] == "NOT_CONFIGURED"
    assert result["image_ingested"] is False
    assert result["dimensions"] is None
    assert "subject-123" not in str(result)


def test_imaging_inference_does_not_fabricate_lesions_or_confidence() -> None:
    result = MONAIVisionNode().run_diffusion_denoise_and_segment(
        {"detected_anomalies": 9, "finding": "synthetic claim", "status": "VOLUME_LOADED"}
    )
    assert result["segmentation_performed"] is False
    assert result["status"] == "NOT_CONFIGURED"
    assert result["detected_anomalies"] is None
    assert result["anomaly_confidence_plddt"] is None
    assert result["finding"] is None


@pytest.mark.parametrize("variant_id", ["rs7412", "RS429358", "BRAF_V600E", "unknown"])
def test_patent_stub_never_confirms_freedom_to_operate(variant_id: str) -> None:
    result = PrecisionMedicineEngine().screen_patent_freedom_to_operate(variant_id)
    assert result["status"] == "NOT_EVALUATED"
    assert result["patent_status"] == "NOT_EVALUATED"
    assert result["freedom_to_operate_confirmed"] is False
    assert result["repurposed_compound"] is None
    assert result["human_review_required"] is True


def test_variant_parser_returns_fields_without_drug_inference() -> None:
    rows = ["##fileformat=VCFv4.2", "#CHROM\tPOS\tID\tREF\tALT",
            "1\t123\trs7412\tA\tG"]
    result = PrecisionMedicineEngine().digest_variant_payload(rows)
    assert result == [{
        "chromosome": "1", "position": "123", "variant_id": "rs7412",
        "ref": "A", "alt": "G",
    }]
