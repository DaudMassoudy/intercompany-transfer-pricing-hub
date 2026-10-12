# User Guide — v2.0.0-rc.1

## Start and sign in

For the synthetic demonstration, use `START_DEMO.bat`; for a persistent local environment use `START_OTP.bat`. Demo accounts are for demonstration only and must not be treated as production identity configuration.

## Master Data Catalog

Open **Master Data Catalog** from the navigation. Choose a domain, search existing records, create a new record or edit an existing one, provide effective dates and a reason, then save a draft. A draft must be submitted and approved by a different authorized user before it becomes the approved master state. Deactivation/reactivation is also governed through a change request. CSV/XLSX import first produces a preview; missing rows never mean delete/deactivate.

## Allocation Workbench

Open **Allocations** and create a new allocation rule instead of running a fixed demo amount. Configure the cost pool, sender, source amount mode, source GL accounts, driver, recipient values, optional composite-driver weights, markup, currency/FX and effective dates. Submit the draft, have an authorized checker approve it, then activate it.

For an ACTIVE rule, enter the period, source amount where manual input is permitted, recipient driver values (`SEGMENT=VALUE`) and exclusion amounts (`CATEGORY=AMOUNT`). **Simulate** first. Review Original Pool, Exclusions, Eligible Pool, Allocated Amount, Residual, Markup and recipient charges. **Execute** only after the result is reconciled and the rule is ACTIVE. Simulation does not post accounting entries.

## Existing operational modules

Use the Control Tower, imports, mappings, imported P&L, forecasting, variance, simulation, true-ups, approvals, journals/postings, reconciliation, exceptions, audit and qualification screens according to your role. Some modules remain release-candidate depth; consult `FUNCTIONAL_COVERAGE_MATRIX.md` before treating a workflow as production complete.

## Auditability

Use history and approval information to reproduce who proposed and approved master/configuration changes. Do not bypass governed UI/API workflows with direct SQL or seed-file edits for normal business operation.
