"""Read UBL 2.1 e-invoices (XML).

UBL is the international standard behind Peppol (Europe, Australia, Singapore...) and
several national e-invoicing systems such as Peru's. When the vendor sends the XML,
no OCR is needed: the data is exact and free to read. Standard library only.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

from .models import Document, LineItem
from .normalize import parse_date

NS = {
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
}

# UNTDID 1001 codes (Peppol) and Peru's SUNAT catalog 01
_TYPE_CODES = {
    "380": "INVOICE", "01": "INVOICE", "03": "RECEIPT",
    "381": "CREDIT_NOTE", "07": "CREDIT_NOTE", "383": "DEBIT_NOTE", "08": "DEBIT_NOTE",
}
_ROOT_TYPES = {"Invoice": "INVOICE", "CreditNote": "CREDIT_NOTE", "DebitNote": "DEBIT_NOTE"}

_TAX_ID_PATHS = (
    "cac:PartyIdentification/cbc:ID",
    "cac:PartyTaxScheme/cbc:CompanyID",
    "cac:PartyLegalEntity/cbc:CompanyID",
)
_NAME_PATHS = ("cac:PartyLegalEntity/cbc:RegistrationName", "cac:PartyName/cbc:Name")


def _text(node: ET.Element | None, *paths: str) -> str | None:
    """Return the text of the first path that exists under `node`."""
    if node is None:
        return None
    for path in paths:
        element = node.find(path, NS)
        if element is not None and element.text:
            return element.text.strip()
    return None


def _amount(value: str | None) -> float | None:
    return round(float(value), 2) if value else None


def parse_ubl(xml_bytes: bytes, file_name: str | None = None) -> Document:
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as error:
        raise ValueError(f"Invalid XML: {error}") from error

    root_name = root.tag.split("}")[-1]
    doc_type = _TYPE_CODES.get(_text(root, "cbc:InvoiceTypeCode") or "") or _ROOT_TYPES.get(root_name, "OTHER")
    vendor = root.find("cac:AccountingSupplierParty/cac:Party", NS)
    buyer = root.find("cac:AccountingCustomerParty/cac:Party", NS)
    totals = root.find("cac:LegalMonetaryTotal", NS)

    doc = Document(
        doc_type=doc_type,
        number=_text(root, "cbc:ID"),
        issue_date=parse_date(_text(root, "cbc:IssueDate")),
        currency=(_text(root, "cbc:DocumentCurrencyCode") or "").upper() or None,
        vendor_name=_text(vendor, *_NAME_PATHS),
        vendor_tax_id=_text(vendor, *_TAX_ID_PATHS),
        buyer_tax_id=_text(buyer, *_TAX_ID_PATHS),
        subtotal=_amount(_text(totals, "cbc:TaxExclusiveAmount", "cbc:LineExtensionAmount")),
        tax=_amount(_text(root, "cac:TaxTotal/cbc:TaxAmount")),
        total=_amount(_text(totals, "cbc:PayableAmount", "cbc:TaxInclusiveAmount")),
        source="ubl_xml",
        file_name=file_name,
    )
    # Data comes straight from the issuer's system: full confidence
    doc.confidence = {name: 100.0 for name in ("number", "issue_date", "vendor_tax_id", "subtotal", "tax", "total")}

    line_tag = "cac:InvoiceLine" if root_name == "Invoice" else f"cac:{root_name}Line"
    for line in root.findall(line_tag, NS):
        quantity = line.find("cbc:InvoicedQuantity", NS)
        doc.line_items.append(
            LineItem(
                description=_text(line, "cac:Item/cbc:Description", "cac:Item/cbc:Name") or "",
                quantity=_amount(quantity.text if quantity is not None else None),
                unit_price=_amount(_text(line, "cac:Price/cbc:PriceAmount")),
                amount=_amount(_text(line, "cbc:LineExtensionAmount")),
            )
        )
    return doc
