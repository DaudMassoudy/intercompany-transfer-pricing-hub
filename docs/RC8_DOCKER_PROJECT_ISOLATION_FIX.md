# RC.8 Docker Project Isolation Fix

RC.7 contained a stale Compose project identifier (`enterprise-otp-demo-100rc5`) in both `docker-compose.yml` and the demo environment generator. On Windows, a fresh RC.7 extraction could therefore attach to an older RC.5 PostgreSQL volume. Because each release generates randomized database credentials, the API could then fail its startup migration/readiness check while PostgreSQL itself remained healthy.

RC.8 fixes this by:

- using `enterprise-otp-demo-100rc10` as the dedicated Compose project;
- forcing that project identity in `START_DEMO.bat`;
- validating both `DEMO_RELEASE_ID` and `COMPOSE_PROJECT_NAME` before reusing `.env`;
- regenerating incompatible local demo configuration automatically;
- preserving older release volumes rather than deleting them;
- keeping dynamic host-port fallback for side-by-side release testing.

A fresh RC.8 extraction therefore uses isolated PostgreSQL, Redis, MinIO, n8n and application volumes and cannot silently reuse RC.5/RC.7 persistent state.
