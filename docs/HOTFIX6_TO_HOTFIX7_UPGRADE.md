# Hotfix 6 → Hotfix 7 Upgrade Guide

## Release transition

From: `2.4.0-rc.3-hotfix6`  
To: `2.4.0-rc.3-hotfix7`

## Upgrade method

1. Stop the Hotfix 6 stack using the provided stop launcher.
2. Back up the Hotfix 6 database/volumes using the existing backup procedure.
3. Extract Hotfix 7 into a new release directory rather than overwriting Hotfix 6 in place.
4. Copy only approved environment-specific configuration/secrets; do not copy runtime build artifacts, caches or packaged databases.
5. Run `START_DEMO.bat` / `START_OTP.bat` as applicable.
6. Confirm `/api/v1/health/version` reports `2.4.0-rc.3-hotfix7`.
7. Run `QUALIFY_10_10.bat` on the target Windows/Docker Desktop environment.
8. Review Qualification Center and System Health before using the upgraded environment for demonstrations or UAT.

## Database compatibility

Hotfix 7 introduces no new schema migration. The existing Hotfix 6 database schema remains compatible. Application-level controls, API endpoints and UI behavior are upgraded without destructive data transformation.

## Behavioral changes users will notice

- Signed-in user/role is visible globally.
- Material actions give explicit progress/success/failure feedback.
- Master Data and approval requests are reviewable before decision.
- True-up proposals require a policy-consistent preview and duplicate protection.
- Approval review is centralized and evidence-oriented.
- P&L/import/variance/audit/workflow/accounting objects provide drill-down.
- Exception triage uses application dialogs instead of browser prompts.
- Security/Integrations use dedicated administration permissions.
- Qualification and System Health distinguish internal runtime health from external production qualification.

## Rollback

Because the database schema is unchanged, rollback consists of stopping Hotfix 7 and restarting the backed-up Hotfix 6 application against the preserved Hotfix 6-compatible data state. Do not roll back after intentionally changing external systems without separately reconciling those actions.
