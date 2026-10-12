# User Acceptance Scenarios — v2.0.0-rc.1

Status reflects what this package can substantiate today; it is not a declaration that customer UAT has occurred.

| ID | Scenario | RC.1 readiness | Notes |
|---|---|---|---|
| A | Onboard ES01 entirely from UI | **Ready for legal entity + governed master flow** | Entity Master supports create/approval; full dependent company configuration across every domain still needs broader orchestration |
| B | Bulk-import 20 entities from Excel | **Ready** | Existing entity master preview/staging; absent rows are non-destructive |
| C | Upload ERP financial data | **Ready for CSV/XLSX** | Live ERP connector is external/open |
| D | Resolve 15 unmapped records | **Partial** | Mapping/validation foundations exist; richer unresolved-record workbench remains a gap |
| E | Create multi-stage IT allocation | **Partial** | Configurable rule/stage metadata exists; unlimited controlled stage execution is not complete |
| F | Exclude shareholder cost | **Ready in allocation simulation/execution** | Exclusion category and amount supported |
| G | Apply weighted Headcount/Payroll driver | **Ready** | Automated 60/40 composite-driver test passes |
| H | Calculate segmented DE01 P&L | **Ready within current imported-P&L model** | Existing P&L tests retained |
| I | Run forecast | **Ready within current forecast model** | Full planning-version workbench is partial |
| J | Explain variance | **Ready for deterministic EBIT bridge** | Full requested driver catalog remains partial |
| K | Goal-seek transfer price | **Ready within current simulation service** | Multi-entity/SKU UX remains partial |
| L | Create true-up | **Ready within current true-up flow** | Full product/SKU/batch lifecycle remains partial |
| M | Complete maker-checker approval | **Ready** | Entity/master-data/critical approval controls demonstrated |
| N | Generate multi-line journal | **Ready within current accounting model** | Generic journal-template designer is partial |
| O | Post through ERP simulator | **Ready for simulator** | Must not be represented as live SAP qualification |
| P | Reconcile final P&L | **Ready within current reconciliation model** | Full automatic exception chain can be deepened |
| Q | Generate audit evidence pack | **Partial** | Audit/evidence foundations exist; fully linked one-click pack across every layer needs more work |

## Acceptance rule

A scenario should be signed off only after a named UAT tester records input data, expected result, actual result, evidence, defects and approval. `Ready` above means the software path exists; it does not replace formal UAT.
