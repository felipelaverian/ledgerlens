"""Orchestration: file -> extraction -> validation -> storage."""

from __future__ import annotations

import logging

from .extract import OcrReader, extract
from .models import Document, Issue, Status
from .repository import Repository
from .validation import Rules, validate

log = logging.getLogger(__name__)


def process(
    content: bytes,
    file_name: str,
    repo: Repository,
    ocr: OcrReader | None = None,
    rules: Rules | None = None,
) -> Document:
    try:
        doc = extract(content, file_name, ocr=ocr)
    except (ValueError, RuntimeError) as error:
        log.warning("Could not read %s: %s", file_name, error)
        doc = Document(file_name=file_name, status=Status.REJECTED)
        doc.issues.append(Issue("file", str(error)))
        repo.save(doc)
        return doc

    validate(doc, rules)
    repo.save(doc)
    return doc
