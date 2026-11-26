"""Lambda triggered by S3: reads each uploaded file, validates it and stores the result."""

from __future__ import annotations

import logging
import os
import urllib.parse

import boto3

from ..extract import TextractReader
from ..pipeline import process
from ..repository import DynamoDBRepository
from ..validation import Rules

log = logging.getLogger()
log.setLevel(logging.INFO)

_s3 = boto3.client("s3")
_repo = DynamoDBRepository(os.environ["TABLE_NAME"])
_ocr = TextractReader()
_rules = Rules(
    confidence_threshold=float(os.environ.get("CONFIDENCE_THRESHOLD", "90")),
    company_tax_id=os.environ.get("COMPANY_TAX_ID") or None,
    country=os.environ.get("COUNTRY", "GENERIC"),
)


def handler(event, context):
    results = []
    for record in event.get("Records", []):
        bucket = record["s3"]["bucket"]["name"]
        key = urllib.parse.unquote_plus(record["s3"]["object"]["key"])
        content = _s3.get_object(Bucket=bucket, Key=key)["Body"].read()
        doc = process(content, key.split("/")[-1], _repo, ocr=_ocr, rules=_rules)
        log.info("Processed %s -> %s", key, doc.status)
        results.append({"key": key, "status": doc.status.value})
    return {"processed": results}
