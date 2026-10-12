________________________________________
Master Prompt — Enterprise OTP Control Tower v2.4.0-rc.3-hotfix7 Upgrade
I am uploading the current working release of my application:
Enterprise OTP Control Tower — v2.4.0-rc.3-hotfix6
Your task is to act as a combined Senior Enterprise Product Architect, Senior Full-Stack Engineer, Transfer Pricing / Finance Systems Product Analyst, UX Architect, Security Architect, QA Lead, Release Engineer and Enterprise Controls Specialist and upgrade the supplied application professionally to:
v2.4.0-rc.3-hotfix7
This must be a real implementation upgrade of the attached Hotfix 6 application. Do not merely write recommendations, mockups, pseudo-code, TODOs, or a design document. Inspect the actual application, understand its architecture and existing behavior, implement the improvements directly in the codebase, preserve working functionality, test the upgraded release thoroughly, and return a complete runnable Hotfix 7 package.
The overriding objective is:
Transform Hotfix 6 from a strong enterprise demo / release-candidate platform into a substantially more coherent, traceable, role-aware, reviewable and control-oriented enterprise application without destroying its existing architecture or working functionality.
The upgrade must address all findings discovered during hands-on user acceptance testing across:
Master Data, Data Imports, Mapping, Allocation, Imported P&L, Policies, Benchmarks, Forecasting, Variance Analysis, Simulation, True-Ups, Approvals, Journals, ERP Postings, Reconciliation, Exceptions, Data Quality, Documents & Evidence, Audit Trail, Security, Integrations, Workflow & Approval Center, Qualification Center and System Health.
Treat every finding below as part of one integrated product improvement program.
________________________________________
1. General implementation principles
Before changing anything, inspect the actual Hotfix 6 codebase, application architecture, API routes, database models, frontend components, permissions, qualification infrastructure, Docker setup, seed/demo data, tests, release validation and startup scripts.
Preserve all existing working features unless a change is specifically required.
Do not replace the application with a simplified rewrite.
Do not break existing seeded datasets, demo workflows, qualification tooling, release-validation tooling, Docker startup or Windows one-click launch behavior.
All changes must follow these principles:
•	evidence before conclusion
•	maker-checker governance
•	immutable history
•	explicit versioning
•	deterministic calculations
•	backend-enforced authorization
•	least privilege
•	segregation of duties
•	full object lineage
•	auditability
•	human-readable UX
•	safe destructive/action controls
•	qualification/test data isolation
•	role-aware navigation
•	clear feedback after every material action
•	no silent failures
•	no dead buttons
•	no misleading controls
•	no action without confirmation where accounting/governance impact is material
•	no claim of external qualification where external evidence does not exist
The existing distinction between demo/internal qualification and external qualification must remain explicit.
________________________________________
2. Priority model
Classify every implementation item into:
P0 — Critical
Issues that affect correctness, approval integrity, financial control, auditability, authorization, workflow safety, idempotency, policy resolution, evidence integrity or production-readiness claims.
These must be implemented before Hotfix 7 is considered qualified.
P1 — High
Issues affecting professional enterprise usability, traceability, user confidence, drill-down, role awareness, workflow effectiveness and administrative control.
Implement all reasonably achievable P1 items in Hotfix 7.
P2 — Medium
Usability, navigation, presentation, dashboard enrichment, analytics or convenience improvements.
Implement where they do not destabilize P0/P1 work.
At the end, provide a traceability matrix showing:
Finding ID → Priority → Code change → Test → Status.
________________________________________
3. Cross-application requirements
These requirements apply across the complete application.
3.1 Signed-in user visibility
The current signed-in user must be visibly identifiable throughout the application.
Display professionally in the top bar, for example:
TP Manager • manager@otp.local
or through a compact profile control.
Where useful show:
•	user name/email
•	role
•	active entity scope
•	environment
•	sign out
Do not expose sensitive credential information.
________________________________________
3.2 Professional navigation
Add consistent application-level navigation controls where context requires them.
Provide professional:
•	Back
•	Forward where meaningful
•	Breadcrumbs
•	“Back to list”
•	“Back to source object”
Do not rely exclusively on browser Back.
Preserve current sidebar navigation.
________________________________________
3.3 Action feedback
Every material action must provide immediate, unambiguous feedback.
Examples:
•	Saving…
•	Submitted successfully
•	Simulation completed
•	Execution completed
•	Approval returned for rework
•	Journal generated
•	ERP posting simulated
•	Reconciliation rebuilt
•	Contract test passed
•	Evidence uploaded
No material button may appear to do nothing.
For longer actions add:
•	loading state
•	disabled duplicate submission
•	progress state
•	success/failure message
•	resulting object ID where relevant
________________________________________
3.4 Drill-down framework
Where the UI displays a business object ID, KPI, exception ID, workflow instance, journal, ERP document, audit object or evidence object, make it actionable where authorization permits.
Users should be able to navigate:
Summary → Detail → Evidence → Audit
and back again.
Examples:
•	True-Up ID → True-Up detail
•	Journal → Journal detail
•	ERP document → posting detail
•	Exception → case detail
•	Reconciliation → reconciliation detail
•	Audit event → business object
•	Business object → audit history
•	Qualification control → evidence
•	KPI → filtered underlying records
________________________________________
3.5 Qualification/test-data isolation
Qualification-generated objects currently appear across normal operational lists.
Implement a clear distinction between:
•	Business / operational data
•	Demo data
•	Qualification/test data
•	Archived data
At minimum provide visible origin/context badges and filters.
Qualification records must not distort production/business KPIs.
Do not remove qualification evidence required by the existing test framework.
________________________________________
4. Master Data Catalog
Preserve the governed maker-checker/versioned master-data architecture.
Implement the following.
P0
MD-001 — Reviewable change requests
Any submitted master-data change must be openable before approval.
The reviewer must see:
•	request ID
•	domain
•	record ID
•	current value
•	proposed value
•	field-by-field diff
•	effective date
•	change reason
•	maker
•	submitted timestamp
•	impacted dependencies
•	evidence where applicable
Do not allow blind approval.
MD-002 — Maker visibility
The Data Steward who creates or edits a record must be able to reopen and inspect their own draft/submitted change request.
MD-003 — Reviewer notification
Relevant approver roles must receive an in-app notification/task when governed master data is submitted.
MD-004 — Approve / Reject / Return for rework
Reviewers require:
•	Approve
•	Reject
•	Return for rework
with comments and immutable audit trail.
P1
•	clickable change-request IDs
•	version comparison
•	effective dating
•	dependency impact preview
•	professional domain-specific forms
•	domain-context-preserving navigation
Do not default a deep link such as Workflow Designer or Benchmark Editor to unrelated GL Accounts.
________________________________________
5. Data Imports
Preserve immutable landing, SHA-256, source metadata and validation.
P0
Implement duplicate import detection using appropriate combination of:
•	SHA-256
•	source
•	period
•	entity
•	row identity
•	source batch
A duplicate file should not silently create another authoritative population.
Provide clear statuses such as:
•	New
•	Duplicate
•	Superseded
•	Validated
•	Rejected
•	Partially accepted
P1
Each import must be drillable into:
•	file metadata
•	hash
•	source
•	period
•	imported by
•	timestamp
•	accepted/rejected/warnings
•	control totals
•	row-level errors
•	downstream usage
Allow safe filtering by source/origin, especially qualification vs business imports.
________________________________________
6. ERP → TP Mapping
Preserve deterministic rule resolution and mapping coverage.
P0
Mappings must retain:
•	rule version
•	priority
•	condition
•	entity
•	segment
•	transaction
•	policy
•	effective dates
Provide conflict detection and block ambiguous mapping where deterministic resolution is impossible.
P1
Allow each mapping rule to open into a detail view with:
•	business-readable rule
•	criteria
•	matched population
•	priority
•	effective dates
•	policy linkage
•	audit trail
Mapping coverage such as 100% / 6000 of 6000 should be drillable to mapped/unmapped populations.
________________________________________
7. Allocation Workbench
Preserve the configurable multi-stage allocation engine.
P0
After Execute, the user must receive explicit feedback.
Show:
•	run ID
•	status
•	executed by
•	timestamp
•	source pool
•	exclusions
•	eligible pool
•	recipients
•	driver values
•	allocation
•	markup
•	residual
•	accounting-impact state
Do not allow a material execution button to appear silent.
Implement idempotency/duplicate-run protection where the same governed execution is repeated unintentionally.
P1
Allocation rules and runs must be openable.
Improve horizontal-table usability and responsive layout.
Explain:
Original Pool − Exclusions = Eligible Pool
and reconciliation logic clearly.
________________________________________
8. Imported / Segmented P&L
P0
Fix non-reactive Open actions.
Every P&L run must be openable into detailed source lineage.
Show:
•	run ID
•	period
•	dimensions
•	mapping coverage
•	allocation residual
•	source import(s)
•	snapshot state
•	SHA-256/manifests
•	creation timestamp
•	creator
•	underlying rows/aggregations
P1
Snapshots must expose:
•	locked by
•	locked at
•	source run
•	scenario
•	version
•	reason
•	immutable status
Preserve snapshot locking.
________________________________________
9. Policies
Preserve policy lifecycle:
Draft → Review → Approved → Active → Superseded
P0
Policy version rows must be openable/editable where permitted.
Do not allow “New version” to create a draft that cannot be opened.
Permission-based controls must be role-aware:
•	hide or disable unauthorized actions before the user attempts them
•	explain required permission professionally
Do not rely on generic errors such as:
Missing permission: admin_policy
for unrelated modules.
P1
Policy detail must show:
•	policy ID
•	entity
•	method
•	PLI
•	target
•	benchmark
•	effective dates
•	version
•	lifecycle state
•	creator
•	reviewer
•	approval timestamp
•	source benchmark/version
•	change history
________________________________________
10. Benchmark Management
P0
Fix non-reactive Comparables buttons.
Benchmark rows must open the comparable-screening workspace.
Do not route the user to generic Master Data without preserving the TP Benchmarks context.
P1
Benchmark detail should show:
•	benchmark ID/version
•	method
•	PLI
•	Q1
•	median
•	Q3
•	source
•	validity
•	comparable population
•	inclusions/exclusions
•	screening rationale
•	observation periods
•	evidence
•	linked policies
All benchmark master-data change requests must be reviewable before approval.
________________________________________
11. Forecasting
The current screen is too thin.
P1
A forecast should expose:
•	entity
•	period
•	actual/YTD period
•	remaining forecast assumptions
•	full-year revenue
•	EBIT
•	ROS
•	forecast version
•	status
•	owner
•	source
•	created at
•	approved at where applicable
Implement a governed forecast lifecycle if supported by the existing architecture:
Draft → Submitted → Approved → Superseded
This is necessary because Variance Analysis currently supports a FORECAST baseline but reported:
No approved forecast version available.
That dependency should be clear to the user.
________________________________________
12. Variance Analysis
Preserve deterministic additive EBIT bridge.
P0
Role-based action availability must be clear. If a user lacks write, the Run button should not behave like an available action.
P1
Variance runs must be drillable.
Display:
•	baseline
•	baseline version
•	actual version
•	baseline EBIT
•	actual EBIT
•	total variance
•	components
•	residual
•	source lineage
Where source data supports it, show:
•	volume
•	price
•	mix
•	FX
Never invent root causes.
________________________________________
13. Simulation & Goal Seek
Preserve immutable scenario analysis that never posts to accounting.
P1
Enhance result context:
•	simulation ID
•	user
•	timestamp
•	source P&L
•	current ROS
•	simulated ROS
•	target ROS
•	IC purchase delta
•	required COGS at target
•	assumptions
•	linked policy
•	disclaimer that simulation is non-posting
Allow the simulation ID to open to details/history.
________________________________________
14. True-Up Workbench
This is one of the highest-priority Hotfix 7 areas.
P0 — policy-target resolution
We observed a true-up using:
POLICY_TARGET = 0.035
while the active DE01 policy screen showed:
0.04.
Implement deterministic applicable-policy resolution.
Before creating a true-up:
•	resolve exact policy ID
•	version
•	effective dates
•	entity
•	method/PLI
•	benchmark
•	target source
•	target value
If the resolved target conflicts with the active applicable policy, block creation and generate a controlled exception.
Do not silently resolve an inconsistent target.
P0 — preview before creation
Provide a true-up calculation preview before creating the proposal.
Include:
•	source calculation
•	actual PLI
•	policy ID/version
•	target basis
•	target value
•	benchmark/version
•	revenue/cost base
•	formula
•	adjustment amount
•	adjustment direction
•	counterparty
•	estimated post-adjustment result
P0 — duplicate protection
Prevent duplicate equivalent open proposals.
If the same:
•	calculation
•	entity
•	period
•	target
•	amount
•	frequency
already has an open proposal, warn/block and provide:
•	Open existing
•	Replace/revise existing
•	Cancel
P0 — immutable source snapshot
Store the exact:
•	policy
•	benchmark
•	source P&L
•	calculation
•	assumptions
•	target
•	amount
used when creating the proposal.
P1
Provide explicit separation between:
•	policy-generated true-ups
•	manual adjustments
•	qualification/test adjustments
________________________________________
15. Approvals
This is another major P0 area.
Replace the shallow current approval behavior with a professional Approval Review Workspace.
P0
A manager must never be required to approve from a summary row without opening the request.
Each approval item must be openable.
Display:
•	request/object ID
•	maker
•	submission timestamp
•	entity
•	period
•	amount
•	currency
•	source calculation
•	actual PLI
•	applicable policy/version
•	benchmark/version
•	target
•	post-adjustment result
•	counterparties
•	accounting impact
•	evidence
•	policy/data-quality warnings
•	duplicate warnings
•	materiality warnings
•	comments/history
Actions:
•	Approve
•	Reject
•	Return for rework
Require comments according to governance rules, especially high-value or exceptional decisions.
P0
If a policy resolution inconsistency exists, approval must be blocked.
P1
Unify the operational Approvals page with the governed Workflow & Approval Center rather than maintaining two disconnected approval experiences.
________________________________________
16. Accounting Journals
Preserve deterministic, balanced journal generation.
P0
Every journal must have explicit lineage:
True-Up → Approval → Journal → ERP Posting → Reconciliation
Provide:
•	source true-up
•	source approval
•	policy/version
•	journal template
•	company code
•	period
•	document date
•	posting date
•	currency
•	GL lines
•	partner
•	profit center
•	debit/credit
•	balance validation
•	created by
•	posted by
•	timestamps
Implement idempotency to prevent duplicate journals for the same economic adjustment.
P1
Support detailed statuses:
Draft → Approved → Posted → Reconciled → Reversed
Show original ↔ reversal linkage.
________________________________________
17. ERP Postings
Preserve explicit separation between simulator and real SAP.
P0
Every ERP posting must link to its source journal and true-up.
Implement/confirm idempotency and store a posting fingerprint.
Show:
•	ERP document ID
•	source journal
•	company code
•	fiscal year
•	period
•	posting date
•	amount
•	currency
•	environment
•	connector
•	service account
•	posted by
•	posted at
•	request/correlation ID
•	response/result
•	retry history
•	error history
•	reconciliation state
P1
Statuses should include as applicable:
•	Pending
•	Posted
•	Reconciled
•	Failed
•	Reversed
Simulator records must visibly show SIMULATOR.
Never present simulated posting as real SAP posting.
________________________________________
18. Reconciliation Control Center
Preserve:
Calculation → True-Up → Journal → Posting → Final P&L
P0
Make reconciliation IDs openable.
Exception IDs such as EXC-REC-13 must deep-link to Exception Management.
Show stage-level differences:
•	Expected → Journal
•	Journal → ERP
•	ERP → Final P&L
P0 — tolerance policy
Show the exact tolerance rule/version applied.
Do not simply display a difference without explaining why it creates or does not create an exception.
P0 — rebuilding
Rebuild stages must:
•	explain exactly what will be rebuilt
•	never overwrite historical evidence
•	create a new reconciliation version/run
•	preserve prior results
•	record actor/time/reason
•	require confirmation
P0 — certification
Certification must support segregation of duties.
Store:
•	certified by
•	certified at
•	comments
•	evidence snapshot
•	tolerance version
________________________________________
19. Exception Management
Replace browser-native prompts with a proper in-app exception workspace.
P0
Exception IDs must be openable.
Case detail must show:
•	exception ID
•	source
•	category
•	entity
•	severity
•	financial exposure
•	owner
•	created date
•	due date
•	status
•	root cause
•	linked object
•	evidence
•	comments
•	activity timeline
P0 — triage
The current triage prompt suggested:
Reconciliation / source-data difference
for a PROFITABILITY_BREACH.
This must be corrected.
Root-cause suggestions must be relevant to the selected category and evidence.
Use governed root-cause taxonomy plus optional narrative.
P0 — waiver controls
A waiver must require:
•	reason
•	risk assessment
•	compensating control
•	approver
•	evidence
•	expiry
•	review date
Do not permit opaque WAIVED cases with no visible rationale.
P1
Use lifecycle:
OPEN → TRIAGED → INVESTIGATING → REMEDIATED → VERIFIED → CLOSED
plus governed WAIVED.
Add SLA, ageing and escalation.
________________________________________
20. Data Quality Control
The current 100% Validity metric is too narrow.
P0
Separate data quality into dimensions:
•	Technical/schema validity
•	Completeness
•	Uniqueness
•	Referential integrity
•	Consistency
•	Timeliness
•	Business-rule validity
•	Downstream control readiness
Do not call the dataset universally “100% valid” if only schema ingestion succeeded.
P0
Include checks for:
•	duplicate imports
•	overlapping periods
•	missing master-data references
•	missing policy/benchmark linkage
•	target inconsistencies
•	impossible/outlier P&L values
•	unresolved exceptions
•	missing mappings
•	stale data
P0
Provide a downstream readiness gate such as:
•	READY
•	CONDITIONAL
•	BLOCKED
Allow critical DQ failures to block relevant downstream processes.
P1 — drill-down
All KPI cards/counts must be clickable:
•	Imported rows
•	Accepted
•	Rejected
•	Warnings
•	Open exceptions
•	Active mapping rules
•	Allocation rules
Open exceptions: 35 must open Exception Management with the correct filter.
________________________________________
21. Documents & Evidence
Preserve versioning, object linkage, expiry and SHA-256.
P0
Fix evidence delivery.
Current download produced a generic file named:
otp-evidence
of approximately 81 bytes.
Downloads must return the real governed evidence artifact or complete evidence package.
Use meaningful filename and extension.
Example:
DE01_TU-DE01-2026-09-12E5023_CALCULATION_EVIDENCE_v1.pdf
P0
Linked object type and linked object ID must be governed selectors, not uncontrolled free text.
P0
Implement immutable evidence version history and retention metadata.
P1
Show:
•	uploader
•	created at
•	version comment
•	type
•	entity
•	linked objects
•	SHA-256
•	retention
•	expiry
•	verification state
•	confidentiality/access classification
Support evidence-pack generation for audit objects/periods.
________________________________________
22. Audit Trail
Preserve the existing strong audit-event architecture.
P0
Audit object references must be clickable.
For example:
adjustment • TU-DE01-2026-09-12E5023
must open the corresponding object.
Correlation IDs must be navigable to a complete correlated event chain.
P0
Provide an audit event detail page/drawer containing:
•	timestamp
•	actor
•	role
•	entity
•	event
•	object
•	previous state
•	new state
•	changed fields
•	correlation ID
•	request/session context
•	evidence links
P1
Add filters for:
•	date range
•	actor
•	event
•	object type
•	object ID
•	entity
•	module
•	result
•	qualification/business context
Support audit export.
Preserve append-only behavior and add visible integrity/tamper-evidence information if supported.
________________________________________
23. Security Administration
P0
Security Administration must use dedicated security permissions, not unrelated admin_policy.
Implement separate scopes such as:
•	security_admin
•	service_account_admin
•	role_admin
•	user_admin
•	policy_admin
•	journal_post
•	reconciliation_certify
•	workflow_admin
P0
Unauthorized users should not see fully actionable privileged forms.
Use route/action-level authorization plus professional read-only/denied state.
P0
Replace free-text comma-separated permission/entity entry with governed selectors.
P0
Service accounts require lifecycle controls:
•	owner
•	purpose
•	environment
•	permissions
•	entity scope
•	authentication method
•	created at
•	last used
•	expiry
•	last rotation
•	rotation due
•	revoke
•	revoke reason
•	audit history
Secrets must never be displayed after initial controlled reveal.
P1
Provide filters:
•	Active
•	Expired
•	Revoked
•	Qualification/Test
Implement periodic access recertification and SoD conflict detection.
________________________________________
24. Enterprise Integrations
Preserve explicit simulator qualification behavior.
P0
Real SAP and simulator must remain clearly separate.
Maintain:
•	SAP_S4
•	SAP_S4_SIMULATOR
•	Live: true/false
•	qualification state
P0
Connection detail must include:
•	connection code
•	connector
•	environment
•	endpoint/system ID
•	authentication method
•	secret reference
•	linked service account
•	entity/company-code scope
•	API/contract version
•	owner
•	configuration version
•	lifecycle status
P1
Contract test result should show:
•	status
•	tested by
•	timestamp
•	latency
•	request ID
•	contract version
•	diagnostics
•	failure reason
•	evidence artifact
Keep historical contract-test results.
Simulator success must not convert external qualification to passed.
________________________________________
25. Workflow & Approval Center
Preserve:
•	version-pinned workflow instances
•	sequential/parallel approvals
•	delegation
•	SLA
•	escalation
•	immutable workflow version used by each instance
P0
The Workflow Designer button currently routes to generic Master Data / GL Accounts.
Fix it so it deep-links directly to:
Master Data → Workflow Definitions
or a dedicated Workflow Designer route.
P0
Use a unified Approval Inbox for all governed approvals.
P0
Workflow definitions must support structured:
•	workflow code
•	business name
•	object type
•	effective dates
•	amount range
•	entity scope
•	country
•	method
•	risk level
•	condition
•	approval mode
•	approval steps
•	approver roles
•	SLA
•	escalation
•	delegation
•	self-approval prevention
P0
Replace comma-separated approver roles with explicit ordered steps.
For sequential mode show, for example:
1.	TP Manager
2.	Finance Controller
3.	Group Tax Director
For parallel mode support:
•	all
•	any
•	quorum
P0
Workflow definition changes must remain maker-checker governed.
Provide impact analysis before activation.
P1
Use professional workflow names such as:
•	Standard True-Up Approval
•	High-Value True-Up Approval
•	Policy Change Approval
•	Benchmark Change Approval
•	Master Data Change Approval
Qualification-generated Q10WF... workflows should be separated/filterable.
________________________________________
26. Qualification Center
Preserve historical release evidence and external-gate honesty.
P0
Each qualification control must be drillable into:
•	control definition
•	test run
•	release version
•	evidence
•	hash
•	reviewer
•	timestamp
•	logs
•	status
P0
The interface must clearly distinguish:
•	Internal automated qualification
•	Internal/local UAT
•	External Finance/TP UAT
•	Live SAP qualification
•	External penetration test
•	Enterprise IdP qualification
•	Independent TP sign-off
•	DR/parallel close where relevant
Do not allow an internal UAT PASS to be confused with external Finance/TP acceptance.
P0
Qualification must always be release-version pinned.
Display current release prominently:
2.4.0-rc.3-hotfix7
P1
Provide:
•	historical release comparison
•	regressions
•	new/removed controls
•	evidence hashes
•	recorded at
•	recorded by
•	external-gate owner
•	target date
•	blocking/non-blocking classification
•	qualification evidence export
Keep historical failures immutable.
________________________________________
27. System Health & Qualification
P0
CONFIGURED is not equivalent to HEALTHY.
Implement actual health checks for:
•	FastAPI
•	PostgreSQL
•	Redis
•	MinIO
•	n8n
•	worker/background processing where applicable
P1
Display:
•	last checked
•	response time
•	service version
•	build SHA
•	environment
•	status
•	recent failures
•	dependencies
Add:
•	DB backup status
•	restore-test status
•	object-storage backup status
•	DR status
•	queue health
•	disk/volume health
•	certificate expiry where applicable
External qualification gates should deep-link to Qualification Center.
Provide overall states such as:
•	Runtime Healthy
•	Degraded
•	Internally Qualified
•	External Qualification Pending
•	Production Blocked
________________________________________
28. Cross-layer notifications
Implement a professional in-app notification/task concept.
At minimum:
Data Steward
Receives:
•	own submitted change status
•	approval/rejection/return
•	remediation requests
TP Manager
Receives:
•	master-data approvals
•	true-up approvals
•	policy/benchmark approval tasks relevant to role
•	material exceptions
•	overdue tasks
Finance Controller
Receives:
•	journal/posting/reconciliation approval or exception tasks
Group Tax / Tax Director
Receives:
•	high-value/escalated approval tasks
•	policy/benchmark governance tasks
•	SLA escalations
Notifications should link directly to the reviewable business object.
________________________________________
29. Permission-aware UX
Do not show an actionable button that is guaranteed to fail for the current user unless intentionally disabled with explanation.
Examples:
Instead of:
New Version → click → Missing permission: admin_policy
show:
New Version disabled
with:
Requires Policy Administrator permission.
Backend authorization remains mandatory even when UI actions are hidden.
________________________________________
30. High-value controls
Introduce materiality-aware controls.
For large adjustments, such as the approximately €33.9m true-up observed during testing, support:
•	high-value workflow
•	additional approval step
•	mandatory evidence
•	mandatory review comment
•	policy/target consistency validation
•	accounting-impact preview
•	duplicate-check
•	audit package
Do not hard-code the observed amount as the threshold. Use configurable workflow rules.
________________________________________
31. UX modernization
Do not redesign the visual identity unnecessarily.
Retain the current professional dark-sidebar / light-workspace design.
Improve:
•	clickable identifiers
•	hover states
•	disabled states
•	tooltips
•	responsive tables
•	sticky headers where useful
•	searchable selectors
•	modal/dialog design
•	breadcrumbs
•	user identity
•	success/error banners
•	empty states
•	loading states
Replace native browser alert, prompt and confirm controls with professional application-controlled modals.
________________________________________
32. Backend controls
Implement or strengthen server-side enforcement for:
•	authorization
•	maker-checker
•	self-approval prevention
•	policy-version pinning
•	workflow-version pinning
•	benchmark-version pinning
•	data-quality readiness gates
•	idempotency
•	duplicate detection
•	effective dating
•	immutable history
•	evidence integrity
•	reconciliation tolerance
•	service-account scope
•	qualification isolation
Do not rely solely on frontend behavior.
________________________________________
33. Acceptance criteria
Hotfix 7 must not be considered complete until the following are demonstrably true:
1.	A Data Steward can create/edit a governed record and reopen their request.
2.	A manager can receive and open the request before approving.
3.	A manager sees field-level before/after changes.
4.	A submitted true-up is fully reviewable before approval.
5.	True-up policy target always resolves deterministically to the applicable policy version.
6.	Policy mismatch blocks creation/approval.
7.	Duplicate true-up proposals are prevented.
8.	Material action buttons provide clear feedback.
9.	P&L Open works.
10.	Benchmark Comparables works.
11.	Policy draft rows are openable.
12.	Approval IDs are openable.
13.	Journal → ERP → Reconciliation lineage is navigable.
14.	Reconciliation exception IDs open the case.
15.	Exception triage uses professional in-app UI.
16.	Waivers require governed rationale.
17.	Data Quality KPIs drill down.
18.	Data Quality separates schema validity from business readiness.
19.	Evidence downloads real, meaningful artifacts with correct names/extensions.
20.	Audit objects and correlations are clickable.
21.	Security uses dedicated permission scopes.
22.	Service accounts have governed credential lifecycle.
23.	Integration contract-test results include evidence/history.
24.	Workflow Designer opens directly to Workflow Definitions.
25.	Workflow steps/roles are structured rather than comma-separated.
26.	Qualification evidence is release-version pinned and drillable.
27.	Historical failures remain intact.
28.	External qualification remains explicitly pending where evidence is absent.
29.	Redis, MinIO and n8n have real health checks, not only configured-state checks.
30.	All material actions are audit logged.
________________________________________
34. Required regression testing
Create or extend automated tests covering the full Hotfix 7 behavior.
At minimum include:
Backend/API
•	authentication
•	RBAC
•	service-account scope
•	maker-checker
•	self-approval block
•	workflow routing
•	workflow version pinning
•	true-up policy resolution
•	mismatch blocking
•	duplicate true-up prevention
•	duplicate journal prevention
•	ERP idempotency
•	reconciliation tolerance
•	exception lifecycle
•	waiver governance
•	evidence integrity
•	audit events
•	DQ readiness
•	qualification isolation
Frontend/browser
Test every major layer:
1.	Control Tower
2.	Entities
3.	Forecasts
4.	Variance
5.	Simulation
6.	True-Ups
7.	Approvals
8.	Journals
9.	ERP Postings
10.	Reconciliation
11.	Master Data
12.	Imports
13.	Mapping
14.	Allocation
15.	Imported P&L
16.	Policies
17.	Benchmarks
18.	Documents
19.	Data Quality
20.	Exceptions
21.	AI Copilot if existing
22.	Audit Trail
23.	Integrations
24.	Workflow
25.	Security
26.	Qualification
27.	System Health
Test:
•	navigation
•	clickable IDs
•	permissions
•	disabled states
•	role switching
•	success/error feedback
•	drill-down
•	back navigation
•	DE/EN localization
•	responsive behavior
________________________________________
35. Release validation and qualification
Update all version references from Hotfix 6 to:
2.4.0-rc.3-hotfix7
Update as appropriate:
•	package version
•	frontend version
•	backend settings
•	Docker markers
•	.env.example
•	startup launcher
•	release docs
•	qualification registry
•	validation rules
•	UI version label
Preserve the successful Hotfix 6 release-validation standards.
Hotfix 7 release validation must verify:
•	required files
•	no transient artifacts
•	no packaged .env
•	no packaged runtime DB
•	pinned dependencies
•	pinned Docker images
•	valid OpenAPI
•	valid n8n JSON
•	startup integrity
•	release version consistency
•	localization
•	master-data governance
•	workflow governance
•	true-up consistency controls
•	approval reviewability
•	deep-link integrity
•	journal/ERP idempotency
•	reconciliation governance
•	evidence download integrity
•	audit linkage
•	security scopes
•	integration qualification
•	qualification evidence registry
•	runtime health
•	Hotfix 7 regression suite
The existing one-click local qualification runner must remain usable.
________________________________________
36. Required deliverables
Return a complete professional Hotfix 7 release containing:
A. Full upgraded application
A complete ZIP:
Enterprise_OTP_Platform_v2.4.0-rc.3-hotfix7.zip
It must run independently and must not require Hotfix 6 files outside the package.
B. One-click startup
Preserve or improve the Windows one-click startup.
C. One-click qualification
Preserve the existing quality/qualification launcher and extend it for Hotfix 7.
D. Release notes
Include:
HOTFIX7_RELEASE_NOTES.md
with:
•	implemented findings
•	P0/P1/P2
•	architecture changes
•	DB migrations
•	UX changes
•	security changes
•	known limitations
•	external qualification gates
E. Hotfix 7 implementation matrix
Include:
HOTFIX7_IMPLEMENTATION_MATRIX.md
Columns:
•	Finding ID
•	Layer
•	Priority
•	Problem
•	Implementation
•	Files changed
•	Test coverage
•	Acceptance criterion
•	Status
F. Test report
Include:
HOTFIX7_TEST_REPORT.md
G. Qualification report
Include:
HOTFIX7_QUALIFICATION_REPORT.md
Clearly separate:
•	internally passed
•	externally pending
•	not applicable
•	blocked
H. Migration / upgrade guide
Include:
HOTFIX6_TO_HOTFIX7_UPGRADE.md
If schema changes are needed, migration must preserve existing Hotfix 6 data.
________________________________________
37. Do not artificially inflate readiness
Even after implementing Hotfix 7, continue to mark the following as externally pending unless actual independent evidence is supplied:
•	live SAP S/4 qualification
•	independent penetration test
•	enterprise/customer IdP validation
•	independent Finance/TP UAT
•	independent TP professional sign-off
•	production DR/parallel close where external qualification is required
Hotfix 7 may achieve 100% internal qualification while still correctly showing external production gates as pending.
________________________________________
38. Final quality bar
Before returning the package, assess the application as if it were being demonstrated to:
•	Head of Transfer Pricing
•	Group Tax Director
•	Finance Controller
•	CFO organization
•	Internal Audit
•	External Auditor
•	IT Security
•	Enterprise Architecture
•	SAP Integration team
•	Data Governance
•	Risk & Compliance
A senior reviewer should be able to answer, directly from the application:
Who did what?
Under which role?
Based on which data?
Using which policy/version?
Which benchmark/version?
Who reviewed it?
What changed?
Which evidence supported it?
What accounting entry resulted?
Was it actually posted or only simulated?
Did the posting reconcile?
Were there exceptions?
Who resolved or waived them?
Is the system technically healthy?
Which release was qualified?
Which external qualifications are still pending?
If those questions cannot be answered through traceable UI and backend evidence, the corresponding workflow is not yet complete.
________________________________________
39. Execution approach
Work systematically:
Phase 1 — Inspect Hotfix 6
Understand the existing implementation before modifying it.
Phase 2 — Build Hotfix 7 backlog
Map every requirement above to actual code/components/models/routes/tests.
Phase 3 — Implement P0 controls
Correctness, approvals, policy resolution, evidence, idempotency, authorization and auditability first.
Phase 4 — Implement P1 UX/governance
Deep links, details, notifications, role-aware controls, administration improvements.
Phase 5 — Implement P2 polish
Navigation, dashboards, presentation, convenience.
Phase 6 — Regression test
Backend + browser + Docker + qualification.
Phase 7 — Release validation
No transient artifacts, no secrets, consistent versioning, clean package.
Phase 8 — Package Hotfix 7
Return the complete standalone ZIP and reports.
Do not stop after identifying a problem that can be fixed in the supplied codebase. Implement it, test it, and document it.
________________________________________
Final instruction
The goal is not to maximize the number of features.
The goal is to make the existing Enterprise OTP Control Tower behave like a coherent, controlled enterprise application in which:
every material object is reviewable, every important action is traceable, every approval is evidence-based, every accounting impact is linked, every permission is intentional, every exception is governed, every qualification claim is defensible, and every user understands what happened after they click an action.
Use Hotfix 6 as the authoritative baseline and upgrade it conservatively to Hotfix 7 while preserving all currently successful functionality and qualification behavior.

