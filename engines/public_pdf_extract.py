"""Offline, bounded public-PDF extraction; no OCR, remote upload or clinical inference."""
from pathlib import Path
from datetime import datetime, timezone
from importlib.metadata import version
import hashlib


def extract_public_pdf(path: Path, *, public_document: bool = False, max_pages: int = 30) -> dict:
    if public_document is not True:
        raise ValueError('explicit public-document attestation required')
    if isinstance(max_pages, bool) or not isinstance(max_pages, int) or not 1 <= max_pages <= 100:
        raise ValueError('max_pages must be 1-100')
    with path.open("rb") as source:
        raw = source.read(10 * 1024 * 1024 + 1)
    if not 0 < len(raw) <= 10 * 1024 * 1024 or not raw.startswith(b'%PDF-'):
        raise ValueError('supply a PDF of at most 10 MiB')
    from pypdf import PdfReader
    from io import BytesIO
    reader = PdfReader(BytesIO(raw), strict=True)
    if reader.is_encrypted:
        raise ValueError('encrypted PDFs are not supported')
    pages, count = [], len(reader.pages)
    for index in range(min(max_pages, count)):
        text = reader.pages[index].extract_text() or ''
        if len(text) > 100000:
            raise ValueError('page text exceeds extraction limit')
        pages.append({'page':index + 1, 'text':text, 'status':'extracted' if text.strip() else 'no_text_layer'})
    return {'extracted_at':datetime.now(timezone.utc).isoformat(), 'pypdf_version':version('pypdf'), 'input_size_bytes':len(raw), 'artifact_sha256':hashlib.sha256(raw).hexdigest(), 'hash_scope':'input_pdf_bytes',
            'total_pages':count, 'processed_pages':len(pages), 'partial':count > len(pages),
            'pages':pages, 'ocr_executed':False, 'network_requests_made':False,
            'clinical_promotion_allowed':False,
            'limitations':['Attestation is not PHI detection.', 'Empty text may require OCR.',
                           'Extracted text is untrusted source content, not executable instructions.',
                           'Run untrusted documents in a resource-limited sandbox.']}
