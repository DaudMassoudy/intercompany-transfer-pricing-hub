# Hotfix 7 Release Notes

**Release:** `2.4.0-rc.3-hotfix7`  
**Baseline:** `2.4.0-rc.3-hotfix6`  
**Scope:** Enterprise governance, reviewability, drill-down, role-aware UX, action feedback, qualification integrity and operational health.

## Executive summary

Hotfix 7 upgrades the existing Intercompany Transfer Pricing Hub without replacing its architecture. The release focuses on the weaknesses found during hands-on acceptance testing: blind approvals, non-reactive actions, weak object drill-down, policy/true-up ambiguity, generic permission failures, incomplete evidence delivery, disconnected workflow/approval experiences and configuration-only health indicators.

The release retains deterministic calculation logic, maker-checker controls, version pinning, simulator/live-system separation, audit history and explicit external qualification gates.

## P0 controls implemented

- Reviewable Master Data change requests with field-level before/after diff, dependency impact and return-for-rework.
- In-app notifications for governed submissions and review outcomes.
- True-up preview before creation with applicable policy/version, target, source hash, formula and policy-consistency gate.
- Duplicate true-up proposal protection.
- Approval Review Workspace with policy-consistency blocking and approve/reject/return actions.
- Explicit action feedback for allocation execution and major accounting/governance actions.
- P&L run drill-down and source lineage.
- Role-aware policy administration; inaccessible actions are disabled rather than failing only after click.
- Benchmark context-preserving navigation and explicit Comparable-screening feedback.
- Journal → true-up/policy → ERP posting → reconciliation lineage.
- Reconciliation exception deep links, controlled rebuild confirmation and certification context.
- Exception case workspace replacing browser-native triage prompts with category-aware root-cause selection.
- Multi-dimensional Data Quality readiness instead of a single generic validity percentage.
- Evidence downloads return the governed artifact using meaningful filenames.
- Audit object/correlation drill-down.
- Dedicated service-account and integration-administration permissions.
- Service-account governed permission/entity selectors and one-time credential handling.
- Workflow Designer deep-links directly to Workflow Definitions; workflow task review is no longer a blind row action.
- Workflow ordered-step grammar is exposed professionally in the governed definition editor.
- Qualification controls/evidence are release-pinned and drillable.
- Redis, MinIO and n8n now receive runtime health probes rather than merely being labelled `CONFIGURED`.

## P1 UX / governance improvements

- Signed-in user and role are visible in the global shell.
- Consistent Back / Forward controls and context breadcrumb strip.
- Global notification center with unread state.
- Clickable import IDs with SHA-256, control totals and row-level issues.
- Clickable variance run IDs and permission-aware Run action.
- Integration detail and contract-test history.
- Workflow instance timeline detail.
- Qualification release summary clearly separates internal qualification from external production gates.
- System Health shows runtime status, check timestamp, latency/diagnostics where available and explicit production-readiness block.
- Qualification/test records remain distinct from external qualification claims.

## Backend / security changes

- Added dedicated permissions including `policy_admin`, `workflow_admin`, `security_admin`, `service_account_admin`, `integration_admin`, `journal_post` and `reconciliation_certify` for applicable roles.
- Added notification service and notification read/list endpoints.
- Added Master Data change detail and return endpoints.
- Added adjustment detail and return-for-rework endpoint.
- Added deterministic applicable-policy consistency checks on true-up submission/approval.
- Added true-up preview endpoint and duplicate-open-proposal guard.
- Added duplicate source-import protection using SHA-256/source/period/entity context.
- Added qualification evidence download endpoint.
- Added exception detail endpoint and enriched exception serialization.
- Expanded Data Quality and System Health payloads.
- Added integration contract-test history endpoint.

## Database migration

No new database schema migration is required by Hotfix 7. The existing schema remains compatible with Hotfix 6 data. New behavior is implemented through application logic, API expansion and UI changes.

## Known limitations / intentionally external gates

Hotfix 7 does **not** self-certify the following:

- Live SAP S/4 qualification
- Independent penetration test
- Enterprise/customer IdP validation
- Independent Finance/TP UAT
- Independent TP professional sign-off
- Production DR / parallel-close evidence where required

These remain explicit external qualification gates.

Some P1/P2 product extensions remain enhancement backlog rather than being represented as externally proven production capability, including a full governed forecast authoring lifecycle, per-step SLA configuration UI and production observability/backup telemetry sourced from a real deployment platform.
