"""Helpers that normalize amounts, dates, currencies and tax IDs read by OCR."""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime

# Longest symbols first, so "US$" wins over "$". A bare "$" is ambiguous (USD, MXN, CLP...) and is ignored.
_CURRENCIES = {
    "US$": "USD", "USD": "USD", "S/.": "PEN", "S/": "PEN", "PEN": "PEN", "R$": "BRL", "BRL": "BRL",
    "€": "EUR", "EUR": "EUR", "£": "GBP", "GBP": "GBP", "MXN": "MXN", "CLP": "CLP", "COP": "COP",
}

# English and Spanish month abbreviations
_MONTHS = {
    "JAN": 1, "ENE": 1, "FEB": 2, "MAR": 3, "APR": 4, "ABR": 4, "MAY": 5, "JUN": 6, "JUL": 7,
    "AUG": 8, "AGO": 8, "SEP": 9, "SET": 9, "OCT": 10, "NOV": 11, "DEC": 12, "DIC": 12,
}


def strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")


def detect_currency(text: str | None, default: str | None = None) -> str | None:
    if not text:
        return default
    upper = text.upper()
    for symbol in sorted(_CURRENCIES, key=len, reverse=True):
        if symbol in upper:
            return _CURRENCIES[symbol]
    return default


def parse_amount(text: str | None) -> float | None:
    """Turn 'S/ 1,180.00', '1.180,00' or '1180' into 1180.0.

    Rule: the last separator ('.' or ',') followed by one or two digits is the decimal mark.
    """
    if text is None:
        return None
    cleaned = re.sub(r"[^\d,.\-]", "", str(text))
    if not re.search(r"\d", cleaned):
        return None
    negative = cleaned.startswith("-")
    cleaned = cleaned.lstrip("-")
    match = re.search(r"[.,](\d{1,2})$", cleaned)
    if match:
        whole = re.sub(r"[.,]", "", cleaned[: match.start()])
        cleaned = f"{whole or '0'}.{match.group(1)}"
    else:
        cleaned = re.sub(r"[.,]", "", cleaned)
    try:
        value = round(float(cleaned), 2)
    except ValueError:
        return None
    return -value if negative else value


def parse_date(text: str | None) -> date | None:
    """Accept 2026-11-15, 15/11/2026, 15-11-26, 15 NOV 2026, Nov 15, 2026 and 15 de noviembre de 2026.

    Numeric dates are read day-first, which is the convention in most countries.
    """
    if not text:
        return None
    cleaned = strip_accents(text.strip().upper())
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d/%m/%y", "%d-%m-%y"):
        try:
            return datetime.strptime(cleaned[:10] if fmt == "%Y-%m-%d" else cleaned, fmt).date()
        except ValueError:
            continue
    day_first = re.search(r"(\d{1,2})\s*(?:DE\s+)?([A-Z]{3})[A-Z]*\.?\s*(?:DE(?:L)?\s+)?(\d{4})", cleaned)
    month_first = re.search(r"([A-Z]{3})[A-Z]*\.?\s+(\d{1,2}),?\s+(\d{4})", cleaned)
    if day_first:
        day, month, year = day_first.groups()
    elif month_first:
        month, day, year = month_first.groups()
    else:
        return None
    if month not in _MONTHS:
        return None
    try:
        return date(int(year), _MONTHS[month], int(day))
    except ValueError:
        return None


def clean_tax_id(text: str | None) -> str | None:
    """Keep only letters and digits: '76.086.428-5' -> '760864285', 'R.U.C. 20555555556' -> '20555555556'."""
    if not text:
        return None
    cleaned = re.sub(r"[^0-9A-Z]", "", strip_accents(text.upper()))
    cleaned = re.sub(r"^(RUC|RUT|NIF|CIF|VAT|TAXID)", "", cleaned)
    return cleaned or None


def doc_type_from_label(label: str | None) -> str:
    text = strip_accents((label or "").upper())
    if "CREDIT" in text or "CREDITO" in text:
        return "CREDIT_NOTE"
    if "DEBIT" in text or "DEBITO" in text:
        return "DEBIT_NOTE"
    if "FACTURA" in text or "INVOICE" in text:
        return "INVOICE"
    if "BOLETA" in text or "RECEIPT" in text or "TICKET" in text:
        return "RECEIPT"
    return "OTHER"
