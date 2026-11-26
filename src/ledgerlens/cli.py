"""Local usage: ledgerlens <file or folder> [--output ledger.xlsx]."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .countries import PROFILES
from .export import to_csv, to_xlsx
from .extract import IMAGE_EXTENSIONS, TextractReader
from .models import Status
from .pipeline import process
from .repository import InMemoryRepository
from .validation import Rules

SUPPORTED = IMAGE_EXTENSIONS | {".xml", ".json"}


def _files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    return sorted(p for p in path.iterdir() if p.suffix.lower() in SUPPORTED)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Turn invoices and receipts into a validated ledger")
    parser.add_argument("path", type=Path, help="file or folder with documents")
    parser.add_argument("--output", type=Path, default=Path("ledger.xlsx"), help=".xlsx or .csv")
    parser.add_argument("--textract", action="store_true", help="read PDFs and images with Amazon Textract")
    parser.add_argument(
        "--country", default="GENERIC", type=str.upper, choices=sorted(PROFILES), help="tax rules to apply"
    )
    parser.add_argument("--company-tax-id", help="check that documents are addressed to this tax ID")
    parser.add_argument("--confidence", type=float, default=90.0, help="minimum OCR confidence (0-100)")
    args = parser.parse_args(argv)

    if not args.path.exists():
        print(f"Not found: {args.path}", file=sys.stderr)
        return 1

    repo = InMemoryRepository()
    rules = Rules(confidence_threshold=args.confidence, company_tax_id=args.company_tax_id, country=args.country)
    ocr = TextractReader() if args.textract else None

    print(f"{'File':<32} {'Number':<16} {'Total':>14}  Status")
    for file in _files(args.path):
        doc = process(file.read_bytes(), file.name, repo, ocr=ocr, rules=rules)
        total = f"{doc.currency or ''} {doc.total}" if doc.total is not None else "-"
        print(f"{file.name:<32} {doc.number or '-':<16} {total:>14}  {doc.status}")
        for issue in doc.issues:
            print(f"{'':<32} - [{issue.severity}] {issue.field}: {issue.message}")

    items = repo.all()
    approved = sum(1 for item in items if item["status"] == Status.APPROVED)
    if args.output.suffix.lower() == ".csv":
        args.output.write_text(to_csv(items), encoding="utf-8")
    else:
        args.output.write_bytes(to_xlsx(items))
    print(f"\n{len(items)} processed, {approved} approved, {len(items) - approved} need attention -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
