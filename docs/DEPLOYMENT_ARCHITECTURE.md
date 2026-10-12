# Deployment Architecture

Local demo uses Docker Compose with persistent volumes:

- `otp-frontend`
- `otp-api`
- `otp-worker`
- `otp-postgres`
- `otp-redis`
- `otp-minio`
- `otp-n8n`

`START_DEMO.bat` checks Docker, creates `.env`, builds/starts services, waits for API/n8n health, imports workflow assets and opens the browser. Production should move stateful services to managed equivalents and add TLS, enterprise identity, centralized logging and HA.
