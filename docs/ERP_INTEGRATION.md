# ERP Integration
The shipped release contains a **simulated ERP posting endpoint**, not a live SAP connector. Production adapters should implement idempotent submit/status contracts for SAP S/4HANA, ECC, Oracle or Dynamics, with explicit source/document identifiers and reconciliation.
