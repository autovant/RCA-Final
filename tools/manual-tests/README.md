# Manual Test Helpers

Utilities in this folder support ad hoc verification of the RCA Engine without touching the automated pytest suites.

- `get_token.py` – Registers/logs in a demo user and saves a short-lived API token to `test_token.txt` for reuse.
- `test_upload.py` – Uploads `test-error.log` and prints progress events to validate ingestion.
- `test_sse_stream.py` – Streams the first few SSE events for a hard-coded job.
- `backend-test.html` – Lightweight browser page for manual API smoke checks.
- `test-error.log` / `test-log.txt` / `test-register.json` – Sample payloads consumed by the scripts above.

Run these scripts directly from this directory to keep paths resolved automatically.
