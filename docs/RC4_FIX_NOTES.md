# RC.5 Fix Notes — PostgreSQL authentication self-healing

## Incident fixed
Windows Docker startup could reach a healthy PostgreSQL container while `otp-api` failed with:

`FATAL: password authentication failed for user "otp"`

Two conditions could cause this:

1. Docker Compose interpolation can be overridden by a same-named Windows/system environment variable, while `env_file: .env` still gives the API a different `DATABASE_URL`.
2. A persistent PostgreSQL volume retains the role password created on first initialization. Regenerating `.env` later does not automatically change that role password.

The old `pg_isready` healthcheck also did not authenticate, so it could report PostgreSQL as healthy despite invalid API credentials.

## RC.5 controls
- `scripts/load_compose_secrets.bat` explicitly loads release secrets from the generated `.env` into the launcher process, overriding conflicting Windows environment values for this process only.
- `scripts/sync_postgres_credentials.bat` starts PostgreSQL separately, reapplies the `.env` password to role `otp` through the local administrative socket, then verifies the exact TCP/password path used by SQLAlchemy.
- The API and worker explicitly receive a Compose-resolved `DATABASE_URL` derived from the same `OTP_DB_PASSWORD` as PostgreSQL.
- PostgreSQL health now performs an authenticated SQL `SELECT 1`, not just `pg_isready`.
- Existing PostgreSQL data is preserved; the launcher does not delete the volume to repair credentials.
- `RESET_DEMO.bat` remains the explicit destructive last-resort path for disposable demo data.
