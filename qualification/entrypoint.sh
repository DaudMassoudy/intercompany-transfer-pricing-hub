#!/usr/bin/env bash
set -euo pipefail
: "${APP_HOST_PORT:=3000}"
: "${API_HOST_PORT:=8000}"
: "${APP_TARGET:=otp-frontend}"
: "${API_TARGET:=otp-api}"
# Chromium runs in an isolated qualification container. The production
# frontend is compiled to use localhost host-port URLs, so local socat
# listeners preserve the exact browser origin while forwarding over the
# private Compose backplane to the real frontend/API containers.
socat TCP-LISTEN:${APP_HOST_PORT},fork,reuseaddr TCP:${APP_TARGET}:3000 >/tmp/otp-app-socat.log 2>&1 &
socat TCP-LISTEN:${API_HOST_PORT},fork,reuseaddr TCP:${API_TARGET}:8000 >/tmp/otp-api-socat.log 2>&1 &
for i in $(seq 1 60); do
  if curl -fsS "http://localhost:${API_HOST_PORT}/api/v1/health/ready" >/dev/null 2>&1 && curl -fsS "http://localhost:${APP_HOST_PORT}" >/dev/null 2>&1; then
    break
  fi
  sleep 1
  if [ "$i" = "60" ]; then
    echo "Qualification container could not reach otp-frontend/otp-api over the Compose backplane." >&2
    cat /tmp/otp-app-socat.log >&2 || true
    cat /tmp/otp-api-socat.log >&2 || true
    exit 2
  fi
done
export BASE_URL="http://localhost:${APP_HOST_PORT}"
export API_URL="http://localhost:${API_HOST_PORT}/api/v1"
exec npx playwright test
