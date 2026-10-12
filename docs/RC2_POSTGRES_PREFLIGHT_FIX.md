# v2.4.0-rc.3 PostgreSQL first-start preflight fix

## Symptom fixed
On a fresh Windows/Docker installation the launcher could stop at:

`[ERROR] Could not synchronize the PostgreSQL role password.`

## Root cause
The previous preflight used `pg_isready` as its initialization gate. During the official PostgreSQL container's first initialization, `pg_isready` can observe the temporary initialization server before the configured application database is fully available. The launcher could then attempt `ALTER ROLE` during that transition and fail even though Docker and the generated credentials were valid.

## Fix
- waits for an actual `SELECT 1` against the `postgres` database rather than only `pg_isready`;
- retries credential synchronization through the local administrative socket;
- executes the role change against `postgres`, avoiding the application-database creation race;
- waits separately for the `otp` database and verifies the exact TCP/password path used by SQLAlchemy;
- stores unsuppressed diagnostics in `logs/postgres_preflight.log`;
- never deletes the PostgreSQL volume as part of automatic repair.

`RESET_DEMO.bat` remains a manual last-resort operation for disposable demo data only.
