# 2.4.0-rc.3-hotfix5 — Qualification timing and sequencing hotfix

This hotfix is based on the retained Playwright artifacts from the Hotfix 4 run.

## Changes

- Keeps ordinary live API calls bounded at 30 seconds.
- Gives genuinely long-running data operations (file import, mapping execution and authoritative P&L build) a bounded 180-second request timeout.
- Gives only the Segmented P&L end-to-end test a 300-second test budget; the normal Playwright test budget remains 90 seconds.
- Increases assertion timeout moderately to 15 seconds for slower Windows/Docker Desktop hosts.
- Corrects Qualification Center sequencing: browser UAT verifies synchronization and static release gates while runtime evidence is still being produced; final runtime PASS/FAIL evidence continues to be synchronized after report generation in step 7/7.
- Aligns executable/current release markers to `2.4.0-rc.3-hotfix5`.

These limits are intentionally finite. They accommodate CPU/disk contention on local Docker Desktop without hiding genuinely stalled operations behind unlimited waits.
