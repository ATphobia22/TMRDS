"""Evaluate offline binary-mask overlap using MONAI; no model or scan ingestion."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engines.research_mask_metrics import binary_mask_dice

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference', type=Path)
    parser.add_argument('candidate', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = binary_mask_dice(np.load(args.reference, mmap_mode='r', allow_pickle=False), np.load(args.candidate, mmap_mode='r', allow_pickle=False))
    def checksum(path):
        digest = hashlib.sha256()
        with path.open('rb') as source:
            for block in iter(lambda: source.read(1024*1024), b''):
                digest.update(block)
        return digest.hexdigest()
    result['input_sha256'] = {'reference':checksum(args.reference), 'candidate':checksum(args.candidate)}
    with args.output.open('x') as target:
        json.dump(result, target, indent=2)
