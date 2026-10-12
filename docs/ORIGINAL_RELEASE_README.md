> **v2.0.0-rc.2 validation note (2026-09-23):** This release materially expands governed master data and replaces the fixed allocation demo UX with a configurable workbench. Backend regression is 100/100 passing with 84% measured coverage. It is an internal release candidate, not a claim of live-ERP, penetration-test, 10m-row performance, or customer production qualification. See `docs/VALIDATION_REPORT.md`.

# Intercompany Transfer Pricing Hub — Operations, Analytics & Governance

**Version:** 2.4.0-rc.3-hotfix7  
**Release class:** Internal Enterprise Release Candidate (external production qualification still required)  
**Architecture:** Next.js + FastAPI + PostgreSQL + Redis + MinIO + n8n + deterministic Python TP engine

This application operationalizes approved Transfer Pricing policy through the controlled lifecycle:

**ERP/finance data → ingestion → validation → mapping → allocation → authoritative imported-data P&L → policy-specific TP calculation → YTD/YTG monitoring → deterministic variance bridge → simulation → true-up → multi-level approval → journal → ERP adapter → reconciliation → audit/evidence.**



## Hotfix 7 qualification reliability

Hotfix 7 separates immutable package validation from mutable runtime test artifacts. Release validation runs before pytest, coverage/cache files are redirected to `qualification/results`, local `.env` is temporarily isolated and restored during package validation, and current-run release evidence is synchronized before browser UAT. See `docs/HOTFIX7_QUALIFICATION_ISOLATION.md`.

## German / English localisation

`v2.0.0-rc.2` adds a professional bilingual **German (de-DE) / English (en-GB)** interface. German is automatically selected for German browser environments and can be changed with the persistent **DE / EN** switch on the login screen and application header. Numbers, currencies, percentages, dates, statuses, finance/TP terminology and deterministic Copilot explanations are locale-aware. See `README_DE.md` and `docs/GERMAN_LOCALISATION.md`.

## Implemented RC capabilities

- Fixed-precision/`Decimal` deterministic TP calculations.
- TNMM (ROS, EBIT/Total Costs, EBIT/Operating Costs, Berry Ratio), Cost Plus, Resale Price/Minus, CUP variance framework, Profit Split, service charging and FX calculations.
- Versioned machine-readable TP policies and calculation manifests.
- **Governed Master Data:** dedicated Legal Entity governance plus an enterprise catalog for partner, GL, cost/profit center, plant, business unit, product group/SKU, customer, vendor, currency, FX source, transaction type and TP segment masters, with maker-checker, versioning, effective dates and controlled bulk onboarding.
- XLSX/CSV finance ingestion with SHA-256, validation, reject/warning tracking and control totals.
- Versioned ERP→TP mapping rules and mapping coverage/conflict detection.
- **Authoritative imported-data P&L generation:** validated/mapped ERP rows now publish controlled segment P&Ls and operational calculation snapshots with source-row lineage.
- Multi-dimensional financial data model and source-row lineage.
- Configurable Allocation Workbench with versioned cost-pool rules, maker-checker lifecycle, source selection, exclusions, weighted/composite drivers, markup/FX metadata, simulation/execution and residual reconciliation.
- Computed YTD/YTG forecast logic with **policy-method-consistent forecast PLI**, plus goal-seek price simulation.
- **Deterministic variance decomposition:** BUDGET and PRIOR_PERIOD EBIT bridges reconcile drivers to total variance with explicit residual control.
- **Production Qualification Center:** internal engineering evidence is separated from external certification gates.
- True-ups with multi-level maker/checker approval and segregation-of-duties controls.
- Multi-line balanced accounting journals, idempotent simulated SAP S/4 posting, posting attempts and reconciliation.
- Organization/workspace/client/entity tenancy model, RBAC/ABAC foundation and PostgreSQL RLS migration policies.
- Argon2 local-demo password hashing, JWT session revocation/versioning and production secret safety checks.
- Seven versioned n8n orchestration workflows; Monthly Transfer Pricing Close includes authoritative P&L generation and deterministic variance analysis (**47 nodes total**).
- Audit/lineage structures, document/evidence models and governed advisory AI boundary.
- One-click Windows Docker launcher, status, reset, checksummed backup and restore scripts.

## Internal validation evidence

