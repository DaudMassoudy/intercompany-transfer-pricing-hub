# Production Qualification Center — v2.0.0-rc.1

The Qualification Center separates **internal engineering evidence** from **external production qualification**.

Internal/automated controls can be evidenced by source code, deterministic tests, security controls and release artifacts. External controls cannot be self-certified by the application.

## Status model

`NOT_STARTED · IN_PROGRESS · PASS · FAIL · BLOCKED · EXTERNAL_REQUIRED · PENDING · EXPIRED`

## Seeded internal evidence controls

- fixed-precision TP arithmetic;
- golden TP regression coverage;
- controlled ingestion;
- authoritative imported-data P&L generation;
- deterministic variance bridge;
- segregation of duties;
- ERP posting idempotency;
- authorization boundaries.

## External blocking gates

- live SAP S/4 sandbox qualification;
- independent penetration test;
- enterprise Entra/Okta validation;
- independent TP professional sign-off;
- Finance UAT;
- parallel close validation;
- production DR exercise.

The application therefore reports **ENTERPRISE_PRODUCTION_RELEASE_CANDIDATE** until external blocking controls are independently satisfied.
