"""Offline command-line inspector for explicitly synthetic biomedical test fixtures.

Example: python -m scripts.inspect_synthetic_research_fixture --synthetic-only samples/example.csv
Never pass real patient/genome/laboratory records to this command. No network use.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from engines.qrce_research_formats import (
    MAX_FILE_BYTES, SyntheticFormatError, inspect_synthetic_fixture,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Local synthetic-only research format inspector, no PHI.")
    parser.add_argument("--synthetic-only", action="store_true",
                        help="Attest that input contains only synthetic, non-personal research data")
    parser.add_argument("file", type=Path, help="Local fixture, never uploaded")
    args = parser.parse_args()
    if args.synthetic_only is not True:
        parser.error("--synthetic-only attestation required (real clinical files prohibited)")
    try:
        size = args.file.stat().st_size
        if size == 0 or size > MAX_FILE_BYTES:
            raise SyntheticFormatError("Synthetic fixture must be 1–262144 bytes")
        payload = args.file.read_bytes()
        result = inspect_synthetic_fixture(
            suffix=args.file.suffix.lower(), data=payload, explicitly_synthetic=True,
        )
    except (OSError, SyntheticFormatError) as exc:
        # Do not echo a filename, path or raw source content to logs.
        print("Synthetic research fixture rejected: " + type(exc).__name__, file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
