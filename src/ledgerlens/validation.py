"""Business rules that decide whether a document is approved or needs human review.

Country-specific rules (tax rates, tax ID check digits) live in countries.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from .countries import get_profile
from .models import Document, Issue, Severity, Status

REQUIRED_FIELDS = ("vendor_tax_id", "number", "issue_date", "total")


@dataclass
class Rules:
    confidence_threshold: float = 90.0
    tolerance: Decimal = Decimal("0.05")             # accepted rounding difference
    max_age_days: int = 365
    company_tax_id: str | None = None   # tax ID of the company receiving the documents
    country: str = "GENERIC"            # see countries.PROFILES


def validate(doc: Document, rules: Rules | None = None, today: date | None = None) -> Document:
    """Add issues and set the status. Returns the same object."""
    rules = rules or Rules()
    profile = get_profile(rules.country)
    today = today or date.today()
    issues: list[Issue] = []

    # 1. Required fields
    for name in REQUIRED_FIELDS:
        if not getattr(doc, name):
            issues.append(Issue(name, "Required field not found"))

    # 2. Tax IDs: check digit of the vendor, and the document must be addressed to our company
    if doc.vendor_tax_id and profile.tax_id_is_valid and not profile.tax_id_is_valid(doc.vendor_tax_id):
        issues.append(Issue("vendor_tax_id", f"{profile.tax_id_name} {doc.vendor_tax_id} has an invalid check digit"))
    if rules.company_tax_id and doc.buyer_tax_id and doc.buyer_tax_id != rules.company_tax_id:
        issues.append(Issue("buyer_tax_id", "Document is not addressed to the company"))

    # 3. Amounts must add up
    if doc.total is not None and doc.total <= 0 and doc.doc_type != "CREDIT_NOTE":
        issues.append(Issue("total", "Total is zero or negative"))
    if doc.subtotal is not None and doc.tax is not None:
        if profile.tax_rates and not _matches_a_rate(doc.subtotal, doc.tax, profile.tax_rates, rules.tolerance):
            # Can be legitimate (exempt items, mixed rates), so only a warning
            rates = ", ".join(f"{rate:.0%}" for rate in profile.tax_rates)
            message = f"{profile.tax_name} {doc.tax} does not match any {profile.name} rate ({rates})"
            issues.append(Issue("tax", message, Severity.WARNING))
        if doc.total is not None and abs(doc.subtotal + doc.tax - doc.total) > rules.tolerance:
            message = f"Subtotal + tax ({doc.subtotal + doc.tax}) does not match the total ({doc.total})"
            issues.append(Issue("total", message))

    # 4. Dates
    if doc.issue_date:
        if doc.issue_date > today + timedelta(days=1):
            issues.append(Issue("issue_date", "Issue date is in the future"))
        elif (today - doc.issue_date).days > rules.max_age_days:
            issues.append(Issue("issue_date", "Document is more than a year old", Severity.WARNING))

    # 5. OCR confidence
    for name in doc.low_confidence_fields(rules.confidence_threshold):
        issues.append(Issue(name, f"Low confidence reading ({doc.confidence[name]:.0f}%)"))

    doc.issues.extend(issues)
    if doc.status != Status.REJECTED:
        has_errors = any(issue.severity == Severity.ERROR for issue in doc.issues)
        doc.status = Status.NEEDS_REVIEW if has_errors else Status.APPROVED
    return doc


def _matches_a_rate(subtotal: Decimal, tax: Decimal, rates: tuple[Decimal, ...], tolerance: Decimal) -> bool:
    return any(abs((subtotal * rate).quantize(Decimal("0.01")) - tax) <= tolerance for rate in rates)
