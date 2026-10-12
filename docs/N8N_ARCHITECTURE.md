# n8n Architecture

n8n orchestrates **when / where / what next**; FastAPI owns financial truth.

```mermaid
flowchart LR
  Trigger[Schedule / Webhook] --> N[n8n]
  N -->|X-Integration-Key| API[FastAPI Internal API]
  API --> Calc[Deterministic TP Engine]
  API --> DB[(PostgreSQL)]
  API --> Audit[Audit Event]
  N --> Notify[Email / Teams / ERP adapters - future]
```

The seven shipped workflow JSON files are version-controlled and contain no plaintext credential values. They reference the n8n environment integration key.
