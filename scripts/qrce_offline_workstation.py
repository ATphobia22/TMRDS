#!/usr/bin/env python3
"""Local-only TMRDS workstation: inspect authorized files, molecules or cube math.

No web service, no patient uploads, no hidden model downloads. The generated
reports omit raw identifiers, text, lab values and genetic sequences by design.
"""
from __future__ import annotations

import argparse
import html
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engines.offline_workstation_adapters import (
    OfflineWorkstationError, capability_report, inspect_local_file, molecule_descriptors,
)
from engines.cube_grover_research import simulate_grover_research_plan


def _write_new(path: Path, text: str) -> None:
    """Never silently replace an earlier clinical-data-derived local report."""
    try:
        fd = os.open(path, os.O_CREAT | os.O_WRONLY | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    except OSError:
        raise OfflineWorkstationError("Unable to securely create new local report") from None


def _html_report(report: dict) -> str:
    rows = []
    for key, value in sorted(report.items()):
        if isinstance(value, (dict, list)):
            readable = json.dumps(value, sort_keys=True, ensure_ascii=True)
        else:
            readable = str(value)
        rows.append("<tr><th>" + html.escape(key) + "</th><td>" +
                    html.escape(readable) + "</td></tr>")
    return (
        "<!doctype html><html lang='en'><meta charset='utf-8'>"
        "<meta http-equiv='Content-Security-Policy' content=\"default-src 'none'; "
        "style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'\">"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        "<title>TMRDS Offline Research QC</title>"
        "<style>body{font:16px system-ui;max-width:860px;margin:auto;padding:2rem;"
        "background:#101c29;color:#edf5fc}table{border-collapse:collapse;width:100%}"
        "td,th{border-bottom:1px solid #3b4a57;padding:.75rem;vertical-align:top;text-align:left;"
        "overflow-wrap:anywhere}th{width:35%}small{color:#b3c4d1}</style>"
        "<h1>Offline workstation: file quality summary</h1>"
        "<p>Local mathematical and structural checks only. Not diagnosis, drug recommendation,"
        " medical imaging interpretation, or clinical decision support.</p>"
        "<table>" + "".join(rows) + "</table>"
        "<p><small>Offline report has no network scripts, no external fonts, no automatic upload."
        " Do not share case-derived reports without appropriate authorization.</small></p></html>"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor", help="Check versions actually installed (not catalog membership)")
    inspection = sub.add_parser("inspect", help="Inspect an authorized local biomedical file")
    inspection.add_argument("file", type=Path, help="Local DICOM/FASTA/FASTQ/SDF/PDF/FHIR/CSV/TSV")
    inspection.add_argument("--authorized-local", action="store_true", help="Assert authorization to process this local file")
    inspection.add_argument("--pixel-qc", action="store_true", help="Numerical DICOM pixel QC; NOT radiology interpretation")
    inspection.add_argument("--include-sha256", action="store_true", help="Include potentially sensitive exact-file digest")
    chemical = sub.add_parser("molecule", help="Calculate actual RDKit descriptors; no drug efficacy inferred")
    chemical.add_argument("--smiles", required=True, help="Research chemical SMILES, not patient information")
    cube = sub.add_parser("cube", help="Exact classical simulation of six-qubit Grover plan search")
    cube.add_argument("--required", default="disease_phenotype,target_pathway,trials_labels")
    cube.add_argument("--max-planes", type=int, default=4)
    for command in (inspection, chemical, cube):
        command.add_argument("--html-report", type=Path, help="Create a new local read-only HTML summary")
    args = parser.parse_args(argv)
    try:
        if args.command == "doctor":
            report = capability_report()
        elif args.command == "inspect":
            report = inspect_local_file(args.file, authorized_local=args.authorized_local,
                                        pixel_qc=args.pixel_qc, include_sha256=args.include_sha256)
        elif args.command == "molecule":
            report = molecule_descriptors(args.smiles)
        else:
            report = simulate_grover_research_plan(
                required=tuple(item.strip() for item in args.required.split(",")),
                max_planes=args.max_planes)
        if getattr(args, "html_report", None):
            _write_new(args.html_report, _html_report(report))
        print(json.dumps(report, sort_keys=True, indent=2))
        return 0
    except (OfflineWorkstationError, ValueError) as error:
        # Error contains only controlled policy strings, never file names or PHI.
        print("TMRDS local operation refused: " + str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
