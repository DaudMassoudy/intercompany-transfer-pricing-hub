# Security Report — v2.4.0-rc.3

QUALIFICATION_STATUS: NOT RUN
## Implemented internal controls

- Backend permission enforcement; UI navigation is not the security boundary.
- Workspace and entity access checks.
- Login throttling / lock behavior retained.
- Service-account tokens use a one-time raw credential; only SHA-256 digest is persisted.
- Service accounts carry explicit permissions and entity scopes.
- Revocation and optional expiration supported.
- Document and evidence access remains entity scoped.
- RAG/evidence architecture retains permission-first design.
- Secrets are supplied via release environment/credential references rather than exposed in frontend payloads.

## External qualification

The following are **EXTERNAL QUALIFICATION REQUIRED**, not PASS:

- customer OIDC/SAML/Entra/Okta configuration validation;
- independent penetration test;
- external vulnerability assessment against deployed infrastructure.