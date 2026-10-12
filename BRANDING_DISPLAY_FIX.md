# Branding and language switch fix

## What changed
- `frontend/Dockerfile`: copies `/app/public` into the Next.js standalone runtime image, so `/tp-arrow-mark.svg` now resolves instead of showing broken-image alternate text.
- `frontend/app/globals.css`: fixes sidebar logo dimensions and adds a stable, full-width DE/EN segmented switch.
- `frontend/app/login/page.tsx`: replaces the cramped inline heading layout with a responsive CSS grid.
- Existing TP Arrow Mark artwork, favicon, theme, business logic and MinIO mirror configuration are preserved.

## Running on Windows
Unzip to a new folder. Open Docker Desktop and run `START_OTP.bat`. Rebuilding the frontend image is necessary: `docker compose build --no-cache otp-frontend` (use the correct service name from `docker compose config --services`), then restart if an old image remains cached. Hard-refresh Firefox using Ctrl+Shift+R.

The container startup was not executed in this environment.
