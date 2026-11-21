"""Convert an Amazon Textract AnalyzeExpense response into a Document.

Textract returns a normalized `Type` per field (TOTAL, TAX, VENDOR_NAME...) and the label
exactly as printed on the paper (`LabelDetection`). Local labels such as "RUC", "IVA" or
"OP. GRAVADA" often come back as OTHER, so fields are also mapped by label.
"""

from __future__ import annotations

from .models import Document, LineItem
from .normalize import (
    clean_tax_id,
    detect_currency,
    doc_type_from_label,
    parse_amount,
    parse_date,
    strip_accents,
)

_BY_TYPE = {
    "VENDOR_NAME": "vendor_name",
    "NAME": "vendor_name",
    "INVOICE_RECEIPT_ID": "number",
    "INVOICE_RECEIPT_DATE": "issue_date",
    "TOTAL": "total",
    "AMOUNT_DUE": "total",
    "SUBTOTAL": "subtotal",
    "TAX": "tax",
    "TAX_PAYER_ID": "vendor_tax_id",
    "VENDOR_VAT_NUMBER": "vendor_tax_id",
}

# Label fragment (uppercase, no accents) -> field. First match wins, so specific labels go first.
_BY_LABEL = [
    ("R.U.C", "vendor_tax_id"), ("RUC", "vendor_tax_id"), ("RUT", "vendor_tax_id"), ("NIF", "vendor_tax_id"),
    ("TAX ID", "vendor_tax_id"), ("VAT NO", "vendor_tax_id"), ("VAT NUMBER", "vendor_tax_id"),
    ("OP. GRAVADA", "subtotal"), ("OP.GRAVADA", "subtotal"), ("NET AMOUNT", "subtotal"), ("SUBTOTAL", "subtotal"),
    ("IGV", "tax"), ("IVA", "tax"), ("VAT", "tax"), ("SALES TAX", "tax"),
    ("IMPORTE TOTAL", "total"), ("TOTAL A PAGAR", "total"), ("TOTAL DUE", "total"),
    ("FECHA DE EMISION", "issue_date"), ("INVOICE DATE", "issue_date"),
    ("FACTURA", "number"), ("BOLETA", "number"), ("INVOICE NO", "number"), ("RECEIPT NO", "number"),
]
_BUYER_HINTS = ("CLIENTE", "CLIENT", "CUSTOMER", "BUYER", "ADQUIRIENTE", "BILL TO")
_AMOUNT_FIELDS = ("subtotal", "tax", "total")


def _text(detection: dict | None) -> str | None:
    return (detection or {}).get("Text")


def _confidence(detection: dict | None) -> float:
    return float((detection or {}).get("Confidence", 0.0))


def _field_for(summary_field: dict) -> str | None:
    label = strip_accents((_text(summary_field.get("LabelDetection")) or "").upper())
    for fragment, name in _BY_LABEL:
        if fragment in label:
            if name == "vendor_tax_id" and any(hint in label for hint in _BUYER_HINTS):
                return "buyer_tax_id"
            return name
    return _BY_TYPE.get(_text(summary_field.get("Type")) or "")


def parse_analyze_expense(response: dict, file_name: str | None = None) -> Document:
    expense_docs = response.get("ExpenseDocuments") or []
    if not expense_docs:
        raise ValueError("The Textract response has no ExpenseDocuments")
    expense = expense_docs[0]  # one document per file

    doc = Document(source="textract", file_name=file_name)
    amount_texts: list[str] = []
    number_label: str | None = None

    for summary_field in expense.get("SummaryFields", []):
        name = _field_for(summary_field)
        value = _text(summary_field.get("ValueDetection"))
        if not name or not value:
            continue
        value_confidence = _confidence(summary_field.get("ValueDetection"))
        confidence = min(value_confidence, _confidence(summary_field.get("Type")) or 100.0)
        if doc.confidence.get(name, -1) >= confidence:
            continue  # keep the reading we trust more
        doc.confidence[name] = confidence

        if name in _AMOUNT_FIELDS:
            amount_texts.append(value)
            setattr(doc, name, parse_amount(value))
        elif name == "issue_date":
            doc.issue_date = parse_date(value)
        elif name in ("vendor_tax_id", "buyer_tax_id"):
            setattr(doc, name, clean_tax_id(value))
        elif name == "number":
            doc.number = value.replace(" ", "").upper()
            number_label = _text(summary_field.get("LabelDetection"))
        else:
            setattr(doc, name, value.strip())

    currency_codes = [(f.get("Currency") or {}).get("Code") for f in expense.get("SummaryFields", [])]
    doc.currency = next((c.upper() for c in currency_codes if c), None) or detect_currency(" ".join(amount_texts))
    doc.doc_type = doc_type_from_label(number_label)
    doc.line_items = list(_line_items(expense))
    return doc


def _line_items(expense: dict):
    for group in expense.get("LineItemGroups", []):
        for item in group.get("LineItems", []):
            values = {
                _text(f.get("Type")): _text(f.get("ValueDetection"))
                for f in item.get("LineItemExpenseFields", [])
                if _text(f.get("Type")) and _text(f.get("ValueDetection"))
            }
            description = values.get("ITEM") or values.get("PRODUCT_CODE")
            if not description:
                continue
            yield LineItem(
                description=description.strip(),
                quantity=parse_amount(values.get("QUANTITY")),
                unit_price=parse_amount(values.get("UNIT_PRICE")),
                amount=parse_amount(values.get("PRICE")),
            )
