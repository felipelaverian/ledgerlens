"""Domain models. No external dependencies."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
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
    quantity: float | None = None
    unit_price: float | None = None
    amount: float | None = None


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
    subtotal: float | None = None
    tax: float | None = None
    total: float | None = None
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
        data["issues"] = [
            {"field": i.field, "message": i.message, "severity": i.severity.value} for i in self.issues
        ]
        return data
