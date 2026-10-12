# Changelog

## 2.4.0-rc.3-hotfix7 — Enterprise governance & reviewability upgrade

- Added reviewable Master Data and approval workflows with field-level diff, return-for-rework and notifications.
- Added deterministic true-up policy preview, mismatch blocking and duplicate proposal protection.
- Added global signed-in user visibility, notifications, Back/Forward context navigation and broad object drill-down.
- Improved P&L, imports, journals, postings, reconciliation, exceptions, Data Quality, audit, security, integrations, workflows, qualification and system health.
- Added dedicated service-account/integration permissions, evidence delivery fixes and real runtime health probes.
- Added Hotfix 7 regression tests and release documentation.

# v2.4.0-rc.3-hotfix7

- Fixed qualification sequencing so release/package integrity is validated before backend pytest can create runtime artifacts.
- Isolated `.coverage` and `.pytest_cache` into `qualification/results` instead of the release tree.
- Temporarily isolates a locally generated runtime `.env` outside the release tree during package validation, then restores it safely.
- Publishes and synchronizes current-run release-integrity evidence before Chromium UAT, preventing stale Qualification Center status.
- Added static release-validator checks for qualification isolation/order and aligned executable/version markers to Hotfix 6.
- Preserved all existing backend, browser/API, security, governance and external-qualification gates.

# v2.4.0-rc.3-hotfix5

- Added operation-specific bounded qualification timeouts: 30s standard API, 180s data-processing API, and 300s only for the full Segmented P&L scenario.
- Increased normal Playwright test budget to 90s and assertion budget to 15s for local Docker Desktop variability.
- Fixed Qualification Center UAT sequencing so final runtime evidence is not required before it is generated.
- Aligned qualification expectations and executable version markers to Hotfix 5.

# v2.4.0-rc.3-hotfix4

- Fixed Qualification Center runtime/evidence version alignment.
- Fixed Security form label accessibility and deterministic Playwright selectors.
- Fixed ERP simulator retry semantics so successful postings are idempotently replayable after journal reconciliation.
- Added bounded qualification API/test timeouts with failure artifacts retained.
- Preserved all external customer/third-party qualification gates.

# v2.4.0-rc.3

- Added governed benchmark management domain with expiry status and policy assignment guard.
- Added writable exception case lifecycle with audit events.
- Added versioned document/evidence upload, SHA-256 lineage, supersession, scoped download and text evidence search.
- Added integration connection creation and explicit non-live connector simulator tests.
- Added governed Data Quality Rule, Workflow Definition and Journal Template domains.
- Added benchmark and document frontend pages; upgraded exception, integration and workflow pages.
- Expanded backend regression suite from 100 to 105 passing tests.
- Regenerated OpenAPI with 96 paths.
- Preserved and version-isolated Windows/Docker launcher hardening.

# Intercompany Transfer Pricing Hub Changelog

## v2.0.0-rc.5
- Fixed `START_OTP.bat` secret-loading order: `.env` credentials are loaded before PostgreSQL credential verification.
- Hardened `sync_postgres_credentials.bat` with a self-loading fallback for `OTP_DB_PASSWORD`.
- Added release-regression checks for direct launcher secret ordering and database-preflight fallback.
- Updated release identifiers and Docker Compose project isolation to RC.5.
- Backend regression: 100/100 tests passing.

# Changelog

## v2.0.0-rc.1 — Configurable enterprise master data and allocation workbench

