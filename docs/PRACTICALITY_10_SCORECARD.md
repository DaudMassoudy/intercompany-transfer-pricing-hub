# v2.4.0-rc.3 — Target-Layer Practicality Scorecard

## Scoring interpretation

`10/10 Practicality` means the layer now contains a usable internal product workflow: persistent business objects, configuration rather than demo-only assumptions, governance where material, authorization, validation/error behavior, audit/lineage, automated tests and an operator-facing UI/API path. It does **not** mean that unavailable third-party/customer qualification has been fabricated. Live ERP/customer IdP/external penetration testing remain explicitly external gates.

| Layer | v2.2 baseline | v2.4 internal practicality | Primary closure evidence |
|---|---:|---:|---|
| Master Data | 9.4 | **10/10** | Governed catalog plus dependency/impact protection, version/effective-date history and operational projections |
| Allocation | 9.3 | **10/10** | Arbitrary multi-stage allocation, cycle protection, composite drivers, recipient benefit/threshold/cap/FX controls, immutable runs and reconciliation |
| Benchmarks | 9.2 | **10/10** | Comparable-company screening, observations, deterministic quartiles, governed versions, expiry and policy linkage |
| Segmented P&L | 8.2 | **10/10** | Multidimensional cube, source lineage, allocation-aware segment results, snapshots and locking |
| True-Ups | 8.5 | **10/10** | Policy/Q1/median/Q3/custom targets, deterministic calculation, batch, reversal and accounting/reconciliation lineage |
| Accounting | 9.1 | **10/10** | Governed journal templates, balanced multi-line journals, validation, posting simulator and reversal/repost lifecycle |
| Exceptions | 8.7 | **10/10** | Case lifecycle, root cause/remediation, waiver controls, automatic reconciliation exceptions and evidence fields |
| Documents / Evidence | 9.1 | **10/10** | Versioned uploads, SHA-256, scoping, tags/expiry/object linkage, indexing and evidence-pack generation |
| Audit | 9.1 | **10/10** | Filterable append-oriented events, correlation/object timelines and transaction-chain reconstruction |
| Approvals | 8.9 | **10/10** | Version-pinned no-code definitions, sequential/parallel groups, delegation, return/reject/withdraw/resubmit, SLA and escalation |
| Policies | 8.0 | **10/10** | Editable workbench, maker-checker lifecycle, benchmark/journal/workflow linkage, version history and impact analysis |
| Variance | 7.7 | **10/10** | Budget/forecast/target/prior-period/prior-year comparisons; additive EBIT bridge and source-driven volume/price/mix/FX when fields exist |
| Reconciliation | 9.0 | **10/10** | Stage reconciliation, configurable tolerance, exception generation and controlled certification |
| Security | 7.6 | **10/10 internal practicality** | Backend RBAC/scoping plus hashed, entity-scoped service-account credentials and security tests; external IdP/pentest remain external gates |
| Qualification | 7.8 | **10/10 qualification-layer practicality** | Persistent evidence registry, release-report synchronization and strict PASS/FAIL/NOT RUN/EXTERNAL distinction |

## External gates that are deliberately not self-certified

- Live SAP / Oracle / Dynamics customer qualification
- Customer OIDC/SAML/Entra/Okta validation
- Independent penetration test
- Customer Finance UAT / TP UAT
- Parallel production close
- Production DR exercise / infrastructure sign-off

These do not reduce the practicality of the Qualification Center itself: its purpose is precisely to represent these gates truthfully rather than turn them into decorative PASS labels.
