# Module Map — v2.0.0-rc.1

| Domain | RC state | Responsibility |
|---|---|---|
| Identity & Access | Implemented RC foundation | Argon2 local auth, JWT expiry/revocation, roles, entity access, production OIDC/SAML-ready configuration |
| Tenancy | Implemented schema/control foundation | Organization → workspace → client → entity; tenant fields and PostgreSQL RLS migration policies |
| Master Data | Implemented | Entities, IC partners, GLs, profit centers, products |
| Imports / DQ | Implemented | CSV/XLSX, SHA-256, schema/row validation, warnings/rejects/control totals |
| Mapping | Implemented | Versioned ERP→TP rules, priority, conflicts, coverage |
| Policies | Implemented | Method/PLI/target/range/benchmark/effective dates/approval matrix |
| Segmented Finance | Implemented data/engine foundation | Raw/normalized records, segment codes, source lineage |
| Allocations | Implemented | Deterministic drivers, runs, results, residual reconciliation |
| TP Engine | Implemented | TNMM PLIs, Cost Plus, Resale, CUP variance, Profit Split, FX, service charging, goal-seek |
| Forecasting | Implemented | Forecast versions + YTD/YTG full-year calculation |
| Simulation | Implemented | Purchase-cost/goal-seek scenario calculation without book mutation |
| Adjustments | Implemented | Proposed/submitted/reviewed/approved lifecycle |
| Approvals | Implemented | Multi-level approval and segregation of duties |
| Journals | Implemented | Header/line accounting model, balance and adjustment controls |
| ERP | RC contract | SAP S/4 interface contract + deterministic simulator; live sandbox external |
| Reconciliation | Implemented | expected/approved/journal/posted/final impact comparison |
| Exceptions | Implemented foundation | Operational and technical exception records |
| Documents/Evidence | Implemented schema foundation | versioned documents/evidence chunks/access metadata |
| AI | Governed advisory foundation | Deterministic grounded explainer and model invocation structures; production RAG external/iterative |
| Audit | Implemented | Actor/role/object/correlation/source audit lineage |
| n8n | Implemented workflow assets | 7 workflows / 46 nodes; live runtime qualification external to build host |
| Observability | Implemented foundation | health/version endpoints, correlation IDs and system-health page |
