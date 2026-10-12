# Independent Penetration Test Scope

Minimum production scope:

- Authentication/session management, lockout and revocation.
- RBAC/ABAC and entity/workspace authorization.
- IDOR / tenant-crossing attempts across every material object type.
- Import/upload validation and malicious-file handling.
- SQL injection, XSS, CSRF, SSRF and request smuggling where applicable.
- API rate limits and brute-force resistance.
- n8n credential/workflow exposure and webhook authorization.
- object storage access controls.
- ERP adapter authorization/idempotency/replay behavior.
- audit-log tampering attempts.
- AI/RAG prompt injection and unauthorized retrieval when AI providers are enabled.
- infrastructure/container/network configuration on the target environment.

Release rule: no unresolved Critical or High findings before customer production go-live unless formally accepted under the customer's risk process.
