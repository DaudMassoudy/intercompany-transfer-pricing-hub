# System Context — v2.0.0-rc.1

```mermaid
flowchart LR
  Tax[Group Tax / TP] --> Hub[Intercompany Transfer Pricing Hub]
  Finance[Finance / Controlling] --> OTP
  Audit[Audit / Reviewer] --> OTP
  ERP[SAP / Oracle / Dynamics / Excel] --> N8N[n8n Orchestration]
  N8N --> OTP
  OTP --> ERP
  OTP --> DMS[Object Storage / DMS]
  OTP --> AI[Approved AI Provider / Local AI]
```

The Intercompany Transfer Pricing Hub is the controlled execution layer between approved TP policy and accounting outcomes. File-based ERP ingestion is implemented. Live ERP write-back remains an adapter qualification boundary; v2.0.0-rc.1 ships an explicitly simulated SAP connector plus production connector contract.
