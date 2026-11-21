"""Export the ledger to CSV or Excel."""

from __future__ import annotations

import csv
import io

COLUMNS = [
    "file_name", "status", "doc_type", "number", "issue_date", "vendor_tax_id", "vendor_name",
    "currency", "subtotal", "tax", "total", "issues",
]
_REVIEW_FILL = "FFF2CC"  # light yellow


def _row(item: dict) -> list:
    issues = "; ".join(f"[{i['severity']}] {i['field']}: {i['message']}" for i in item.get("issues", []))
    return [issues if column == "issues" else item.get(column) for column in COLUMNS]


def to_csv(items: list[dict]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(COLUMNS)
    writer.writerows(_row(item) for item in items)
    return buffer.getvalue()


def to_xlsx(items: list[dict]) -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Ledger"
    sheet.append(COLUMNS)
    for cell in sheet[1]:
        cell.font = Font(bold=True)
    fill = PatternFill("solid", fgColor=_REVIEW_FILL)
    for item in items:
        sheet.append(_row(item))
        if item.get("status") != "APPROVED":
            for cell in sheet[sheet.max_row]:
                cell.fill = fill
    sheet.freeze_panes = "A2"
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
