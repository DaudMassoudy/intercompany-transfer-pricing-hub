# Production Readiness — v2.0.0-rc.1

## Current status

**Internal Enterprise Release Candidate — not customer Production Qualified.**

The release has passed the internally executable backend regression, coverage, source-integrity, OpenAPI, migration-generation and package-structure checks documented in `VALIDATION_REPORT.md`. A full Next.js production build and Docker runtime launch were not executable on this host and therefore are not marked PASS.

## Internally demonstrated capabilities

- Fixed-precision deterministic TP engine with multiple methods/PLIs.
- Controlled CSV/XLSX finance ingestion, mapping, P&L, forecasting, variance, true-up, accounting and reconciliation foundations.
- Governed Legal Entity Master plus enterprise Master Data Catalog with maker-checker, versioning, effective dates, bulk preview/staging and operational projection for key master domains.
- Configurable Allocation Workbench with approval lifecycle, source modes, exclusions, weighted/composite drivers, markup/FX metadata, simulation, execution and residual reconciliation.
- Tenant-aware schema, RBAC/ABAC foundation and PostgreSQL RLS migration policies.
- Seven n8n workflow assets, audit/lineage structures and a governed advisory AI boundary.
- German/English localisation.
- **100 backend tests passing; 84% overall measured coverage; finance service 96%; allocation service 100%; master-data catalog service 75%.**
- One-click Windows/Docker scripts preserved in the package.

## Production promotion blockers

Before production promotion, rerun a full frontend build and Docker startup in CI/target infrastructure, then complete live ERP connector certification, enterprise IdP/MFA validation, independent penetration testing, Finance/TP UAT, parallel-close evidence, target-scale performance (including 10m+ rows), backup/restore verification and DR rehearsal. See `PRODUCTION_QUALIFICATION_SCORECARD.md`.
