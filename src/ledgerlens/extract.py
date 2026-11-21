"""Pick the right reader for each file.

- XML        -> ubl_parser (exact, no OCR cost)
- PDF/image  -> Amazon Textract AnalyzeExpense
- JSON       -> a saved Textract response (local development and tests)

boto3 is imported only when AWS is actually used, so tests run without credentials.
"""

from __future__ import annotations

import json
from pathlib import PurePath
from typing import Protocol

from .models import Document
from .textract_parser import parse_analyze_expense
from .ubl_parser import parse_ubl

IMAGE_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff"}


class OcrReader(Protocol):
    def analyze(self, content: bytes, file_name: str) -> dict: ...


class TextractReader:
    """Synchronous AnalyzeExpense call. Multi-page PDFs need the asynchronous API."""

    def __init__(self, client=None, region: str | None = None):
        if client is None:
            import boto3  # deferred import

            client = boto3.client("textract", region_name=region)
        self._client = client

    def analyze(self, content: bytes, file_name: str) -> dict:
        return self._client.analyze_expense(Document={"Bytes": content})


def extract(content: bytes, file_name: str, ocr: OcrReader | None = None) -> Document:
    extension = PurePath(file_name).suffix.lower()
    if extension == ".xml":
        return parse_ubl(content, file_name=file_name)
    if extension == ".json":
        return parse_analyze_expense(json.loads(content), file_name=file_name)
    if extension in IMAGE_EXTENSIONS:
        if ocr is None:
            raise RuntimeError("An OCR reader (Textract) is required for PDFs and images")
        return parse_analyze_expense(ocr.analyze(content, file_name), file_name=file_name)
    raise ValueError(f"Unsupported format: {extension or 'no extension'}")
