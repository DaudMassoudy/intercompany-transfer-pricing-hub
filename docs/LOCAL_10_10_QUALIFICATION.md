# Local 10/10 Practicality Qualification

The v2.4.0-rc.3 package contains a one-click Windows qualification harness:

`QUALIFY_10_10.bat`

It is designed for the final runtime evidence that cannot be honestly generated in an environment without Docker Desktop and a graphical browser runtime.

## What it executes

1. Starts the actual OTP Docker stack through the hardened `START_DEMO.bat` path.
2. Reuses the dynamically selected application/API ports.
3. Runs the full backend regression suite with measured coverage in an isolated test container.
4. Runs the release/package validator.
5. Runs Chromium through Playwright against the actual local frontend.
6. Runs live API UAT for each of the 15 target layers against the actual local FastAPI/PostgreSQL stack.
7. Generates `qualification/results/LOCAL_10_10_QUALIFICATION.md`.
8. Synchronizes the generated evidence into the in-app Qualification Center.

## Strict scoring rule

A layer is printed as **10/10** only when all of the following pass locally:

- its operator-facing browser workbench check;
- its layer-specific live API business-flow test;
- backend regression tests;
- release validation;
- real Docker application startup;
- frontend runtime health.

If any mandatory check fails, the layer is shown as **NOT QUALIFIED**, never as a cosmetic 10/10.

## Target layers

Master Data; Allocation; Benchmarks; Segmented P&L; True-Ups; Accounting; Exceptions; Documents / Evidence; Audit; Approvals; Policies; Variance; Reconciliation; Security; Qualification.

## External qualification

Live customer ERP qualification, customer IdP integration, independent penetration testing, customer Finance/TP sign-off, parallel production close and production DR remain external gates. They are not fabricated by the local practicality test.
