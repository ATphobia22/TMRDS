import numpy as np
import pytest
pytest.importorskip('monai')
from engines.research_mask_metrics import binary_mask_dice


def test_actual_monai_overlap():
    ref = np.zeros((3,3,3), dtype=np.uint8)
    ref[0,0,0] = 1
    assert binary_mask_dice(ref, ref)['value'] == 1
    shifted = np.zeros_like(ref)
    shifted[2,2,2] = 1
    result = binary_mask_dice(ref, shifted)
    assert result['value'] == 0 and not result['inference_executed']
    assert binary_mask_dice(ref * 0, ref * 0)['value'] is None


@pytest.mark.parametrize('candidate', [np.ones((2,2)), np.full((3,3,3), 2), np.full((3,3,3), float('nan'))])
def test_invalid_masks_rejected(candidate):
    with pytest.raises(ValueError):
        binary_mask_dice(np.zeros((3,3,3)), candidate)
