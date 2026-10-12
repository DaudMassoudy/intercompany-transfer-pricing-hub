# RC.3 Fix Notes

## Fixed launcher blocker
RC.2 expected `DEMO_RELEASE_ID=2.0.0-rc.2` but `generate_demo_env.ps1` still generated the RC.1 identifiers. The generated `.env` was therefore rejected immediately.

RC.3 makes the launcher, environment generator, Compose project, API/frontend version markers and validation scripts consistent at `2.0.0-rc.3` / `enterprise-otp-demo-200rc3`.

## Windows compatibility
The secret generator now uses `RandomNumberGenerator.Create().GetBytes(...)`, compatible with Windows PowerShell 5.1, instead of relying on the static `RandomNumberGenerator.Fill(...)` API.

## Diagnostics
Environment generation and marker failures are no longer suppressed, making launcher errors actionable.