- Extended governed maker-checker master data beyond legal entities to intercompany partners, GL accounts, cost/profit centers, plants, business units, product groups/SKUs, customers, vendors, currencies, FX sources, transaction types and TP segments.
- Added immutable master-data versions, effective dating, controlled CSV/XLSX preview/staging, audit events and operational projections for existing GL/partner/profit-center/product engines.
- Replaced the primary fixed €1m allocation UX with a configurable workbench supporting draft/review/approval/activation, source configuration, exclusions, weighted/composite drivers, markup, FX metadata, simulation, execution and reconciliation.
- Added migration `0007_configurable_core`, new API regression tests and release documentation/matrices.
- Preserved the RC.10 API compatibility endpoint `/allocations/run`; it is no longer used as the normal business UX.
- Automated backend regression: 100/100 PASS; backend coverage measured at 84% overall, with allocation service 100%, entity master service 92%, finance engine 96%, ingestion 97%, mapping 92%, and new master-data catalog service 75%.
- External production qualification remains explicitly required for live ERP, enterprise IdP, penetration testing, Finance/TP UAT, target-infrastructure performance and disaster recovery.

## 1.0.0-rc.10 — Governed Legal Entity Master Management

- Added in-app Add/Edit/Deactivate/Reactivate for legal entities.
- Added maker-checker EntityChangeRequest workflow with DRAFT → SUBMITTED → APPROVED/REJECTED lifecycle.
- Added immutable EntityVersion history with effective dating and audit events.
- Added dedicated Master Data Steward demo persona.
- Added controlled `01_Entity_Master.xlsx` preview and bulk staging; absence from Excel never implies deletion.
- Added PostgreSQL migration `0006_entity_master_mgmt` with RLS policies for new master-data tables.
- Expanded OpenAPI to 68 paths and backend suite to 94 passing tests.

## 1.0.0-rc.10 — PostgreSQL migration compatibility hotfix
- Fixed Windows/Docker startup failure `StringDataRightTruncation: value too long for type character varying(32)` while Alembic updated `alembic_version`.
- Shortened migration revision ID from `0005_imported_pnl_variance_qualification` (40 chars) to `0005_pnl_variance_qual` (22 chars), retaining `down_revision=0004_posting_schema_compat`.
- Added automated regression test requiring every Alembic revision identifier to fit the standard 32-character version column.
- Revalidated the migration head, PostgreSQL offline DDL generation, release structure and full backend test suite.
- Release-isolated Docker project is now `enterprise-otp-demo-100rc10`.

## 1.0.0-rc.8
- Fixed cross-release Docker project identity leakage that could make RC.7 reuse RC.5 PostgreSQL volumes.
- Enforced release-specific Compose project `enterprise-otp-demo-100rc8`.
- Added launcher validation of both release ID and Compose project ID before reusing `.env`.
- Added explicit startup logging of the isolated Docker project.

## v1.0.0-rc.8 — Imported-data P&L, variance decomposition and qualification center
- Closed the RC.6 data-flow gap: validated/mapped ERP records can now publish the authoritative segmented P&L and calculation snapshot used by the Control Tower.
- Added `pnl_runs` and `pnl_segment_results` with source hashes, import IDs, mapping coverage, allocation lineage, policy version, direct/allocated OPEX and source-row drilldown.
- Authoritative P&L publication is blocked when accepted rows remain unresolved, control totals do not reconcile, or active allocation rules lack completed as-of-period runs.
- Added `sample_data/20_Authoritative_PnL_Demo.csv` (500 coherent records) reproducing the reference DE01/FR01/IT01/PL01/NL02 results after the EUR 1m IT allocation.
- Added deterministic variance decomposition with BUDGET and PRIOR_PERIOD baselines; additive EBIT components reconcile to total variance with explicit residual control.
- Added Production Qualification Center with database-backed internal evidence controls and externally blocked qualification gates; external PASS cannot be self-certified through the application.
- Fixed method-consistent forecast PLI display for Cost Plus and EBIT/TC entities instead of displaying ROS for every entity.
- Added Local Finance / Data Steward demo persona for import/data-process demonstration.
- Integrated authoritative P&L and variance stages into Monthly Transfer Pricing Close orchestration; seven n8n workflows now contain 47 nodes.
- Expanded OpenAPI to 60 paths.
- Backend regression suite: 90/90 PASS; finance engine coverage 96%; overall backend coverage 84%.

