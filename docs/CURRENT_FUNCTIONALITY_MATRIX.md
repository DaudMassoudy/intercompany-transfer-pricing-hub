# Current Functionality Matrix — v2.4.0-rc.3

Evidence-based status after upgrading the supplied v2.0.0-rc.5 baseline. `10/10` is not used where a mandatory exit gate remains unverified.

| Layer | Status | Practicality | Principal evidence | Remaining limitation |
|---|---|---:|---|---|
| Master Data | Working | 9.0 | Governed catalog, maker-checker, versioning, effective dates, bulk preview/import, operational projections; added benchmark/DQ/workflow/journal-template domains | Not every domain has a dedicated relational projection/impact engine |
| Data Import | Working | 7.2 | CSV/XLSX ingestion, hashes, raw/normalized rows, controls | Live enterprise connectors and full schema wizard incomplete |
| Data Quality | Partial+ | 7.2 | Existing import controls plus governed user-maintainable DQ rule definitions | Configured rule definitions are not yet a universal runtime rules engine |
| Mapping | Working | 7.2 | Versioned rules, run, coverage/conflicts | Full nested no-code AND/OR rule builder incomplete |
| Segmentation | Partial | 6.5 | TP segment master and P&L segmentation foundations | Full hierarchy designer/compare/re-parent UX incomplete |
| Allocation | Working | 8.5 | Configurable pools/rules, exclusions, composite drivers, lifecycle, simulation, execution, reconciliation | Unlimited multi-stage execution still incomplete |
| Segmented P&L | Working | 8.0 | Authoritative build, lineage, drilldown, policy result | Lock/snapshot UX and full multidimensional designer incomplete |
| Policies | Working | 7.7 | Multiple methods/PLIs, target/range fields, benchmark assignment | Full editable lifecycle workbench incomplete |
| Benchmarks | Working+ | 8.0 | New governed benchmark domain, versioning, expiry status, policy assignment, maker-checker | Comparable-company row-level financial workbench/API provider adapter incomplete |
| Control Tower | Working | 7.5 | KPI/dashboard foundations | User dashboard designer/saved widget layouts incomplete |
| Forecasting | Working | 7.0 | Forecast versions and policy-aligned PLI | Full assumptions/override approval workbench incomplete |
| Variance | Working | 7.5 | Deterministic bridge and residual control | Requested driver decomposition not complete for all categories |
| Simulation | Working | 7.5 | Goal-seek/scenario logic and persisted simulations | Multi-entity/SKU scenario portfolio incomplete |
| True-Ups | Working | 8.0 | Adjustment/approval/accounting chain | Batch SKU-level supersession/reversal depth incomplete |
| Approvals | Working | 7.8 | Maker-checker on core objects; governed workflow definitions added | Generic executable workflow designer with delegation/OoO/SLA not complete |
| Accounting | Working | 8.0 | Balanced journals and posting simulator; governed journal-template domain added | Template domain not yet fully consumed by journal generator |
| ERP Posting | Simulator | 6.0 | Adapter contracts/simulator/idempotent posting path | Live SAP/Oracle/D365 qualification unavailable |
| Reconciliation | Working | 7.5 | Adjustment/journal/posting reconciliation | Universal chain-level automatic exception creation incomplete |
| Exceptions | Working+ | 8.0 | New create/update lifecycle, resolution rules, ownership/evidence fields, audit | SLA automation/reminders/bulk actions still limited |
| Documents/Evidence | Working+ | 8.0 | New versioned upload/download, SHA-256, supersession, entity scope, deterministic text indexing/search | PDF extraction/object-store provider/evidence-pack builder incomplete |
| AI/RAG | Partial | 6.5 | Advisory/evidence-grounding constraints and AI invocation model | Production vector retrieval/evaluation suite incomplete |
| Audit | Working | 8.0 | Audit events and governed histories | Stronger append-only external assurance still required |
| Integrations | Working+ | 7.0 | New connection creation, secret references, explicit contract simulator test, run records | Live endpoint qualification and credential-vault integration incomplete |
| n8n | Working | 7.2 | 7 versioned workflows / 47 nodes and runtime-run visibility | Full retry/human-task runtime validation not executed here |
| Security | Working | 7.5 | JWT/Argon2/RBAC/scopes/security headers | External pen test, production IdP/MFA/SCIM incomplete |
| Administration | Partial+ | 6.5 | Role/user foundations plus governed configuration domains | Unified admin center for all scopes/IdPs/retention/feature flags incomplete |
| Qualification | Working | 7.5 | DB-backed qualification controls and explicit external gates | Live ERP/IdP/UAT/DR remain external validation |
