# RC.5 ERP Posting Fix

## Root cause
The legacy v0.x schema created `erp_postings.journal_id` as NOT NULL. The enterprise RC introduced `journal_headers` and `erp_postings.journal_header_id`, but the old `journal_id` constraint remained NOT NULL in PostgreSQL. The API therefore passed SQLite/TestClient tests while PostgreSQL rejected a valid enterprise posting insert.

## Fix
Migration `0004_posting_schema_compat` makes the legacy `journal_id` nullable. New enterprise postings continue to use `journal_header_id`; historical v0.x postings remain valid.

## Expected user flow
Fully approved adjustment -> balanced journal -> Post to SAP simulator -> simulated ERP document -> automatic reconciliation.
