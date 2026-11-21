import json
from datetime import date

import pytest

from ledgerlens.extract import extract
from ledgerlens.textract_parser import parse_analyze_expense
from ledgerlens.ubl_parser import parse_ubl


def test_peruvian_ubl_invoice(samples):
    doc = parse_ubl((samples / "ubl_invoice_pe.xml").read_bytes())
    assert doc.doc_type == "INVOICE"
    assert doc.number == "F001-00000245"
    assert doc.issue_date == date(2026, 11, 10)
    assert doc.currency == "PEN"
    assert doc.vendor_tax_id == "20555555556"
    assert doc.buyer_tax_id == "20601234565"
    assert (doc.subtotal, doc.tax, doc.total) == (500.0, 90.0, 590.0)
    assert len(doc.line_items) == 2


def test_peppol_ubl_invoice(samples):
    doc = parse_ubl((samples / "peppol_invoice_es.xml").read_bytes())
    assert doc.number == "INV-2026-0042"
    assert doc.vendor_name == "Iberia Demo Consulting"
    assert doc.vendor_tax_id == "ESB12345674"
    assert doc.currency == "EUR"
    assert (doc.subtotal, doc.tax, doc.total) == (1000.0, 210.0, 1210.0)
    assert doc.line_items[0].description == "Cloud architecture consulting"


def test_invalid_xml_raises():
    with pytest.raises(ValueError):
        parse_ubl(b"<Invoice>")


def test_textract_invoice(samples):
    doc = parse_analyze_expense(json.loads((samples / "textract_invoice_pe.json").read_text()))
    assert doc.number == "F002-00001873"
    assert doc.doc_type == "INVOICE"
    assert doc.vendor_tax_id == "20555555556"
    assert doc.currency == "PEN"
    assert (doc.subtotal, doc.tax, doc.total) == (1000.0, 180.0, 1180.0)
    assert len(doc.line_items) == 1


def test_textract_without_documents_raises():
    with pytest.raises(ValueError):
        parse_analyze_expense({"ExpenseDocuments": []})


def test_extract_rejects_unknown_format():
    with pytest.raises(ValueError):
        extract(b"hello", "notes.txt")


def test_extract_needs_ocr_for_images():
    with pytest.raises(RuntimeError):
        extract(b"fake", "photo.jpg")
