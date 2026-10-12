# Hotfix 6 — deterministic qualification isolation

Version: `2.4.0-rc.3-hotfix7`

Hotfix 6 corrects a qualification-runner sequencing defect discovered during repeated local qualification on Windows/Docker Desktop.

## Root cause fixed

Hotfix 5 executed backend pytest/coverage before release/package validation while bind-mounting the release tree into the qualification container. Pytest could therefore create `backend/.coverage` and `backend/.pytest_cache`. A locally generated runtime `.env` could also legitimately exist after startup. The subsequent package-integrity gate correctly rejected those files, causing release validation to fail even when the clean release package itself was valid. The stale failure was then synchronized to the Qualification Center and caused the release-evidence UI assertion to fail.

## Hotfix 6 controls

- Release/package validation runs before mutable backend regression execution.
- A locally generated `.env` is temporarily moved outside the release tree for package-integrity validation and restored immediately afterward.
- If that `.env` exists, Docker Compose still receives it through `--env-file`; no secrets are copied into the release tree.
- Pytest coverage state is written to `/results/.coverage-local` and pytest cache to `/results/pytest-cache`, not into `backend/`.
- Current-run release validation evidence is written and synchronized before Chromium UAT so the Qualification Center cannot expose stale release-integrity evidence.
- Backend regression, release validation, browser/API UAT, scorecard generation, and final evidence synchronization remain separate mandatory gates.
- External customer/third-party qualification remains explicitly outside local self-certification.

These changes do not weaken release validation. They separate immutable package-integrity evidence from mutable runtime/test evidence so each gate measures the intended subject.

## Runtime version safety

The qualifier reuses an already-running OTP stack only when both health checks pass **and** `/api/v1/health/version` exactly matches `VERSION.txt`. A healthy Hotfix 5 runtime therefore cannot be accidentally used to certify Hotfix 6; the current release is rebuilt/restarted instead.
