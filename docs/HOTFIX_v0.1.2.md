# v0.1.2 Hotfix — MinIO Registry

## Reported failure
Docker Compose failed before application startup while pulling `minio/minio:latest`, returning a pull-access-denied/repository-not-found error.

## Root cause
The previous Compose file referenced the Docker Hub `minio/minio` repository. MinIO's current published container quickstart uses `quay.io/minio/minio`.

## Fix
- Default image changed to `quay.io/minio/minio:latest`.
- Image name is configurable through `MINIO_IMAGE` so an enterprise/private mirror can be used without editing Compose.
- No OTP application data model or calculation logic changed.

## Upgrade
Extract v0.1.2 to a new folder and run `START_DEMO.bat`.
