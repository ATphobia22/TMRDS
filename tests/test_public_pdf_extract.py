import pytest
pytest.importorskip('pypdf')
from pypdf import PdfWriter
from engines.public_pdf_extract import extract_public_pdf


def test_blank_pages_are_not_fabricated_text(tmp_path):
    path = tmp_path / 'synthetic.pdf'
    writer = PdfWriter()
    writer.add_blank_page(width=100,height=100)
    writer.add_blank_page(width=100,height=100)
    writer.write(path)
    result = extract_public_pdf(path, public_document=True, max_pages=1)
    assert result['partial'] and result['total_pages'] == 2
    assert result['pages'][0]['status'] == 'no_text_layer'
    assert not result['ocr_executed'] and not result['network_requests_made']
    assert len(result['artifact_sha256']) == 64
    with pytest.raises(ValueError):
        extract_public_pdf(path)


def test_non_pdf_rejected(tmp_path):
    path = tmp_path / 'bad.pdf'
    path.write_text('not a PDF')
    with pytest.raises(ValueError):
        extract_public_pdf(path, public_document=True)


def test_real_pdf_text_layer_extracted(tmp_path):
    from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
    writer = PdfWriter()
    page = writer.add_blank_page(width=200,height=200)
    font = DictionaryObject({NameObject('/Type'):NameObject('/Font'), NameObject('/Subtype'):NameObject('/Type1'), NameObject('/BaseFont'):NameObject('/Helvetica')})
    page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):font})})
    stream = DecodedStreamObject()
    stream.set_data(b'BT /F1 12 Tf 20 100 Td (Synthetic public research text) Tj ET')
    page[NameObject('/Contents')] = stream
    path = tmp_path / 'synthetic-text.pdf'
    writer.write(path)
    result = extract_public_pdf(path, public_document=True)
    assert 'Synthetic public research text' in result['pages'][0]['text']
    assert result['pages'][0]['status'] == 'extracted'
