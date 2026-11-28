#!/usr/bin/env python3
"""Run the offline two-qubit VQE validation benchmark and print its receipt."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engines.quantum_statevector_vqe import run_bell_hamiltonian_vqe


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--grid-points", type=int, default=721)
    args = parser.parse_args()
    result = run_bell_hamiltonian_vqe(grid_points=args.grid_points)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
