# ERP Adapter Architecture — v2.0.0-rc.1

Canonical connector operations:

1. `health_check()`
2. `fetch_master_data()` / future live adapter extension
3. `fetch_gl()` / future live adapter extension
4. `fetch_intercompany_transactions()` / future live adapter extension
5. `submit_journal(journal_payload, idempotency_key)`
6. `get_posting_status(document_number)`
7. `reverse_posting(document_number, reason)`

The RC includes a deterministic SAP S/4 simulator for contract/demo tests and a live SAP S/4 contract that explicitly raises `LIVE ERP SANDBOX QUALIFICATION = PENDING` for posting operations until real credentials/implementation are supplied.

No simulated posting is represented as a live ERP posting.
