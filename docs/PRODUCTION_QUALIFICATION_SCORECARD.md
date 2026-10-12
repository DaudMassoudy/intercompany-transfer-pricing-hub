# Production Qualification Scorecard — v2.4.0-rc.3

This document deliberately separates **product practicality** from **production/customer qualification**.

| Gate | Status |
|---|---|
| Backend automated regression | PASS — 116/116 |
| Frontend source/import validation | PASS |
| Alembic migration head | PASS — 0009_practicality_10 |
| PostgreSQL offline migration SQL generation | PASS |
| OpenAPI generation | PASS — 139 paths |
| Release structure/integrity | PASS after packaging validation |
| Live Docker runtime in build environment | NOT RUN |
| Full browser E2E | NOT RUN |
| Live SAP / Oracle / Dynamics | EXTERNAL QUALIFICATION REQUIRED |
| Customer enterprise IdP | EXTERNAL QUALIFICATION REQUIRED |
| Independent penetration test | EXTERNAL QUALIFICATION REQUIRED |
| Finance / TP customer UAT | EXTERNAL QUALIFICATION REQUIRED |
| Parallel close | EXTERNAL QUALIFICATION REQUIRED |
| DR exercise / production infrastructure | EXTERNAL QUALIFICATION REQUIRED |

A layer can be 10/10 internally practical while these external gates remain explicitly open. The application must never call itself production-qualified until the applicable external gates have independent evidence.
