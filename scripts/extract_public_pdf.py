"""Extract a public PDF locally, preserving page numbers and source checksum."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engines.public_pdf_extract import extract_public_pdf

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--public-document', action='store_true')
    parser.add_argument('--max-pages', type=int, default=30)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = extract_public_pdf(args.input, public_document=args.public_document, max_pages=args.max_pages)
    with args.output.open('x') as target:
        json.dump(report, target, indent=2)
