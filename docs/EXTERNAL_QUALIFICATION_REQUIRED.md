# External Qualification Required

The software is packaged as an **Enterprise Production Release Candidate**. The following gates require real external systems, people or infrastructure and are therefore intentionally not represented as completed:

1. **Live ERP sandbox certification** — SAP S/4HANA/ECC or the customer's target ERP, including extraction, posting, rejection, retry, reversal and final P&L reconciliation.
2. **Enterprise identity validation** — customer Microsoft Entra ID / Okta / OIDC/SAML tenant, MFA and lifecycle controls.
3. **Independent penetration test** — external assessor; no unresolved Critical/High findings before production.
4. **Independent TP professional sign-off** — supported methods, policy configuration, accounting treatment and golden cases for the customer's facts.
5. **Finance/Accounting UAT** — journal accounts, posting keys, tax codes, currencies, periods, close/reversal procedures.
6. **Parallel close cycles** — normally 2–3 periods comparing the OTP platform against the existing trusted process.
7. **Production-scale performance qualification** — intended PostgreSQL/container/cloud infrastructure with representative 10M+ row volumes and concurrency.
8. **Production backup/restore and DR exercise** — measured RPO/RTO on deployed infrastructure.
9. **Networked SAST/CVE/container/dependency scan** — performed in CI with up-to-date vulnerability feeds.
10. **Operational ownership** — support model, incident response, monitoring/on-call, change/release governance and approved cutover plan.

A real production deployment should not be labelled customer **Production Qualified** until the applicable items above have documented PASS evidence.
