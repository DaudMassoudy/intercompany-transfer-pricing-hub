# Release Gates — v2.0.0-rc.1

1. **Data** — source/control totals, invalid row tracking, mapping coverage, no silent row loss.
2. **TP Engine** — Decimal precision, golden calculations, versioned manifests.
3. **Segmentation / Allocation** — mapping/segment lineage and zero unexplained allocation residual.
4. **Operational TP** — YTD/YTG, simulation, true-up, exception/variance foundation.
5. **Governance** — multi-level approvals, segregation of duties, audit and policy versioning.
6. **Accounting** — balanced journal, duplicate prevention, posting state and reconciliation.
7. **n8n** — workflow JSON/version structure internally validated; live container execution is target-host qualification.
8. **Security** — internal auth/authorization/secret controls validated; external pen/IdP qualification pending.
9. **Reliability** — local performance and backup-script integrity validated; target-scale/DR external.
10. **Package** — source/package integrity and release validators must pass; Windows/Docker runtime must be confirmed on target host.

The RC is promoted to customer Production Qualified only after applicable external gates in `EXTERNAL_QUALIFICATION_REQUIRED.md` pass.
