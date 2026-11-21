# Architecture

## Flow

1. A document lands in `s3://<bucket>/inbox/`.
2. The S3 event triggers the `ProcessFunction` Lambda.
3. `extract.py` picks the reader:
   - **UBL XML** (`ubl_parser.py`): exact data, no OCR cost. Works with Peppol e-invoices and national UBL systems.
   - **PDF / image** (`textract_parser.py`): Amazon Textract `AnalyzeExpense`.
4. `validation.py` checks required fields, totals, dates and OCR confidence, and sets the status.
5. The result is stored in DynamoDB (`repository.py`).

## Why this shape

- **Pure Python core.** Parsers, validation and export know nothing about AWS. AWS lives only in
  `extract.TextractReader`, `repository.DynamoDBRepository` and `handlers/`. Tests run in seconds without credentials.
- **XML first.** Many countries already exchange signed XML invoices. Reading them is exact and free;
  OCR is only for what does not come as XML (receipts, photos, paper invoices).
- **Serverless.** No servers running while idle; cost scales with the number of documents.

## Statuses

| Status | Meaning |
| --- | --- |
| `APPROVED` | Passed every check |
| `NEEDS_REVIEW` | At least one ERROR issue; a human must check it |
| `REJECTED` | The file could not be read |
