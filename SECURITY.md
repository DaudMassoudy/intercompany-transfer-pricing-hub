# Security policy

This repository is a **demonstration / portfolio release**, not a qualified production financial system.

- Run only with fictitious data and on trusted development machines.
- Never expose the Docker demo ports to an untrusted network or publicly host the seeded demo accounts.
- Never commit `.env`, tokens, credential-bearing logs, real taxpayer/client data, or generated backups.
- Demo persona passwords in documentation and source are intentionally known and **must not be used in production**.
- The MinIO configuration currently references a third-party mirror because the original Quay.io image returned HTTP 401. Its provenance is **not independently verified**; use an approved, digest-pinned image for sensitive environments.
- This repository has not undergone an independent penetration test, third-party compliance audit, or live ERP qualification.

If you identify a vulnerability, please avoid posting exploit details publicly. Contact the repository maintainer privately through the GitHub profile associated with the repository.
