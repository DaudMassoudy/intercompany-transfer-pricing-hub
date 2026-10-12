# v2.4.0-rc.3 — Local qualification startup/progress fix

## Incident reproduced from Windows screenshot

`QUALIFY_10_10.bat` remained visually at **1/7 Start the real Docker application** while the OTP application was already healthy in the browser. The qualifier always called `START_DEMO.bat`; that launcher deliberately performs a Compose down/up with `--build`, and normal build output was redirected to `logs/launcher.log`. The result looked frozen and needlessly rebuilt a stack that was already running.

## Fix

- The qualifier now resolves the current runtime ports and probes both the frontend and `/api/v1/health/ready`.
- A healthy existing stack is reused immediately; it is **not** stopped, rebuilt, or restarted.
- `START_DEMO.bat` is called only when no healthy runtime exists.
- When the qualifier really must start/build the application, it sets `OTP_SHOW_BUILD_PROGRESS=1`, and Docker build output is shown live.
- Qualification-runner builds use `docker compose --progress plain build`, so first-run Playwright/Python image downloads are visible instead of appearing frozen.
- A fallback reads the actual published Compose ports when `logs/runtime_ports.env` is unavailable.
- Post-start HTTP/API checks confirm that the runtime is usable before qualification continues.

This changes qualification orchestration only; OTP business data and persistent volumes are not reset.
