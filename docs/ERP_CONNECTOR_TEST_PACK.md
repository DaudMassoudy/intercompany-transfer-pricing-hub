# ERP Connector Test Pack — v2.0.0-rc.1

## Current connector status

The release implements an `ERPConnector` abstraction and a deterministic `SimulatedSAPConnector` for contract/demo testing. A separate `SAPS4ConnectorContract` explicitly returns qualification `PENDING` and refuses live posting operations until real credentials/implementation are supplied.

The simulator is never represented as a live SAP connection.

## Live SAP S/4HANA sandbox qualification procedure

1. Provision least-privilege sandbox technical identity and approved endpoint/API/OData mechanism.
2. Configure secret reference outside source code.
3. Validate `health_check` and certificate/TLS trust.
4. Pull entity/master data and reconcile record counts.
5. Pull a controlled GL period and reconcile control totals to SAP.
6. Validate counterparty/profit-center/material mapping.
7. Post one low-value test journal with a unique idempotency key.
8. Confirm returned SAP document number/status.
9. Repeat the same request and prove duplicate posting is prevented.
10. Trigger a designed SAP rejection and prove error state/exception workflow.
11. Correct and retry the rejected journal.
12. Execute reversal and verify reversal document/status.
13. Reconcile approved adjustment → journal → SAP posting → resulting SAP P&L.
14. Run authorization, timeout and connectivity-failure tests.
15. Execute volume/batch posting tests agreed with Finance/IT.
16. Record screenshots/logs/document IDs in a signed ERP UAT pack.

## Qualification status

**LIVE ERP SANDBOX QUALIFICATION = PENDING** because this build environment has no customer SAP/Oracle/Dynamics credentials or sandbox.
