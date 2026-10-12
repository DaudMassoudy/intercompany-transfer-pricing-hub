# RC.5 Fix Notes

## Startup defect fixed
The RC.4 `START_OTP.bat` path invoked the PostgreSQL credential preflight before loading secrets from `.env`. This caused:

`[ERROR] OTP_DB_PASSWORD is not loaded into the launcher environment.`

RC.5 fixes this in two layers:

1. `START_OTP.bat` explicitly calls `scripts\load_compose_secrets.bat` immediately after release-environment validation and before database preflight.
2. `scripts\sync_postgres_credentials.bat` now self-loads the release secrets from `.env` whenever `OTP_DB_PASSWORD` is not already defined, making the preflight safe when invoked from any launcher.

## Regression prevention
`release_validate.py` now checks the ordering in `START_OTP.bat` and verifies the self-loading fallback in the database preflight script.
