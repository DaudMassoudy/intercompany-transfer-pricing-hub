# Admin Guide — v2.0.0-rc.1

## Windows one-click operations

- `START_DEMO.bat` — start/reset into the synthetic demonstration mode intended for portfolio walkthroughs.
- `START_OTP.bat` — start the normal local stack while preserving data.
- `START_DEV.bat` — development-oriented start path.
- `STATUS_OTP.bat` — inspect configured stack/services.
- `STOP_OTP.bat` — stop services without intentional data reset.
- `RESET_DEMO.bat` — destructive reset of synthetic demo state only.
- `BACKUP_OTP.bat` / `RESTORE_OTP.bat` — local backup/restore workflow.
- `VALIDATE_RC.bat` — release-package validation.

The Compose project name for this release is isolated as `enterprise-otp-demo-200rc1` so it does not silently reuse the RC.10 project namespace.

## Database migrations

Alembic head is `0007_configurable_core`. The migration adds enterprise master-data governance tables, operational master activation flags, and expanded AllocationRule configuration. Apply migrations using the backend Alembic configuration in a controlled environment; back up production data before schema changes.

## Governed master data

The Master Data Catalog supports the following generic domains: intercompany partners, GL accounts, cost centers, profit centers, plants, business units, product groups, products/SKUs, customers, vendors, currencies, FX sources, transaction types and TP segments. Legal entities retain their dedicated governance module.

Normal flow: Data Steward creates a DRAFT → submits → authorized checker approves/rejects. The maker cannot approve their own request. Approved versions are immutable history. For projected operational domains, only approved changes synchronize into runtime master tables.

## Allocation administration

Allocation rules are business objects, not fixed demo actions. Configure pool name/type, sender, period/currency, source dimensions/mode, driver/driver source, composite weights, recipients, exclusions, markup and FX metadata. Use simulation before execution. Only ACTIVE rules can execute.

## Security notes

Do not reuse demo credentials outside demo mode. Replace all secret placeholders through environment/secret-management controls. External IdP, MFA, production RLS behavior, penetration testing and infrastructure scanning must be qualified in the target environment.

## Release verification

From the project root run `python scripts/release_validate.py`; from `backend` run `pytest -q`. A full frontend `npm run build` and Docker Compose startup should also be mandatory CI/release gates in an environment with dependency/network and Docker access.
