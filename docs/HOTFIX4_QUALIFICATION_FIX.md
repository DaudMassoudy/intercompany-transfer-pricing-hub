# 2.4.0-rc.3-hotfix4 — Qualification determinism and accessibility hotfix

This hotfix addresses the three concrete failures captured by the local Playwright artifacts from hotfix3:

1. **Qualification release identity** — backend `APP_VERSION`, generated `.env`, frontend version and qualification expectations are aligned to `2.4.0-rc.3-hotfix4` so synchronized evidence reports the actual running release.
2. **Security UI accessibility** — service-account fields now have explicit `id`/`htmlFor`, `name`, and `aria-label` associations. Playwright `getByLabel(...)` and assistive technologies can resolve all three fields deterministically.
3. **ERP posting idempotency** — repeated posting of an already reconciled journal now returns the existing posting with `idempotent_replay=true` before enforcing the mutable journal-status gate. The first posting still executes the same validation and simulator path.

Reliability improvements:

- qualification test timeout reduced from 120s to 60s;
- assertion timeout reduced to 10s;
- API qualification calls have a 30s request timeout;
- traces, screenshots and videos remain retained on failure.

No external qualification gate is self-certified by this hotfix.
