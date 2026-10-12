# Hotfix 7 Implementation Matrix

Status values: **IMPLEMENTED**, **PARTIAL**, **DEFERRED-EXTERNAL**.

| Finding / Layer | Priority | Problem observed | Hotfix 7 implementation | Verification | Status |
|---|---|---|---|---|---|
| XAPP-USER | P1 | Signed-in user not visible | Global shell shows role/email and environment | Frontend source validation | IMPLEMENTED |
| XAPP-NAV | P1 | No professional back/forward context | Shell Back/Forward controls and breadcrumb/context bar | Frontend source validation | IMPLEMENTED |
| XAPP-FEEDBACK | P0 | Material actions appeared silent | Loading/success/error messages added to allocation, approval, journal, integration and other workbenches | Browser/source checks + API tests | IMPLEMENTED |
| XAPP-DRILL | P1 | IDs often non-clickable | Drill-down added across Master Data, approvals, P&L, imports, variance, audit, postings, journals, workflows | Frontend source validation | IMPLEMENTED |
| MD-001 | P0 | Blind Master Data approval | Change-detail endpoint + modal field-level diff/current/proposed/impact | `test_hotfix7_master_data_change_is_reviewable` | IMPLEMENTED |
| MD-002 | P0 | Maker could not inspect request | Request IDs open for creator/reviewer | API + UI | IMPLEMENTED |
| MD-003 | P0 | Reviewer not notified | Notification service on submit/review outcomes | API regression | IMPLEMENTED |
| MD-004 | P0 | Missing return-for-rework | `/catalog-changes/{id}/return` + reviewer comment | Hotfix 7 regression | IMPLEMENTED |
| IMP-DUP | P0 | Duplicate authoritative imports possible | SHA-256/source/period/entity duplicate guard | Backend regression | IMPLEMENTED |
| IMP-DETAIL | P1 | Import not drillable | Import detail modal with hash/control totals/issues | Frontend source validation | IMPLEMENTED |
| MAP-CONFLICT | P0 | Ambiguous mapping must remain deterministic | Existing deterministic conflict control preserved | Existing regression suite | IMPLEMENTED |
| MAP-DETAIL | P1 | Rule drill-down limited | Core rule visibility retained; dedicated expanded rule drawer remains backlog | Existing UI | PARTIAL |
| ALLOC-FEEDBACK | P0 | Execute had no visible reaction | Explicit executing/completed run feedback | Frontend source validation | IMPLEMENTED |
| ALLOC-IDEMP | P0 | Repeat execution risk | Existing governed run persistence/idempotent controls preserved; feedback added | Existing allocation tests | IMPLEMENTED |
| PNL-OPEN | P0 | Open button appeared dead | Open action now opens source-lineage modal | Frontend source validation | IMPLEMENTED |
| PNL-SNAPSHOT | P1 | Snapshot lineage weak | Existing immutable snapshot lock retained; run drill-down improved | Existing tests | IMPLEMENTED |
| POL-OPEN | P0 | New version draft could not be opened | Draft opens directly in editor; policy IDs drillable | Frontend source validation | IMPLEMENTED |
| POL-PERM | P0 | Generic `admin_policy` failure after click | Role-aware disabled controls with explanatory tooltip | Frontend source validation | IMPLEMENTED |
| BM-COMP | P0 | Comparables click appeared non-reactive | Explicit opening feedback, smooth navigation to screening, context-preserving master link | Frontend source validation | IMPLEMENTED |
| FORECAST-LC | P1 | Forecast screen too thin / approved baseline dependency unclear | Existing calculation retained; full authoring lifecycle remains roadmap | Existing API | PARTIAL |
| VAR-PERM | P0 | Run action available without write | Role-aware Run disable and tooltip | Frontend source validation | IMPLEMENTED |
| VAR-DETAIL | P1 | Variance run not drillable | Clickable run detail modal | Frontend source validation | IMPLEMENTED |
| SIM-CONTEXT | P1 | Simulation context could be stronger | Existing immutable non-posting semantics retained | Existing tests | PARTIAL |
| TU-POLICY | P0 | 0.035 vs active 0.04 policy ambiguity | Deterministic applicable-policy resolution and consistency blocker | Backend tests | IMPLEMENTED |
| TU-PREVIEW | P0 | No preview before proposal | `/true-ups/preview` + UI policy/target/formula/source review | `test_hotfix7_true_up_preview_pins_applicable_policy` | IMPLEMENTED |
| TU-DUP | P0 | Duplicate proposals possible | Equivalent open proposal guard | Backend regression | IMPLEMENTED |
| APPROVAL-REVIEW | P0 | Manager could approve without opening | Dedicated Approval Review Workspace | Frontend source + API tests | IMPLEMENTED |
| APPROVAL-RETURN | P0 | No controlled rework route | Return-for-rework with comment and audit | Backend/API | IMPLEMENTED |
| JRN-LINEAGE | P0 | Accounting lineage incomplete in UI | Journal detail includes true-up, approval actor, policy/version, template, lines | Existing + Hotfix 7 regression | IMPLEMENTED |
| JRN-IDEMP | P0 | Duplicate journal risk | Existing one-journal-per-adjustment uniqueness retained | Existing tests | IMPLEMENTED |
| ERP-LINEAGE | P0 | Posting source/history not visible | Posting detail shows source journal/true-up, attempts, fingerprint and reconciliation | Frontend/API | IMPLEMENTED |
| REC-LINK | P0 | Exception/reconciliation IDs not actionable | Reconciliation ID detail + exception deep-link | Frontend source validation | IMPLEMENTED |
| REC-REBUILD | P0 | Rebuild action lacked impact confirmation | In-app confirmation and explicit result feedback; historical run behavior retained | Existing tests + UI source | IMPLEMENTED |
| EXC-UI | P0 | Browser-native prompt | Professional in-app exception modal | Frontend source validation | IMPLEMENTED |
| EXC-ROOT | P0 | Wrong root-cause suggestion for profitability breach | Category-aware governed root-cause choices | Frontend source validation | IMPLEMENTED |
| EXC-WAIVER | P0 | Waiver rationale weak | Waiver requires reason; richer risk/evidence fields remain follow-up | API/UI | PARTIAL |
| DQ-DIMS | P0 | “100% validity” too broad | Multi-dimensional quality/readiness payload and screen | `test_hotfix7_data_quality_is_multidimensional` | IMPLEMENTED |
| DQ-DRILL | P1 | KPI counts not clickable | KPI/control links to underlying workbenches | Frontend source validation | IMPLEMENTED |
| DOC-DOWNLOAD | P0 | Download returned generic 81-byte `otp-evidence` | Real governed artifact download and meaningful filename handling | API/UI | IMPLEMENTED |
| DOC-LINK | P0 | Object linkage free text | Governed selectors added for object/document classifications in UI | Frontend source | IMPLEMENTED |
| AUDIT-LINK | P0 | Audit object text non-clickable | Object/correlation drill-down and timeline modal | Existing audit test + UI | IMPLEMENTED |
| SEC-PERM | P0 | Security used `admin_policy` | Dedicated service-account/security permission model | Regression suite | IMPLEMENTED |
| SEC-SCOPE | P0 | Free-text permissions/entities | Governed permission checkboxes and entity multi-select | Frontend source | IMPLEMENTED |
| INT-PERM | P0 | Integration admin tied to generic policy permission | Dedicated `integration_admin` | `test_hotfix7_integration_test_history_and_dedicated_admin` | IMPLEMENTED |
| INT-HISTORY | P1 | Contract tests had no history drill-down | `/integrations/{id}/runs` + detail modal | Hotfix 7 regression | IMPLEMENTED |
| WF-DESIGNER | P0 | Workflow Designer opened GL Accounts | Deep-link to `WORKFLOW_DEFINITIONS` | Frontend source | IMPLEMENTED |
| WF-REVIEW | P0 | Workflow inbox allowed blind row approval | Review modal before approve/return/reject | Frontend source | IMPLEMENTED |
| WF-STEPS | P0 | Approver roles presented as comma-separated text | Ordered step grammar shown explicitly; backend resolves `>` and `+` structure | Existing workflow tests | IMPLEMENTED |
| WF-TIMELINE | P1 | Instance history not drillable | Workflow instance/task timeline modal | Frontend source | IMPLEMENTED |
| QUAL-DRILL | P0 | Qualification controls/evidence not drillable | Control detail modal and evidence download | Frontend/API | IMPLEMENTED |
| QUAL-SPLIT | P0 | Internal 100% could be confused with production readiness | Explicit internal vs external summary and production block | Frontend source | IMPLEMENTED |
| HEALTH-RUNTIME | P0 | Redis/MinIO/n8n only `CONFIGURED` | Runtime probes with latency/diagnostics + checked time | `test_hotfix7_system_health_separates_runtime_and_external_gates` | IMPLEMENTED |
| HEALTH-EXT | P1 | External gates disconnected | Deep links to Qualification Center and explicit production block | Frontend source | IMPLEMENTED |
| EXT-SAP | External | Live SAP evidence unavailable | Remains pending; simulator never self-qualifies live SAP | Qualification registry | DEFERRED-EXTERNAL |
| EXT-PENTEST | External | Independent penetration test unavailable | Remains REQUIRED | Qualification registry | DEFERRED-EXTERNAL |
| EXT-IDP | External | Customer/enterprise IdP evidence unavailable | Remains pending | Qualification registry | DEFERRED-EXTERNAL |
| EXT-UAT | External | Independent Finance/TP UAT unavailable | Remains pending | Qualification registry | DEFERRED-EXTERNAL |
| EXT-TP | External | Independent TP sign-off unavailable | Remains pending | Qualification registry | DEFERRED-EXTERNAL |
