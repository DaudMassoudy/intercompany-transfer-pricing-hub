# 2.4.0-rc.3-hotfix3 — Qualification repeatability hotfix

This hotfix keeps the authoritative P&L allocation prerequisite intact while making the local qualification repeatable.

- stale `Q10AL*` qualification-only active rules are deactivated at qualification start; business/demo rules are not touched;
- the seeded `ALLOC-HQ-IT-001` rule receives a completed 2026-09 controlled run when needed before authoritative P&L publication;
- release/version markers are synchronized to `2.4.0-rc.3-hotfix3`;
- Qualification UI/API assertions use the package release version;
- `START_DEMO.bat` control flow is repaired and retains visible low-concurrency Docker build progress.
