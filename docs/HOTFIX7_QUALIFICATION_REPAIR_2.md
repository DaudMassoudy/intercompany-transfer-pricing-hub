# Hotfix 7 Qualification Repair 2

This repair updates the local 10/10 qualification harness after the first successful Hotfix 7 runtime execution exposed two harness incompatibilities.

## 1. Rerunnable import qualification
The live P&L qualification previously attempted to re-import the same immutable qualification source file and treated the platform's intentional HTTP 409 duplicate-import control as a failure. The qualification now preserves that production control and, when the exact validated batch already exists, resolves the returned `existing_import_code` and reuses that governed source import for downstream mapping/P&L qualification.

## 2. Security UI qualification
Hotfix 7 replaced comma-separated permission/entity fields with governed checkbox and entity selectors and renamed the action to **Create governed account**. The browser qualification still targeted the pre-Hotfix-7 controls. It now validates the current governed selectors and waits for the administrative control to become enabled after `/auth/me` resolves.

No production duplicate-import control, authorization rule, financial calculation, or accounting behavior was weakened by these changes.