## v1.0.0-rc.6 — German localisation
- Added professional bilingual German/English UI localisation with a persistent DE/EN language switch.
- German is the default UI language for German browser environments; the selected language is persisted locally.
- Localised all Operations, Data & Policy, and Governance navigation and page labels.
- Added German finance/TP terminology for legal-entity characterisations, policies, transaction types, methods, PLIs, statuses, debit/credit labels and exception categories while retaining standard abbreviations such as TNMM, ROS and EBIT.
- Added locale-aware German number, currency, percentage, date and time formatting (`de-DE`) and English formatting (`en-GB`).
- Added German-compatible numeric input parsing so values such as `0,04` and `-1.000.000` can be used in simulation inputs.
- Added German deterministic TP Evidence Copilot responses through the governed `/ai/explain/{entity}?lang=de` API path; no authoritative financial logic was moved into AI.
- Added German login, demo-role guidance, qualification wording, workflow descriptions and system-health labels.
- Added `README_DE.md` and `docs/GERMAN_LOCALISATION.md` documenting terminology, formatting, scope and validation.
- Preserved all English UI functionality and existing enterprise workflow/security controls.

# Changelog

## v1.0.0-rc.5
- Isolated demo Docker Compose project/volumes per release to prevent stale PostgreSQL volumes from being reused with newly randomized database credentials.
- Added release-ID validation for `.env`; stale release environment files are backed up and regenerated safely in demo mode.
- Added automatic FastAPI container log diagnostics whenever Docker Compose or API readiness fails.
- Preserved automatic host-port fallback for frontend, API, n8n and MinIO console.

# v1.0.0-rc.5

- Windows launcher now auto-selects free host ports for frontend (3000+), API (8000+), n8n (5678+) and MinIO console (9001+).
- Frontend build-time API URL and API CORS origin follow the selected runtime ports.
- START_DEMO, START_OTP, START_DEV, STATUS and Windows validation scripts consume the same persisted runtime port map.
- Fixes RC.2 startup failure when port 3000 or 8000 is already allocated.

# Changelog

## 1.0.0-rc.5 — Enterprise Production Release Candidate

### Architecture and data
- Added organization/workspace/client tenancy model and tenant-scoped enterprise domain tables.
- Added source import/raw/normalized finance records, partner/account/product/profit-center master data, mapping rules, allocation runs, forecast versions, simulations, approval steps, professional journal headers/lines, posting attempts, exceptions, evidence and integration/workflow records.
- Added PostgreSQL Row Level Security migration policies for tenant-scoped tables.
- Decoupled SQLAlchemy metadata from engine creation to support offline migration generation.

### TP engine
- Replaced authoritative binary-float monetary logic with Decimal/fixed precision.
- Added TNMM ROS, EBIT/TC, EBIT/Operating Costs, Berry Ratio, Cost Plus, Resale Price/Minus, CUP variance, Profit Split, FX, service charging, allocation and goal-seek utilities.
- Added versioned calculation-manifest data and deterministic demo golden cases.

### Operational TP
- Added XLSX/CSV ingestion and row validation.
- Added ERP→TP mapping, mapping coverage/conflicts and normalized finance records.
- Added deterministic allocation execution.
- Added computed YTG forecasts and price goal-seek simulation.
- Added multi-level approval and maker/checker controls.
- Added multi-line balanced journals, posting idempotency, posting-attempt records and reconciliation.

### Security/governance
- Added Argon2 local password hashing, JWT session/version revocation, account lockout and production secret checks.
- Added RBAC/ABAC foundations and entity access grants.
- Added append-oriented audit/lineage fields and controlled AI invocation structures.
- Removed deprecated `datetime.utcnow()` runtime use.

### n8n
- Expanded Monthly Transfer Pricing Close to 16 nodes with source/DQ/mapping coverage branches.
- Expanded six supporting workflows for true-up approval, ERP posting, policy lifecycle, document ingestion, forecast refresh and integration failure.

