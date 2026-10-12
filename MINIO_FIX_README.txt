MINIO REGISTRY FIX - local demonstration

The previously configured Quay image returns 401 UNAUTHORIZED.
Patched: scripts/generate_demo_env.ps1, scripts/ensure_release_env.bat, docker-compose.yml, .env.example
Replacement: dappros/minio:RELEASE.2025-09-07T16-13-09Z

1. Extract this archive into a NEW folder.
2. Start Docker Desktop.
3. Double-click START_OTP.bat.
4. If already running this same version, .env is amended to the new image without resetting secrets.

Security: the replacement image is a third-party mirror, not officially maintained by MinIO.
Verify image provenance before production use. This is a local demo workaround.
The image was not pulled or runtime-tested in the archive creation environment.
Do not run docker compose down -v unless you deliberately want to delete volumes.
