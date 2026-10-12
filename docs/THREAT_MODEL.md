# Threat Model
Primary threats: tenant leakage, IDOR, credential theft, malicious spreadsheet/file ingestion, SQL injection, XSS, workflow secret exposure, privilege escalation and AI retrieval leakage. Required mitigations include least privilege, RLS/ABAC, file validation, parameterized ORM, CSP, secret management, audit logs and tenant-scoped retrieval.
