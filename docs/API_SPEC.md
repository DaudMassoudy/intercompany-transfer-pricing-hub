# API Specification

Base: `/api/v1`

- `GET /health` - runtime/version health.
- `POST /auth/login` - demo credential exchange.
- `GET /dashboard` - control-tower KPIs and entity status.
- `GET /entities` - entity master.
- `GET /entities/{code}` - policy, P&L, forecast and calculation detail.
- `POST /simulations?entity_code=&ic_purchase_delta=` - non-posting price-cost simulation.
- `GET /adjustments` - adjustment queue.
- `POST /adjustments/{id}/submit` - submit proposed adjustment.
- `POST /adjustments/{id}/approve` - human approval step.
- `POST /journals/from-adjustment/{id}` - balanced journal generation.
- `POST /postings/simulate/{journal_id}` - simulated ERP adapter + reconciliation.
- `GET /audit` - latest audit events.
- `GET /ai/explain/{entity_code}` - grounded deterministic explanation.
- `POST /internal/monthly-close` - n8n service endpoint with integration key.
- `POST /internal/workflow-event` - n8n event/audit endpoint.

FastAPI serves interactive OpenAPI docs at `/docs` and schema at `/openapi.json` when the service is running.
