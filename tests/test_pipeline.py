import csv
import io

from ledgerlens.export import to_csv, to_xlsx
from ledgerlens.models import Status
from ledgerlens.pipeline import process
from ledgerlens.repository import InMemoryRepository


def test_samples_end_to_end(samples):
    repo = InMemoryRepository()
    statuses = {
        name: process((samples / name).read_bytes(), name, repo).status
        for name in ("ubl_invoice_pe.xml", "textract_invoice_pe.json", "textract_blurry_photo.json")
    }
    assert statuses == {
        "ubl_invoice_pe.xml": Status.APPROVED,
        "textract_invoice_pe.json": Status.APPROVED,
        "textract_blurry_photo.json": Status.NEEDS_REVIEW,
    }
    assert len(repo.all()) == 3


def test_unreadable_file_is_rejected_and_stored():
    repo = InMemoryRepository()
    doc = process(b"hello", "notes.txt", repo)
    assert doc.status == Status.REJECTED
    assert len(repo.all()) == 1


def test_csv_export_has_one_row_per_document(samples):
    repo = InMemoryRepository()
    process((samples / "ubl_invoice_pe.xml").read_bytes(), "ubl_invoice_pe.xml", repo)
    rows = list(csv.reader(io.StringIO(to_csv(repo.all()))))
    assert rows[0][0] == "file_name"
    assert rows[1][1] == "APPROVED"


def test_xlsx_export_is_a_zip_file(samples):
    repo = InMemoryRepository()
    process((samples / "ubl_invoice_pe.xml").read_bytes(), "ubl_invoice_pe.xml", repo)
    assert to_xlsx(repo.all())[:2] == b"PK"
