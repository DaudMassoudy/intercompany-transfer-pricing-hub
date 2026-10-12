# v2.4.0-rc.3 Docker/WSL Startup Hotfix

This hotfix addresses a Windows Docker Desktop failure mode where the Docker CLI exists but the Linux engine returns errors such as:

`500 Internal Server Error ... DockerDesktopLinuxEngine/v1.54/... check if the server supports the requested API version`

## Improvements

- Adds a Docker engine health guard before Docker Compose operations.
- Automatically starts Docker Desktop when needed.
- On the named-pipe/API-500 failure, first performs a targeted recovery of Docker's own `docker-desktop` WSL distribution.
- If targeted recovery fails and no unrelated WSL distribution is running, performs a safe full `wsl --shutdown` recovery automatically.
- Avoids shutting down an active Ubuntu/other WSL session.
- Retries PostgreSQL preflight and Compose startup once when the failure is specifically caused by the Docker engine dropping.
- Suppresses misleading/spammy Compose diagnostics when the Docker engine itself is unavailable.
- Adds `REPAIR_DOCKER.bat` for one-click Docker engine recovery.
- Shows Docker build output by default so long frontend dependency/build steps no longer look frozen.
- Adds npm fetch retry/timeout settings so a broken npm/network request fails in a bounded time instead of appearing to hang indefinitely.
- Adds frontend/backend `.dockerignore` files to reduce Docker build context size.

## Normal use

Double-click `START_DEMO.bat`.

If Docker Desktop is in the API-500 state, the launcher will attempt recovery automatically. If manual recovery is ever needed, double-click `REPAIR_DOCKER.bat` and then retry `START_DEMO.bat`.

Persistent Docker volumes are not deleted by the recovery logic.
