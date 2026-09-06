"""
MedicalNet 3D-ResNet Backbone Adapter for TMRDS.
Pre-trained 3D ResNet (Med3D) for transfer learning on volumetric CT/MRI.
Source: Tencent/MedicalNet (MIT) — arXiv:1904.00625
Weights: Hugging Face TencentMedicalNet / MONAI get_pretrained_resnet_medicalnet
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import torch
import torch.nn as nn

logger = logging.getLogger("TMRDS.MedicalNet")

# Preferred load path: MONAI (already wires HF download)
try:
    from monai.networks.nets import resnet10, resnet18, resnet34, resnet50, resnet101, resnet152, resnet200
    from monai.networks.nets.resnet import get_pretrained_resnet_medicalnet
    MONAI_AVAILABLE = True
except ImportError:
    MONAI_AVAILABLE = False

try:
    from huggingface_hub import hf_hub_download
    HF_AVAILABLE = True
except ImportError:
    HF_AVAILABLE = False


class MedicalNetBackbone:
    """
    Production 3D-ResNet backbone with real MedicalNet weights.

    Weight download (automatic via MONAI or huggingface_hub):
        repo = f"TencentMedicalNet/MedicalNet-Resnet{depth}"
        filename = f"resnet_{depth}_23dataset.pth"   # preferred (23-dataset)

    Manual download:
        huggingface-cli download TencentMedicalNet/MedicalNet-Resnet50 \\
            resnet_50_23dataset.pth --local-dir ./weights/medicalnet
    """

    SUPPORTED_DEPTHS = (10, 18, 34, 50, 101, 152, 200)

    def __init__(
        self,
        depth: int = 50,
        pretrained: bool = True,
        device: str = "cpu",
        spatial_dims: int = 3,
        in_channels: int = 1,
        num_classes: int = 0,
    ) -> None:
        if depth not in self.SUPPORTED_DEPTHS:
            raise ValueError(f"depth must be one of {self.SUPPORTED_DEPTHS}")
        self.depth = depth
        self.device = torch.device(device)
        self.pretrained = pretrained
        self.spatial_dims = spatial_dims
        self.in_channels = in_channels
        self.num_classes = num_classes
        self.model: Optional[nn.Module] = None
        self.weights_loaded = False
        self._build()

    def _build(self) -> None:
        if MONAI_AVAILABLE:
            factory = {
                10: resnet10, 18: resnet18, 34: resnet34, 50: resnet50,
                101: resnet101, 152: resnet152, 200: resnet200,
            }[self.depth]
            self.model = factory(
                pretrained=self.pretrained,
                spatial_dims=self.spatial_dims,
                n_input_channels=self.in_channels,
                num_classes=self.num_classes if self.num_classes > 0 else 400,
            )
            if self.pretrained:
                self.weights_loaded = True
                logger.info("MedicalNet weights loaded via MONAI (HF TencentMedicalNet)")
            self.model = self.model.to(self.device)
            self.model.eval()
            return

        logger.warning("MONAI not available — using feature-extractor stub")
        self.model = nn.Sequential(
            nn.Conv3d(self.in_channels, 64, kernel_size=7, stride=2, padding=3, bias=False),
            nn.BatchNorm3d(64),
            nn.ReLU(inplace=True),
            nn.AdaptiveAvgPool3d((1, 1, 1)),
            nn.Flatten(),
            nn.Linear(64, 512),
        ).to(self.device)
        self.model.eval()

    def load_weights_manual(self, local_path: Optional[str] = None) -> bool:
        """Explicit weight load for offline / air-gapped environments."""
        if not HF_AVAILABLE and local_path is None:
            logger.error("huggingface_hub required for remote download")
            return False
        try:
            if local_path is None:
                repo_id = f"TencentMedicalNet/MedicalNet-Resnet{self.depth}"
                filename = f"resnet_{self.depth}_23dataset.pth"
                local_path = hf_hub_download(repo_id=repo_id, filename=filename)
            state = torch.load(local_path, map_location=self.device, weights_only=True)
            cleaned = {k.replace("module.", ""): v for k, v in state.items()}
            if self.model is not None:
                self.model.load_state_dict(cleaned, strict=False)
                self.weights_loaded = True
                logger.info("MedicalNet weights loaded from %s", local_path)
                return True
        except Exception as exc:  # noqa: BLE001
            logger.error("Weight load failed: %s", exc)
        return False

    def extract_features(self, volume: torch.Tensor) -> torch.Tensor:
        """volume: (B, C, D, H, W) → feature vector or logits"""
        if volume.dim() != 5:
            raise ValueError("Expected 5-D tensor (B, C, D, H, W)")
        with torch.no_grad():
            return self.model(volume.to(self.device))

    def transfer_status(self) -> Dict[str, Any]:
        return {
            "backbone": f"MedicalNet-3D-ResNet{self.depth}",
            "pretrained": self.pretrained,
            "weights_loaded": self.weights_loaded,
            "source": "Tencent/MedicalNet via MONAI or HF",
            "hf_repo": f"TencentMedicalNet/MedicalNet-Resnet{self.depth}",
            "status": "READY" if self.weights_loaded or not self.pretrained else "STUB",
            "citation": "Chen et al., Med3D, arXiv:1904.00625",
        }
