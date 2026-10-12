# Security Architecture

```mermaid
flowchart TB
  Browser -->|Bearer token| API[FastAPI]
  N8N[n8n] -->|Integration key| API
  API --> DB[(PostgreSQL)]
  API --> OBJ[(S3/MinIO)]
  API --> AUDIT[Audit Log]
```

Demo authentication uses PBKDF2-SHA256 password hashing and an HMAC-signed expiring session token. Production qualification requires enterprise OIDC/SAML, MFA, tenant-scoped RLS/ABAC, TLS termination, external secrets management, CSP/export hardening and independent penetration testing.
