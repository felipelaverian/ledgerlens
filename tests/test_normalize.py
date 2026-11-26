from datetime import date
from decimal import Decimal

import pytest

from ledgerlens.normalize import clean_tax_id, detect_currency, doc_type_from_label, parse_amount, parse_date


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("S/ 1,180.00", Decimal("1180.00")),
        ("1.180,00", Decimal("1180.00")),
        ("1180", Decimal("1180.00")),
        ("€ 12,5", Decimal("12.50")),
        ("-45.10", Decimal("-45.10")),
    ],
)
def test_parse_amount(text, expected):
    assert parse_amount(text) == expected


def test_parse_amount_is_exact():
    assert parse_amount("0.10") + parse_amount("0.20") == Decimal("0.30")
    assert str(parse_amount("590")) == "590.00"


def test_parse_amount_without_digits_returns_none():
    assert parse_amount("N/A") is None
    assert parse_amount(None) is None


@pytest.mark.parametrize(
    "text",
    ["2026-11-15", "15/11/2026", "15-11-26", "15 NOV 2026", "Nov 15, 2026", "15 de noviembre de 2026"],
)
def test_parse_date(text):
    assert parse_date(text) == date(2026, 11, 15)


def test_parse_date_garbage_returns_none():
    assert parse_date("not a date") is None


@pytest.mark.parametrize(
    ("text", "expected"),
    [("S/ 10.00", "PEN"), ("US$ 10", "USD"), ("10,00 €", "EUR"), ("$ 10", None)],
)
def test_detect_currency(text, expected):
    assert detect_currency(text) == expected


def test_clean_tax_id():
    assert clean_tax_id("76.086.428-5") == "760864285"
    assert clean_tax_id("R.U.C. 20555555556") == "20555555556"


def test_doc_type_from_label():
    assert doc_type_from_label("FACTURA ELECTRÓNICA") == "INVOICE"
    assert doc_type_from_label("Nota de Crédito") == "CREDIT_NOTE"
    assert doc_type_from_label("Sales receipt") == "RECEIPT"
    assert doc_type_from_label(None) == "OTHER"
