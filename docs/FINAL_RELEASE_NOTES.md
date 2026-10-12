# Final Release Notes — v2.0.0-rc.1

RC.1 upgrades the supplied v1.0.0-rc.10 application in place. It deliberately preserves the existing FastAPI/PostgreSQL/Next.js/n8n architecture while closing two major product-readiness gaps: cross-domain governed master data and the hard-coded allocation demo UX.

## Major additions

- Enterprise Master Data Catalog for intercompany partners, GL accounts, cost centers, profit centers, plants, business units, product groups/SKUs, customers, vendors, currencies, FX sources, transaction types and TP segments.
- Generic maker-checker change requests, immutable versions, effective dates, CSV/XLSX preview/staging, deactivate/reactivate and audit integration.
- Approved GL/partner/profit-center/product changes project into operational tables; deactivation is respected by ingestion for active GL/partner validation.
- Allocation Workbench with configurable cost pools, sender/source configuration, exclusion amounts, standard/composite drivers, markup, FX metadata, effective dates, rule lifecycle, simulation, execution and reconciliation.
- New Alembic revision `0007_configurable_core` and updated OpenAPI (87 paths).
- `backend/pytest.ini` for portable test discovery.
- Expanded automated suite to **100/100 passing**; measured backend coverage **84%**.
- New functional-coverage, role-matrix and UAT-readiness documents.

## Compatibility

The existing `/allocations/run` API is retained for backward compatibility/sample use but is no longer used by the normal Allocation UI. Existing RC.10 data structures and operational flows remain in place; schema changes are additive except for the new active-state behavior on operational master projections.

## Qualification boundary

RC.1 is not represented as fully production qualified. Live ERP/IdP, penetration test, target-scale performance, full frontend/Docker build-runtime validation, customer Finance/TP UAT, parallel close and DR remain explicit gates.
