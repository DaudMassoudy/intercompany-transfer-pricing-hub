# Hotfix2: Docker BuildKit EOF / frontend build resilience

This hotfix addresses Windows Docker Desktop runs where the frontend image build fails during `npm install` with an error similar to:

`rpc error: code = Unavailable desc = error reading from server: EOF`

Changes:

- limits Compose build concurrency to one service at a time to reduce Docker Desktop CPU/RAM spikes;
- pre-builds `otp-frontend` separately before the rest of the stack;
- automatically retries the frontend build up to three times;
- checks/recoveries the Docker Desktop Linux engine if it drops during a build;
- keeps npm downloads in a persistent BuildKit cache so retries avoid unnecessary downloads;
- increases npm network retry/timeouts and prefers cached packages;
- uses Next.js standalone runtime output to reduce the final frontend image size;
- distinguishes image-build failures from API/PostgreSQL runtime failures in diagnostics;
- preserves named Docker volumes throughout recovery and retries.

No database reset or volume deletion is performed by the launcher.
