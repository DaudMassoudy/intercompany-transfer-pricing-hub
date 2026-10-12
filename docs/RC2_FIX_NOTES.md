# RC.2 Fix Notes

## Primary fix
- `START_DEMO.bat` and `START_OTP.bat` now call `scripts\ensure_docker_desktop.bat`.
- If Docker Desktop is installed but not already running, the launcher attempts to start it automatically and waits up to 180 seconds for `docker info` to become ready.

## Additional hardening
- `BACKUP_OTP.bat` and `VALIDATE_RC.bat` use the same Docker readiness helper.
- `STATUS_OTP.bat` and `STOP_OTP.bat` now fail more gracefully when Docker Desktop is not running.
- Fixed stale `RC.8` wording in `START_OTP.bat`.
- Updated compose project isolation from `enterprise-otp-demo-200rc1` to `enterprise-otp-demo-200rc2`.
