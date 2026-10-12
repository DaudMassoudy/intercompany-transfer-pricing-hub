# Requirement Traceability Matrix — v2.4.0-rc.3

| ID | Layer | Requirement | Frontend/API/Service evidence | Automated evidence |
|---|---|---|---|---|
| MD-10 | Master Data | dependency/impact protection | master-data workbench + catalog dependency resolver | master catalog regression tests |
| AL-10 | Allocation | arbitrary multi-stage/cycle/composite/recipient controls | Allocation Workbench + allocation service | allocation regression suite |
| BM-10 | Benchmarks | comparable observations + deterministic quartiles | Benchmarks UI/API + benchmark service | benchmark tests |
| PL-10 | Segmented P&L | cube/snapshot/lock/source lineage | `/pnl/runs/{id}/cube`, snapshot APIs + P&L UI | P&L snapshot/control tests |
| TU-10 | True-Ups | deterministic targets/batch/reversal | `/true-ups`, `/true-ups/batch`, `/reverse` + UI | practicality tests |
| AC-10 | Accounting | governed template-driven balanced journals | journal routes/services + UI/master-data templates | accounting tests |
| EX-10 | Exceptions | triage/remediation/waiver + automatic creation | exception UI/APIs + reconciliation hook | reconciliation/exception tests |
| DE-10 | Documents | version/hash/linkage/evidence pack | document repository + evidence-pack endpoint | document/evidence tests |
| AU-10 | Audit | object/transaction/correlation reconstruction | audit explorer + transaction-chain API | audit regression tests |
| WF-10 | Approvals | versioned sequential/parallel/delegation/return/escalate | Workflow Center + workflow-engine APIs | workflow tests |
| PO-10 | Policies | editable lifecycle/version/impact | Policy Workbench + practical10 policy APIs | policy lifecycle tests |
| VA-10 | Variance | multiple baselines + additive/source drivers | Variance UI + variance service | variance service tests |
| RE-10 | Reconciliation | stage/tolerance/exceptions/certification | Reconciliation Control Center | reconciliation tests |
| SE-10 | Security | scoped service identity and backend enforcement | Security Admin + security.py | service-account authorization test |
| QU-10 | Qualification | persistent evidence-backed current-release controls | Qualification Center + sync/evidence APIs | qualification sync test |