- **100 automated backend tests: PASS**.
- **Overall backend coverage: 84%**; finance service 96%, allocation service 100%, master-data catalog service 75%.
- PostgreSQL Alembic migration chain has a single head through `0007_configurable_core`; offline PostgreSQL SQL generation is validated.
- Current OpenAPI specification contains **87 API paths**.
- Frontend local-import/source preflight: PASS. Targeted TypeScript validation for the new Master Data and Allocation pages: PASS.
- Full Next.js production build: **not executed successfully on this host** because dependencies were not installed and installation timed out; rerun in networked CI/Docker.
- 19 sample XLSX workbooks: integrity validated.
- `20_Authoritative_PnL_Demo.csv`: **500 coherent rows** designed to reproduce the reference entity profitability after the controlled Group IT allocation.
- 6 fictional supporting PDFs: PDF structural integrity validated.
- n8n workflow JSON: validated; **47 nodes total** across seven workflows.
- Release/package structural validation: PASS.

See `docs/VALIDATION_REPORT.md` for exact scope and limitations.

## Quick start (Windows)

Docker Desktop is the runtime prerequisite.

1. Extract the release ZIP.
2. Start Docker Desktop.
3. Double-click `START_DEMO.bat`.
4. The browser opens automatically after health checks and the startup smoke test. Port 3000 is preferred; if it is occupied the launcher selects a free fallback. API, n8n, and MinIO console host ports use the same collision-safe behavior.

No local Python, Node.js, PostgreSQL, Redis, n8n or MinIO installation is intended for demo mode.


## Controlled profitability demo (sample data)

For the new source-to-Control-Tower path, use `sample_data/20_Authoritative_PnL_Demo.csv`:

1. Data Imports → validate/import.
2. Data Quality → verify 500 accepted / 0 rejected.
3. Mappings → run and verify 100% coverage.
4. Allocations → open the seeded configurable Group IT rule, simulate/execute the sample EUR 1m input, and verify zero residual. The €1m value is sample data, not hard-coded product behavior.
5. Imported P&L → build/publish the authoritative 2026-09 P&L.
6. Variance Analysis → run DE01 vs BUDGET and verify zero residual.
7. Continue Forecast → True-Up → Approval → Journal → ERP Posting → Reconciliation.

The DE01 imported-data result reconciles to Revenue EUR 111.9m, EBIT EUR 2.58489m, ROS 2.31% and a EUR 1.89111m target true-up.

## Important qualification

`v2.0.0-rc.2` is a **Production Release Candidate**, not a customer-specific “Production Qualified” certification. Real production qualification still requires external evidence such as a live SAP/ERP sandbox qualification, independent penetration test, customer Entra/Okta validation, independent TP/Finance UAT, production-scale infrastructure testing, parallel close cycles and a production DR exercise. These are listed in `docs/EXTERNAL_QUALIFICATION_REQUIRED.md`.

No simulated ERP connector, internal security check, or synthetic UAT is represented as an external certification.


### Windows host-port fallback
`START_DEMO.bat` automatically selects collision-safe host ports for the application (starting at 3000), API (8000), n8n (5678) and MinIO Console (9001). Container-internal service ports remain stable, while the selected host-port map is propagated to the frontend build, API CORS and smoke tests.


## RC.10 governed Entity Master

The Legal Entities page is now an operational master-data module rather than a read-only seeded list. Use the dedicated demo **Master Data Steward** (`data.steward@otp.local` / `Demo-DataSteward-2026!`) to create or edit a legal entity, save a draft, and submit it for review. A separate authorized reviewer must approve the request before the PostgreSQL Entity Master changes. Every approved state is stored as an immutable entity version.

`sample_data/01_Entity_Master.xlsx` can also be uploaded for controlled bulk onboarding. The application previews CREATE / UPDATE / NO_CHANGE / INVALID rows before staging governed requests. Missing rows are never treated as implicit deletions.


Note: In rc.2, START_DEMO.bat and START_OTP.bat attempt to start Docker Desktop automatically if it is installed but not already running.


RC.3 environment fix: the generated `.env` now uses the same release/project identifiers as the launcher and is compatible with Windows PowerShell 5.1.

## v2.4.0-rc.3 Practicality Upgrade

This release strengthens multi-stage allocations, benchmark comparable management, governed approvals, journal templates, reconciliation controls, evidence packs, dependency impact and audit reconstruction. It remains a release candidate; external ERP, enterprise IdP, penetration-test and customer UAT qualification are not self-certified.

## One-click final 10/10 practicality qualification

After extracting the release on Windows, double-click `QUALIFY_10_10.bat`. The qualifier starts the actual Docker application, runs backend regression/coverage and release validation, executes Chromium browser plus live API UAT across all 15 target layers, creates `qualification/results/LOCAL_10_10_QUALIFICATION.md`, and synchronizes the evidence into the in-app Qualification Center. A layer is reported as 10/10 only when its required local runtime checks pass.
