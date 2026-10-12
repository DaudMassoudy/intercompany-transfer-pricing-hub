# User / Role Matrix — v2.0.0-rc.1

This matrix distinguishes implemented application support from the full target role definition.

| Role | Implemented/usable in RC.1 | Still partial / future depth |
|---|---|---|
| Local Finance | ERP file import, validation feedback, source totals, imported P&L/reconciliation foundations, local-finance demo persona | Full source-connector setup, rejected-record correction UI, local journal/posting workbench and local-report designer |
| TP Analyst | Mapping/TP calculations, forecasts, variance, simulations, true-up foundations, configurable allocation create/simulate/execute | Complete transaction/segment designer, all allocation recipient/stage controls, evidence drafting workbench |
| TP Manager | Maker-checker approvals, policy/adjustment review foundations, allocation approval/activation | Generic approval matrix designer, benchmark-expiry/deadline portfolio controls, delegation/SLA capabilities |
| Finance Controller | Journal/posting/reconciliation foundations | Full journal-template UI, posting-failure operations, reversal/repost control center |
| Group Tax Director | Control-tower/global TP concepts, approval/read access foundations | Complete projected-exposure/scenario board reporting and materiality-driven approval matrix |
| Master Data Steward | Legal Entity Master plus enterprise catalog create/edit/deactivate/reactivate/import/version history | Domain-specific relationship management for every master and advanced duplicate/merge controls |
| Auditor | Read-only evidence/audit/qualification foundations | One-click reproducible evidence pack across every chain and immutable external archive |
| Platform Admin / IT | User/role/runtime/system-health foundations | Complete IdP/integration/credential/n8n/retention/backup/service-account UI |
| Executive | Control Tower / management outputs | Configurable executive KPI packs and saved management-report views |

## Maker-checker controls

For enterprise catalog changes, the request creator cannot approve or reject the same submitted request. Approved changes create immutable versions. Operational projections are updated only after approval.
