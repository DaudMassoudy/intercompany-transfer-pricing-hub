# Backup / Restore Test Report — v2.0.0-rc.1

The release contains one-click Windows scripts that:

- dump PostgreSQL;
- archive MinIO object data;
- archive n8n state;
- copy workflow sources and environment metadata;
- generate a timestamped backup manifest;
- generate SHA-256 checksums for backup artifacts;
- verify checksums before restoration.

Static script review and release packaging checks pass.

A real container-volume destruction → restore → data comparison exercise cannot be executed on this build host because Docker is unavailable. Therefore **production DR/restore qualification remains pending**, rather than being falsely reported as PASS.
