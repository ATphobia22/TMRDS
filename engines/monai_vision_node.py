"""Inactive medical-imaging adapter.

No medical image is read and no inference is performed. This explicit
placeholder must never emit invented dimensions, lesions or confidence values.
Real medical-image processing needs its own intended-use and safety review.
"""
from __future__ import annotations

from typing import Any


class MONAIVisionNode:
    """Research imaging integration point, not an operational imaging model."""

    def __init__(self) -> None:
        self.device = "NOT_CONFIGURED"

    def load_3d_volume(self, dicom_path: str) -> dict[str, Any]:
        """Report unavailable imaging support without opening or echoing the path."""
        if not isinstance(dicom_path, str) or not dicom_path.strip():
            raise ValueError("dicom_path must be a non-empty string")
        return {
            "status": "NOT_CONFIGURED",
            "image_ingested": False,
            "dimensions": None,
            "spacing_mm": None,
            "device": self.device,
            "research_advisory": True,
            "reason": "Medical-image ingestion is not configured or validated.",
        }

    def run_diffusion_denoise_and_segment(
        self, volume_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Never convert caller-supplied metadata into a fictional lesion result."""
        if not isinstance(volume_data, dict):
            raise TypeError("volume_data must be a dict")
        return {
            "status": "NOT_CONFIGURED",
            "segmentation_performed": False,
            "detected_anomalies": None,
            "anomaly_confidence_plddt": None,
            "finding": None,
            "research_advisory": True,
            "human_review_required": True,
            "reason": "No validated imaging model or inference pipeline is configured.",
        }
