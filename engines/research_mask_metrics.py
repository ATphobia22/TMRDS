"""Optional offline MONAI mask evaluation. No scan ingestion or model inference."""
from __future__ import annotations
import numpy as np


def binary_mask_dice(reference: np.ndarray, candidate: np.ndarray) -> dict:
    if not isinstance(reference, np.ndarray) or not isinstance(candidate, np.ndarray):
        raise ValueError("masks must be NumPy arrays")
    if reference.shape != candidate.shape or reference.ndim != 3 or not 0 < reference.size <= 16777216:
        raise ValueError("supply matching non-empty 3D masks of at most 16 million voxels")
    for mask in (reference, candidate):
        if mask.dtype.kind not in 'buif' or not np.isfinite(mask).all() or not np.isin(mask, [0, 1]).all():
            raise ValueError("masks must contain finite binary labels only")
    import torch
    import monai
    from monai.metrics import DiceMetric
    ref = torch.from_numpy(np.array(reference, dtype=np.float32, order="C", copy=True))[None, None]
    pred = torch.from_numpy(np.array(candidate, dtype=np.float32, order="C", copy=True))[None, None]
    if reference.any() or candidate.any():
        value = float(DiceMetric(include_background=True, reduction='mean', ignore_empty=False)(pred, ref).item())
        status = 'computed'
    else:
        value, status = None, 'undefined_both_masks_empty'
    return {'metric': 'binary_foreground_dice', 'value': value, 'status': status,
            'shape': list(reference.shape), 'monai_version': monai.__version__,
            'torch_version': torch.__version__, 'device': 'cpu', 'inference_executed': False,
            'clinical_promotion_allowed': False,
            'limitations': ['Array shape does not validate physical spatial alignment.',
                            'Dice is overlap, not diagnostic confidence or treatment effectiveness.',
                            'Caller must independently verify spacing, orientation and registration.']}
