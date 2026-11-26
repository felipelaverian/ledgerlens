"""Domain models. No external dependencies."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from decimal import Decimal
from enum import StrEnum


class Status(StrEnum):
    APPROVED = "APPROVED"          # passed every check
    NEEDS_REVIEW = "NEEDS_REVIEW"  # a human has to look at it
    REJECTED = "REJECTED"          # the file could not be read


class Severity(StrEnum):
    ERROR = "ERROR"      # forces human review
    WARNING = "WARNING"  # informative only


@dataclass
class Issue:
    field: str
    message: str
    severity: Severity = Severity.ERROR


@dataclass
class LineItem:
    description: str
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    amount: Decimal | None = None


@dataclass
class Document:
    """A normalized purchase document: invoice, receipt, credit note..."""

    doc_type: str | None = None            # INVOICE, RECEIPT, CREDIT_NOTE, DEBIT_NOTE, OTHER
    number: str | None = None              # F001-00000245, INV-2026-0042...
    issue_date: date | None = None
    currency: str | None = None            # ISO 4217 code
    vendor_name: str | None = None
    vendor_tax_id: str | None = None
    buyer_tax_id: str | None = None
    subtotal: Decimal | None = None
    tax: Decimal | None = None
    total: Decimal | None = None
    line_items: list[LineItem] = field(default_factory=list)
    source: str = "unknown"                # ubl_xml | textract
    file_name: str | None = None
    confidence: dict[str, float] = field(default_factory=dict)  # 0-100 per field, from the extractor
    issues: list[Issue] = field(default_factory=list)
    status: Status = Status.NEEDS_REVIEW

    def low_confidence_fields(self, threshold: float) -> list[str]:
        return [name for name, value in self.confidence.items() if value < threshold]

    def to_dict(self) -> dict:
        data = asdict(self)
        data["status"] = self.status.value
        data["issue_date"] = self.issue_date.isoformat() if self.issue_date else None
        # Money travels as strings: exact in JSON/CSV, and DynamoDB rejects Python floats.
        for name in ("subtotal", "tax", "total"):
            data[name] = _money(data[name])
        data["line_items"] = [
            {key: value if key == "description" else _money(value) for key, value in line.items()}
            for line in data["line_items"]
        ]
        data["confidence"] = {name: str(round(value, 1)) for name, value in self.confidence.items()}
        data["issues"] = [
            {"field": i.field, "message": i.message, "severity": i.severity.value} for i in self.issues
        ]
        return data


def _money(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None
