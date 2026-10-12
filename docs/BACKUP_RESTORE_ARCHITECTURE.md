# Backup / Restore Architecture

`BACKUP_OTP.bat` captures:

- PostgreSQL logical dump
- MinIO data volume archive
- n8n state archive
- environment backup
- versioned workflow source
- backup manifest

`RESTORE_OTP.bat` requires explicit confirmation and restores database plus available service archives. Production qualification still requires encrypted off-host storage, automated schedules and restore/DR testing against stated RPO/RTO.
