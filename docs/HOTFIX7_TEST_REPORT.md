# Hotfix 7 Test Report

**Release:** `2.4.0-rc.3-hotfix7`

## Executed in build environment

### Backend regression suite

Command:

```text
cd backend && pytest -q
```

Result:

- **121 passed**
- **0 failed**
- **1 deprecation warning** in a pre-existing test using `datetime.utcnow()`

Hotfix 7 adds regression coverage for:

- reviewable Master Data changes and return-for-rework
- deterministic true-up policy preview
- multi-dimensional Data Quality readiness
- dedicated integration administration and contract-test history
- runtime-health / external-qualification separation

### Frontend source/import validation

Command:

```text
python scripts/frontend_source_check.py
```

Result: **PASS**

### Static release/package validation

Command:

```text
python scripts/release_validate.py
```

Result: **PASS** for `2.4.0-rc.3-hotfix7`.

Validated controls include required files, transient-artifact exclusion, runtime DB exclusion, secret packaging, JSON/n8n structure, Docker Compose parsing/pinning, dynamic ports, database credential preflight, dependency pinning, version consistency, localisation, governed master data, allocations, benchmarks, workflows, accounting/reconciliation, evidence packs, audit reconstruction, sample XLSX/PDF integrity and qualification-harness integrity.

## Not executed in this build environment

The build environment does not provide the Docker executable, so the live Docker Compose + Playwright qualification harness could not be executed here. The one-click `QUALIFY_10_10.bat` / PowerShell qualification infrastructure remains packaged and release validation confirms its structure.

Run `QUALIFY_10_10.bat` on the target Windows/Docker Desktop environment to produce current runtime/browser evidence for Hotfix 7.