### Packaging
- Pinned Docker image versions used in Compose.
- Added one-click launch/status/reset scripts and checksummed backup/restore handling.
- Synchronized release version to 1.0.0-rc.5 across executable configuration.

### Validation
- 83 automated backend tests passing.
- 85% overall backend coverage; finance engine 96%.
- Offline PostgreSQL migration SQL generation passing.
- Frontend source/import and TS/TSX syntax preflight passing.

## 1.0.0-rc.5 — Windows port-conflict hardening
- Fixed one-click startup failure when host TCP port 5678 is already allocated by another n8n instance or previous stack.
- Added automatic auxiliary-port selection: n8n uses the first free port from 5678–5708; MinIO Console uses the first free port from 9001–9031.
- Kept container-internal service ports unchanged, so OTP↔n8n and OTP↔MinIO integration behavior is stable.
- Added early, explicit failure for required browser/API ports 3000 and 8000 rather than allowing Docker Compose to fail later with a cryptic bind error.
- Added runtime port diagnostics to the launcher and STATUS_OTP.bat.
- Bumped application/package version to 1.0.0-rc.5.

## 2.4.0-rc.3 — Practicality Upgrade

- Added executable multi-stage allocation with stage lineage and circular-allocation protection.
- Added benchmark comparable screening, annual PLI observations, deterministic comparable-level quartile statistics and maker-checker staging of recalculated benchmark ranges.
- Added governed workflow-definition resolution and workflow code/version pinning to true-up approval requests.
- Added governed journal-template execution for TP adjustment journals while retaining a compatibility fallback for older data.
- Added reconciliation-linked exception creation and controlled reconciliation certification.
- Added downloadable auditor evidence packs for adjustment-to-posting transaction chains.
- Added master-data dependency-impact preview and blocking deactivation controls for supported active dependencies.
- Added filterable audit explorer API and object-level timeline reconstruction.
- Expanded frontend workbenches for multi-stage allocations, benchmark comparables, audit filtering and reconciliation certification.
- Added Alembic revision `0008_practicality_upgrade` and expanded backend regression suite to 110 tests.

## 2.4.0-rc.3 — Target-layer practicality closure

- Completed governed TP Policy Workbench with version/history/impact lifecycle.
- Added arbitrary multi-stage allocation, cycle protection, composite drivers and recipient eligibility/benefit/threshold/cap/FX controls.
- Added comparable-level benchmark observations and deterministic statistics.
- Added multidimensional P&L cube, snapshots and locking.
- Added deterministic target-selectable true-ups, batch creation and controlled reversal.
- Expanded reusable workflow engine with version pinning, sequential/parallel groups, delegation, return/reject/withdraw/resubmit and overdue escalation.
- Added stage-level reconciliation with automatic exception creation and certification.
- Added richer exception remediation/waiver workflow and evidence fields.
- Added controlled document metadata, expiry, tags/object linkage and evidence-pack capabilities.
- Added scoped, revocable service accounts with one-time tokens stored only as SHA-256 hashes.
- Added persistent release qualification evidence synchronization.
- Expanded variance baselines and source-driven volume/price/mix/FX decomposition where the required source dimensions exist.
- Added Alembic migration `0009_practicality_10`.
- Backend regression: 116 passed / 0 failed.

## 2.4.0-rc.3-hotfix2
- Added recovery for transient Docker BuildKit `EOF` failures during frontend npm install/build.
- Limited Compose build concurrency to reduce Docker Desktop resource saturation.
- Added persistent BuildKit npm cache and stronger npm network retry settings.
- Added frontend pre-build with up to three automatic retries and Docker-engine health recovery.
- Switched frontend runtime image to Next.js standalone output for a smaller runtime footprint.
- Improved build-specific diagnostics while preserving persistent volumes.
