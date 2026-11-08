"""
MedicalNet 3D-ResNet Backbone Adapter for TMRDS.
Local 3D ResNet (Med3D) research architecture for volumetric CT/MRI.
Source: Tencent/MedicalNet (MIT) — arXiv:1904.00625
Weights: reviewed local bundle only; automatic pretrained downloads disabled.
"""
from __future__ import annotations

import logging
from pathlib import Path
from engines.model_bundle_review import load_reviewed_weights
from typing import Any, Dict, Optional

import torch
import torch.nn as nn

logger = logging.getLogger("TMRDS.MedicalNet")

# Construct MONAI architecture locally; all weights require explicit bundle review.
try:
    from monai.networks.nets import resnet10, resnet18, resnet34, resnet50, resnet101, resnet152, resnet200
    MONAI_AVAILABLE = True
except ImportError:
    MONAI_AVAILABLE = False



class MedicalNetBackbone:
    """Research-only local architecture with explicit reviewed weight loading.

    No automatic downloads. Randomly initialized networks are not pretrained.
    """

    SUPPORTED_DEPTHS = (10, 18, 34, 50, 101, 152, 200)

    def __init__(
        self,
        depth: int = 50,
        pretrained: bool = False,
        device: str = "cpu",
        spatial_dims: int = 3,
        in_channels: int = 1,
        num_classes: int = 0,
        bundle_directory: Optional[str] = None,
        bundle_manifest: Optional[dict] = None,
    ) -> None:
        if depth not in self.SUPPORTED_DEPTHS:
            raise ValueError(f"depth must be one of {self.SUPPORTED_DEPTHS}")
        if pretrained and (bundle_directory is None or bundle_manifest is None):
            raise ValueError("pretrained weights require a reviewed local bundle")
        if not MONAI_AVAILABLE:
            raise RuntimeError("MONAI is required; no substitute backbone is provided")
        self.depth = depth
        self.device = torch.device(device)
        self.pretrained = pretrained
        self.spatial_dims = spatial_dims
        self.in_channels = in_channels
        self.num_classes = num_classes
        self.model: Optional[nn.Module] = None
        self.weights_loaded = False
        self._build()
        if pretrained:
            if not self.load_weights_manual(bundle_directory=bundle_directory, manifest=bundle_manifest):
                raise ValueError("reviewed pretrained weight load failed")

    def _build(self) -> None:
        if MONAI_AVAILABLE:
            factory = {
                10: resnet10, 18: resnet18, 34: resnet34, 50: resnet50,
                101: resnet101, 152: resnet152, 200: resnet200,
            }[self.depth]
            self.model = factory(
                pretrained=False,
                spatial_dims=self.spatial_dims,
                n_input_channels=self.in_channels,
                num_classes=self.num_classes if self.num_classes > 0 else 400,
            )
            self.model = self.model.to(self.device)
            self.model.eval()
            return

    def load_weights_manual(self, local_path: Optional[str] = None, *,
                            bundle_directory: Optional[str] = None, manifest: Optional[dict] = None) -> bool:
        """Load an explicitly reviewed tensor state dictionary; never download."""
        if bundle_directory is None or manifest is None:
            raise ValueError("a reviewed bundle directory and manifest are required")
        if local_path is not None and Path(local_path).resolve() != (Path(bundle_directory) / manifest["weights"]).resolve():
            raise ValueError("weight path must match reviewed manifest")
        state = load_reviewed_weights(Path(bundle_directory), manifest)
        cleaned = {k.removeprefix("module."): v for k, v in state.items()}
        if self.model is None:
            raise RuntimeError("MONAI architecture is unavailable")
        self.model.load_state_dict(cleaned, strict=True)
        self.weights_loaded = True
        self.pretrained = True
        logger.info("Reviewed local MedicalNet weights loaded for research")
        return True

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
            "source": "local reviewed bundle" if self.weights_loaded else "random initialization",
            "hf_repo": f"TencentMedicalNet/MedicalNet-Resnet{self.depth}",
            "status": "RESEARCH_WEIGHTS_LOADED" if self.weights_loaded else "UNTRAINED_RESEARCH",
            "citation": "Chen et al., Med3D, arXiv:1904.00625",
        }
