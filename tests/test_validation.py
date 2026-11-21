from datetime import date

from ledgerlens.models import Document, Severity, Status
from ledgerlens.validation import Rules, validate

TODAY = date(2026, 11, 21)


def _doc(**changes) -> Document:
    values = dict(
        doc_type="INVOICE", number="F001-1", issue_date=date(2026, 11, 10), currency="PEN",
        vendor_tax_id="20555555556", subtotal=100.0, tax=18.0, total=118.0,
    )
    values.update(changes)
    return Document(**values)


def test_valid_document_is_approved():
    assert validate(_doc(), today=TODAY).status == Status.APPROVED


def test_missing_required_field_needs_review():
    doc = validate(_doc(number=None), today=TODAY)
    assert doc.status == Status.NEEDS_REVIEW
    assert any(i.field == "number" for i in doc.issues)


def test_totals_that_do_not_add_up_need_review():
    doc = validate(_doc(total=130.0), today=TODAY)
    assert doc.status == Status.NEEDS_REVIEW


def test_unexpected_tax_rate_is_only_a_warning():
    doc = validate(_doc(tax=10.0, total=110.0), today=TODAY)
    assert doc.status == Status.APPROVED
    assert [i.severity for i in doc.issues] == [Severity.WARNING]


def test_future_date_needs_review():
    assert validate(_doc(issue_date=date(2027, 1, 1)), today=TODAY).status == Status.NEEDS_REVIEW


def test_low_confidence_needs_review():
    doc = _doc()
    doc.confidence = {"total": 70.0}
    assert validate(doc, today=TODAY).status == Status.NEEDS_REVIEW


def test_document_for_another_company_needs_review():
    rules = Rules(company_tax_id="20601234565")
    doc = validate(_doc(buyer_tax_id="20999999999"), rules, today=TODAY)
    assert doc.status == Status.NEEDS_REVIEW
