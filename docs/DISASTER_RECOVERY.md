# Disaster Recovery Plan

Target architecture objectives: RPO ≤ 24 hours and RTO ≤ 4 hours until a customer defines stricter objectives.

Recovery order: infrastructure/network → PostgreSQL → object storage → Redis/workers → API → n8n → frontend → integrations. Restore must verify backup checksums, DB migration version, document hashes, workflow state and a deterministic DE01 golden calculation before service is reopened.

Production qualification requires a real target-infrastructure DR exercise with measured RPO/RTO.
