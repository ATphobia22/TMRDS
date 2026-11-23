"""TMRDS FieldLab: no-server, no-network local research workstation.

No patient data is transmitted. The explicit --private-local switch acknowledges
that file data remains under the local machine operator's responsibility.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main(argv: list[str] | None = None) -> int:
    from engines.fieldlab_local import (
        FieldLabError, inspect_local_file, molecular_descriptors,
        runtime_capabilities,
    )

    parser = argparse.ArgumentParser(
        description="Offline source inspection using real open-source research libraries; NOT diagnostic software."
    )
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("status", help="Actually import local libraries and report versions")
    inspect = sub.add_parser("inspect", help="Inspect a local DICOM/NIfTI/lab CSV/FASTA/FASTQ file")
    inspect.add_argument("file", type=Path)
    inspect.add_argument(
        "--private-local", action="store_true",
        help="Required explicit approval: examine this file locally, without patient-data upload"
    )
    inspect.add_argument(
        "--pixel-summary", action="store_true",
        help="Decode bounded DICOM pixels and calculate local min/max after DICOM modality LUT"
    )
    molecule = sub.add_parser("molecule", help="Calculate RDKit 2D descriptors for a research SMILES")
    molecule.add_argument("--smiles", required=True, help="Public/non-patient SMILES only")
    args = parser.parse_args(argv)

    try:
        if args.action == "status":
            result = runtime_capabilities()
        elif args.action == "inspect":
            result = inspect_local_file(
                args.file,
                private_local=args.private_local,
                include_pixel_summary=args.pixel_summary,
            )
        else:
            result = molecular_descriptors(args.smiles)
    except FieldLabError:
        # Never write the filename, patient ID, source text or SMILES to logs.
        print(json.dumps({
            "status": "local_input_rejected_or_reader_unavailable",
            "clinical_interpretation": None,
            "source_data_uploaded": False,
        }), file=sys.stderr)
        return 2

    print(json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
