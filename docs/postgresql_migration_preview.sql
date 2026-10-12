BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 0001_initial

CREATE TABLE users (
    id SERIAL NOT NULL, 
    email VARCHAR NOT NULL, 
    password_hash VARCHAR NOT NULL, 
    role VARCHAR, 
    active BOOLEAN, 
    PRIMARY KEY (id), 
    UNIQUE (email)
);

CREATE UNIQUE INDEX ix_users_email ON users (email);

CREATE TABLE entities (
    id SERIAL NOT NULL, 
    entity_code VARCHAR NOT NULL, 
    legal_name VARCHAR NOT NULL, 
    country VARCHAR NOT NULL, 
    currency VARCHAR NOT NULL, 
    characterization VARCHAR NOT NULL, 
    company_code VARCHAR NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (entity_code)
);

CREATE UNIQUE INDEX ix_entities_entity_code ON entities (entity_code);

CREATE TABLE tp_policies (
    id SERIAL NOT NULL, 
    policy_code VARCHAR NOT NULL, 
    entity_id INTEGER NOT NULL, 
    method VARCHAR NOT NULL, 
    pli VARCHAR NOT NULL, 
    target FLOAT NOT NULL, 
    lower_bound FLOAT NOT NULL, 
    upper_bound FLOAT NOT NULL, 
    benchmark_id VARCHAR, 
    version VARCHAR, 
    status VARCHAR, 
    PRIMARY KEY (id), 
    UNIQUE (policy_code), 
    FOREIGN KEY(entity_id) REFERENCES entities (id)
);

CREATE TABLE financial_periods (
    id SERIAL NOT NULL, 
    entity_id INTEGER NOT NULL, 
    period VARCHAR NOT NULL, 
    revenue FLOAT NOT NULL, 
    cogs FLOAT NOT NULL, 
    opex FLOAT NOT NULL, 
    forecast_ros FLOAT, 
    source_import_id VARCHAR, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_entity_period UNIQUE (entity_id, period), 
    FOREIGN KEY(entity_id) REFERENCES entities (id)
);

CREATE TABLE calculations (
    id SERIAL NOT NULL, 
    calculation_code VARCHAR NOT NULL, 
    entity_id INTEGER NOT NULL, 
    policy_id INTEGER NOT NULL, 
    period VARCHAR NOT NULL, 
    revenue FLOAT NOT NULL, 
    ebit FLOAT NOT NULL, 
    actual_pli FLOAT NOT NULL, 
    target_pli FLOAT NOT NULL, 
    suggested_adjustment FLOAT NOT NULL, 
    engine_version VARCHAR, 
    source_hash VARCHAR, 
    created_at TIMESTAMP WITHOUT TIME ZONE, 
    PRIMARY KEY (id), 
    UNIQUE (calculation_code), 
    FOREIGN KEY(entity_id) REFERENCES entities (id), 
    FOREIGN KEY(policy_id) REFERENCES tp_policies (id)
);

CREATE TABLE adjustments (
    id SERIAL NOT NULL, 
    adjustment_code VARCHAR NOT NULL, 
    calculation_id INTEGER NOT NULL, 
    entity_id INTEGER NOT NULL, 
    amount FLOAT NOT NULL, 
    status VARCHAR, 
    submitted_by VARCHAR, 
    approved_by VARCHAR, 
    created_at TIMESTAMP WITHOUT TIME ZONE, 
    PRIMARY KEY (id), 
    UNIQUE (adjustment_code), 
    FOREIGN KEY(calculation_id) REFERENCES calculations (id), 
    FOREIGN KEY(entity_id) REFERENCES entities (id)
);

CREATE TABLE journal_entries (
    id SERIAL NOT NULL, 
    journal_code VARCHAR NOT NULL, 
    adjustment_id INTEGER NOT NULL, 
    entity_code VARCHAR NOT NULL, 
    counterparty_code VARCHAR NOT NULL, 
    debit FLOAT NOT NULL, 
    credit FLOAT NOT NULL, 
    currency VARCHAR NOT NULL, 
    status VARCHAR, 
    PRIMARY KEY (id), 
    UNIQUE (journal_code), 
    FOREIGN KEY(adjustment_id) REFERENCES adjustments (id)
);

CREATE TABLE erp_postings (
    id SERIAL NOT NULL, 
    journal_id INTEGER NOT NULL, 
    erp_document_number VARCHAR NOT NULL, 
    posted_amount FLOAT NOT NULL, 
    status VARCHAR, 
    posted_at TIMESTAMP WITHOUT TIME ZONE, 
    PRIMARY KEY (id), 
    UNIQUE (erp_document_number), 
    FOREIGN KEY(journal_id) REFERENCES journal_entries (id)
);

CREATE TABLE reconciliations (
    id SERIAL NOT NULL, 
    adjustment_id INTEGER NOT NULL, 
    expected_amount FLOAT NOT NULL, 
    posted_amount FLOAT NOT NULL, 
    difference FLOAT NOT NULL, 
    status VARCHAR NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE, 
    PRIMARY KEY (id), 
    FOREIGN KEY(adjustment_id) REFERENCES adjustments (id)
);

CREATE TABLE audit_events (
    id SERIAL NOT NULL, 
    event_type VARCHAR NOT NULL, 
    actor VARCHAR NOT NULL, 
    entity_code VARCHAR, 
    correlation_id VARCHAR, 
    details TEXT NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE, 
    PRIMARY KEY (id)
);

INSERT INTO alembic_version (version_num) VALUES ('0001_initial') RETURNING alembic_version.version_num;

-- Running upgrade 0001_initial -> 0002_enterprise_rc

CREATE TABLE organizations (
    id SERIAL NOT NULL, 
    code VARCHAR(40) NOT NULL, 
    name VARCHAR(200) NOT NULL, 
    active BOOLEAN DEFAULT true NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (code)
);

CREATE UNIQUE INDEX ix_organizations_code ON organizations (code);

CREATE TABLE workspaces (
    id SERIAL NOT NULL, 
    organization_id INTEGER NOT NULL, 
    code VARCHAR(40) NOT NULL, 
    name VARCHAR(200) NOT NULL, 
    active BOOLEAN DEFAULT true NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_workspace_org_code UNIQUE (organization_id, code), 
    FOREIGN KEY(organization_id) REFERENCES organizations (id)
);

CREATE INDEX ix_workspaces_organization_id ON workspaces (organization_id);

CREATE TABLE clients (
    id SERIAL NOT NULL, 
    workspace_id INTEGER NOT NULL, 
    code VARCHAR(40) NOT NULL, 
    name VARCHAR(200) NOT NULL, 
    active BOOLEAN DEFAULT true NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_client_workspace_code UNIQUE (workspace_id, code), 
    FOREIGN KEY(workspace_id) REFERENCES workspaces (id)
);

CREATE INDEX ix_clients_workspace_id ON clients (workspace_id);

ALTER TABLE users ADD COLUMN workspace_id INTEGER;

ALTER TABLE users ADD FOREIGN KEY(workspace_id) REFERENCES workspaces (id);

CREATE INDEX ix_users_workspace_id ON users (workspace_id);

ALTER TABLE users ADD COLUMN failed_login_count INTEGER DEFAULT '0' NOT NULL;

ALTER TABLE users ADD COLUMN locked_until TIMESTAMP WITHOUT TIME ZONE;

ALTER TABLE users ADD COLUMN last_login_at TIMESTAMP WITHOUT TIME ZONE;

ALTER TABLE users ADD COLUMN token_version INTEGER DEFAULT '1' NOT NULL;

ALTER TABLE users ADD COLUMN created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL;

ALTER TABLE users ADD COLUMN updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL;

ALTER TABLE entities ADD COLUMN workspace_id INTEGER;

ALTER TABLE entities ADD FOREIGN KEY(workspace_id) REFERENCES workspaces (id);

ALTER TABLE entities ADD COLUMN client_id INTEGER;

ALTER TABLE entities ADD FOREIGN KEY(client_id) REFERENCES clients (id);

ALTER TABLE entities ADD COLUMN tax_jurisdiction VARCHAR(80);

ALTER TABLE entities ADD COLUMN group_currency VARCHAR(3) DEFAULT 'EUR' NOT NULL;

ALTER TABLE entities ADD COLUMN erp_system VARCHAR(60) DEFAULT 'DEMO_ERP' NOT NULL;

ALTER TABLE entities ADD COLUMN tax_rate NUMERIC(14, 10);

ALTER TABLE entities ADD COLUMN customs_territory VARCHAR(80);

ALTER TABLE entities ADD COLUMN active BOOLEAN DEFAULT true NOT NULL;

ALTER TABLE entities ADD COLUMN effective_from VARCHAR(10);

ALTER TABLE entities ADD COLUMN effective_to VARCHAR(10);

ALTER TABLE entities ADD COLUMN created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL;

ALTER TABLE entities ADD COLUMN updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL;

CREATE INDEX ix_entities_workspace_id ON entities (workspace_id);

CREATE INDEX ix_entities_client_id ON entities (client_id);

ALTER TABLE entities DROP CONSTRAINT entities_entity_code_key;

ALTER TABLE entities ADD CONSTRAINT uq_entity_workspace_code UNIQUE (workspace_id, entity_code);

ALTER TABLE tp_policies ADD COLUMN workspace_id INTEGER;

ALTER TABLE tp_policies ADD FOREIGN KEY(workspace_id) REFERENCES workspaces (id);

ALTER TABLE tp_policies ADD COLUMN counterparty_code VARCHAR(60);

ALTER TABLE tp_policies ADD COLUMN transaction_type VARCHAR(120) DEFAULT 'DISTRIBUTION' NOT NULL;

ALTER TABLE tp_policies ADD COLUMN median NUMERIC(14, 10);

ALTER TABLE tp_policies ADD COLUMN markup NUMERIC(14, 10);

ALTER TABLE tp_policies ADD COLUMN effective_from VARCHAR(10);

ALTER TABLE tp_policies ADD COLUMN effective_to VARCHAR(10);

ALTER TABLE tp_policies ADD COLUMN true_up_frequency VARCHAR(40);

ALTER TABLE tp_policies ADD COLUMN materiality_threshold NUMERIC(20, 6) DEFAULT '0' NOT NULL;

ALTER TABLE tp_policies ADD COLUMN approval_matrix JSON;

ALTER TABLE tp_policies ADD COLUMN document_references JSON;

ALTER TABLE tp_policies ADD COLUMN created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL;

ALTER TABLE tp_policies ADD COLUMN updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL;

CREATE INDEX ix_tp_policies_workspace_id ON tp_policies (workspace_id);

ALTER TABLE tp_policies DROP CONSTRAINT tp_policies_policy_code_key;

ALTER TABLE tp_policies ADD CONSTRAINT uq_policy_workspace_code_version UNIQUE (workspace_id, policy_code, version);

ALTER TABLE tp_policies ALTER COLUMN target TYPE NUMERIC(14, 10) USING target::numeric;

ALTER TABLE tp_policies ALTER COLUMN lower_bound TYPE NUMERIC(14, 10) USING lower_bound::numeric;

ALTER TABLE tp_policies ALTER COLUMN upper_bound TYPE NUMERIC(14, 10) USING upper_bound::numeric;

ALTER TABLE financial_periods ADD COLUMN workspace_id INTEGER;

ALTER TABLE financial_periods ADD FOREIGN KEY(workspace_id) REFERENCES workspaces (id);

ALTER TABLE financial_periods ADD COLUMN created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL;

ALTER TABLE financial_periods ADD COLUMN updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL;

CREATE INDEX ix_financial_periods_workspace_id ON financial_periods (workspace_id);

ALTER TABLE financial_periods ALTER COLUMN revenue TYPE NUMERIC(20, 6) USING revenue::numeric;

ALTER TABLE financial_periods ALTER COLUMN cogs TYPE NUMERIC(20, 6) USING cogs::numeric;

ALTER TABLE financial_periods ALTER COLUMN opex TYPE NUMERIC(20, 6) USING opex::numeric;

ALTER TABLE financial_periods ALTER COLUMN forecast_ros TYPE NUMERIC(14, 10) USING forecast_ros::numeric;

ALTER TABLE calculations ADD COLUMN workspace_id INTEGER;

ALTER TABLE calculations ADD FOREIGN KEY(workspace_id) REFERENCES workspaces (id);

ALTER TABLE calculations ADD COLUMN manifest JSON;

ALTER TABLE calculations ADD COLUMN finalized BOOLEAN DEFAULT false NOT NULL;

ALTER TABLE calculations ADD COLUMN updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL;

CREATE INDEX ix_calculations_workspace_id ON calculations (workspace_id);

ALTER TABLE calculations ALTER COLUMN revenue TYPE NUMERIC(20, 6) USING revenue::numeric;

ALTER TABLE calculations ALTER COLUMN ebit TYPE NUMERIC(20, 6) USING ebit::numeric;

ALTER TABLE calculations ALTER COLUMN suggested_adjustment TYPE NUMERIC(20, 6) USING suggested_adjustment::numeric;

ALTER TABLE calculations ALTER COLUMN actual_pli TYPE NUMERIC(14, 10) USING actual_pli::numeric;

ALTER TABLE calculations ALTER COLUMN target_pli TYPE NUMERIC(14, 10) USING target_pli::numeric;

ALTER TABLE adjustments ADD COLUMN workspace_id INTEGER;

ALTER TABLE adjustments ADD FOREIGN KEY(workspace_id) REFERENCES workspaces (id);

ALTER TABLE adjustments ADD COLUMN currency VARCHAR(3) DEFAULT 'EUR' NOT NULL;

ALTER TABLE adjustments ADD COLUMN version INTEGER DEFAULT '1' NOT NULL;

ALTER TABLE adjustments ADD COLUMN locked_at TIMESTAMP WITHOUT TIME ZONE;

ALTER TABLE adjustments ADD COLUMN materiality NUMERIC(20, 6) DEFAULT '0' NOT NULL;

ALTER TABLE adjustments ADD COLUMN updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL;

CREATE INDEX ix_adjustments_workspace_id ON adjustments (workspace_id);

ALTER TABLE adjustments ALTER COLUMN amount TYPE NUMERIC(20, 6) USING amount::numeric;

ALTER TABLE journal_entries ALTER COLUMN debit TYPE NUMERIC(20, 6) USING debit::numeric;

ALTER TABLE journal_entries ALTER COLUMN credit TYPE NUMERIC(20, 6) USING credit::numeric;

ALTER TABLE erp_postings ADD COLUMN workspace_id INTEGER;

ALTER TABLE erp_postings ADD FOREIGN KEY(workspace_id) REFERENCES workspaces (id);

ALTER TABLE erp_postings ADD COLUMN journal_header_id INTEGER;

ALTER TABLE erp_postings ADD COLUMN idempotency_key VARCHAR(120);

ALTER TABLE erp_postings ADD COLUMN erp_system VARCHAR(60) DEFAULT 'SAP_SIMULATOR' NOT NULL;

ALTER TABLE erp_postings ADD COLUMN created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL;

ALTER TABLE erp_postings ADD COLUMN updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL;

ALTER TABLE erp_postings ADD CONSTRAINT uq_erp_postings_idempotency_key UNIQUE (idempotency_key);

CREATE INDEX ix_erp_postings_workspace_id ON erp_postings (workspace_id);

ALTER TABLE erp_postings ALTER COLUMN posted_amount TYPE NUMERIC(20, 6) USING posted_amount::numeric;

ALTER TABLE reconciliations ADD COLUMN workspace_id INTEGER;

ALTER TABLE reconciliations ADD FOREIGN KEY(workspace_id) REFERENCES workspaces (id);

ALTER TABLE reconciliations ADD COLUMN approved_amount NUMERIC(20, 6);

ALTER TABLE reconciliations ADD COLUMN journal_amount NUMERIC(20, 6);

ALTER TABLE reconciliations ADD COLUMN final_pnl_impact NUMERIC(20, 6);

ALTER TABLE reconciliations ADD COLUMN tolerance NUMERIC(20, 6) DEFAULT '0.01' NOT NULL;

ALTER TABLE reconciliations ADD COLUMN updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL;

CREATE INDEX ix_reconciliations_workspace_id ON reconciliations (workspace_id);

ALTER TABLE reconciliations ALTER COLUMN expected_amount TYPE NUMERIC(20, 6) USING expected_amount::numeric;

ALTER TABLE reconciliations ALTER COLUMN posted_amount TYPE NUMERIC(20, 6) USING posted_amount::numeric;

ALTER TABLE reconciliations ALTER COLUMN difference TYPE NUMERIC(20, 6) USING difference::numeric;

ALTER TABLE audit_events ADD COLUMN workspace_id INTEGER;

ALTER TABLE audit_events ADD FOREIGN KEY(workspace_id) REFERENCES workspaces (id);

ALTER TABLE audit_events ADD COLUMN actor_role VARCHAR(64);

ALTER TABLE audit_events ADD COLUMN object_type VARCHAR(80);

ALTER TABLE audit_events ADD COLUMN object_id VARCHAR(120);

ALTER TABLE audit_events ADD COLUMN previous_value JSON;

ALTER TABLE audit_events ADD COLUMN new_value JSON;

ALTER TABLE audit_events ADD COLUMN reason TEXT;

ALTER TABLE audit_events ADD COLUMN request_id VARCHAR(100);

ALTER TABLE audit_events ADD COLUMN source_system VARCHAR(80);

CREATE INDEX ix_audit_events_workspace_id ON audit_events (workspace_id);

CREATE INDEX ix_audit_events_event_type ON audit_events (event_type);

CREATE INDEX ix_audit_events_correlation_id ON audit_events (correlation_id);

CREATE TABLE intercompany_partners (
    id SERIAL NOT NULL, 
    workspace_id INTEGER NOT NULL, 
    partner_code VARCHAR(60) NOT NULL, 
    entity_id INTEGER, 
    trading_partner_code VARCHAR(60), 
    vendor_code VARCHAR(60), 
    customer_code VARCHAR(60), 
    country VARCHAR(2), 
    relationship_type VARCHAR(80), 
    effective_from VARCHAR(10), 
    effective_to VARCHAR(10), 
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_partner_workspace_code UNIQUE (workspace_id, partner_code), 
    FOREIGN KEY(workspace_id) REFERENCES workspaces (id), 
    FOREIGN KEY(entity_id) REFERENCES entities (id)
);

CREATE INDEX ix_intercompany_partners_workspace_id ON intercompany_partners (workspace_id);

CREATE TABLE gl_accounts (
    id SERIAL NOT NULL, 
    workspace_id INTEGER NOT NULL, 
    account_code VARCHAR(40) NOT NULL, 
    description VARCHAR(200) NOT NULL, 
    classification VARCHAR(60) NOT NULL, 
    operating BOOLEAN NOT NULL, 
    pli_included BOOLEAN NOT NULL, 
    cost_plus_eligible BOOLEAN NOT NULL, 
    allocation_eligible BOOLEAN NOT NULL, 
    exceptional_item BOOLEAN NOT NULL, 
    pass_through BOOLEAN NOT NULL, 
    effective_from VARCHAR(10), 
    effective_to VARCHAR(10), 
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_gl_workspace_code UNIQUE (workspace_id, account_code), 
    FOREIGN KEY(workspace_id) REFERENCES workspaces (id)
);

CREATE INDEX ix_gl_accounts_workspace_id ON gl_accounts (workspace_id);

CREATE TABLE profit_centers (
    id SERIAL NOT NULL, 
    workspace_id INTEGER NOT NULL, 
    code VARCHAR(60) NOT NULL, 
    entity_id INTEGER NOT NULL, 
    function VARCHAR(120), 
    business_unit VARCHAR(120), 
    geography VARCHAR(120), 
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_pc_workspace_code UNIQUE (workspace_id, code), 
    FOREIGN KEY(workspace_id) REFERENCES workspaces (id), 
    FOREIGN KEY(entity_id) REFERENCES entities (id)
);

CREATE INDEX ix_profit_centers_workspace_id ON profit_centers (workspace_id);

CREATE INDEX ix_profit_centers_entity_id ON profit_centers (entity_id);

CREATE TABLE products (
    id SERIAL NOT NULL, 
    workspace_id INTEGER NOT NULL, 
    sku VARCHAR(80) NOT NULL, 
    product_group VARCHAR(120), 
    entity_id INTEGER, 
    standard_cost NUMERIC(20, 6), 
    currency VARCHAR(3), 
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_product_workspace_sku UNIQUE (workspace_id, sku), 
    FOREIGN KEY(workspace_id) REFERENCES workspaces (id), 
    FOREIGN KEY(entity_id) REFERENCES entities (id)
);

CREATE INDEX ix_products_workspace_id ON products (workspace_id);

CREATE TABLE user_entity_access (
    id SERIAL NOT NULL, 
    user_id INTEGER NOT NULL, 
    entity_id INTEGER NOT NULL, 
    can_read BOOLEAN DEFAULT true NOT NULL, 
    can_write BOOLEAN DEFAULT false NOT NULL, 
    can_approve BOOLEAN DEFAULT false NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_user_entity_access UNIQUE (user_id, entity_id), 
    FOREIGN KEY(user_id) REFERENCES users (id), 
    FOREIGN KEY(entity_id) REFERENCES entities (id)
);

CREATE TABLE source_imports (
    id SERIAL NOT NULL, 
    import_code VARCHAR(100) NOT NULL, 
    workspace_id INTEGER NOT NULL, 
    entity_id INTEGER, 
    source_system VARCHAR(80) NOT NULL, 
    period VARCHAR(20) NOT NULL, 
    filename VARCHAR(255) NOT NULL, 
    sha256 VARCHAR(64) NOT NULL, 
    row_count INTEGER DEFAULT '0' NOT NULL, 
    accepted_rows INTEGER DEFAULT '0' NOT NULL, 
    rejected_rows INTEGER DEFAULT '0' NOT NULL, 
    warning_rows INTEGER DEFAULT '0' NOT NULL, 
    source_control_total NUMERIC(20, 6) DEFAULT '0' NOT NULL, 
    imported_control_total NUMERIC(20, 6) DEFAULT '0' NOT NULL, 
    status VARCHAR(30) NOT NULL, 
    schema_version VARCHAR(30) NOT NULL, 
    original_path VARCHAR(500), 
    actor VARCHAR(320), 
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (import_code), 
    FOREIGN KEY(workspace_id) REFERENCES workspaces (id), 
    FOREIGN KEY(entity_id) REFERENCES entities (id)
);

CREATE INDEX ix_source_imports_workspace_id ON source_imports (workspace_id);

CREATE INDEX ix_source_imports_entity_id ON source_imports (entity_id);

CREATE TABLE raw_financial_records (
    id SERIAL NOT NULL, 
    workspace_id INTEGER NOT NULL, 
    source_import_id INTEGER NOT NULL, 
    row_number INTEGER NOT NULL, 
    period VARCHAR(20) NOT NULL, 
    entity_code VARCHAR(40) NOT NULL, 
    company_code VARCHAR(40), 
    document_number VARCHAR(100), 
    gl_account VARCHAR(40) NOT NULL, 
    cost_center VARCHAR(60), 
    profit_center VARCHAR(60), 
    counterparty_code VARCHAR(60), 
    product_sku VARCHAR(80), 
    product_group VARCHAR(120), 
    currency VARCHAR(3) NOT NULL, 
    amount NUMERIC(20, 6) NOT NULL, 
    debit_credit VARCHAR(10), 
    validation_status VARCHAR(30) NOT NULL, 
    validation_messages JSON, 
    raw_payload JSON, 
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_import_row_number UNIQUE (source_import_id, row_number), 
    FOREIGN KEY(workspace_id) REFERENCES workspaces (id), 
    FOREIGN KEY(source_import_id) REFERENCES source_imports (id)
);

CREATE INDEX ix_raw_workspace ON raw_financial_records (workspace_id);

CREATE INDEX ix_raw_import ON raw_financial_records (source_import_id);

CREATE INDEX ix_raw_period ON raw_financial_records (period);

CREATE INDEX ix_raw_entity ON raw_financial_records (entity_code);

CREATE INDEX ix_raw_gl ON raw_financial_records (gl_account);

CREATE TABLE mapping_rules (
    id SERIAL NOT NULL, 
    workspace_id INTEGER NOT NULL, 
    rule_code VARCHAR(80) NOT NULL, 
    version INTEGER NOT NULL, 
    priority INTEGER NOT NULL, 
    match_fields JSON NOT NULL, 
    segment_code VARCHAR(80) NOT NULL, 
    controlled_transaction_code VARCHAR(80) NOT NULL, 
    policy_code VARCHAR(80) NOT NULL, 
    effective_from VARCHAR(10), 
    effective_to VARCHAR(10), 
    status VARCHAR(30) NOT NULL, 
    approved_by VARCHAR(320), 
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_mapping_rule_version UNIQUE (workspace_id, rule_code, version), 
    FOREIGN KEY(workspace_id) REFERENCES workspaces (id)
);

CREATE INDEX ix_mapping_rules_workspace_id ON mapping_rules (workspace_id);

CREATE INDEX ix_mapping_priority ON mapping_rules (workspace_id, priority);

CREATE TABLE normalized_financial_records (
    id SERIAL NOT NULL, 
    workspace_id INTEGER NOT NULL, 
    raw_record_id INTEGER NOT NULL, 
    entity_id INTEGER NOT NULL, 
    period VARCHAR(20) NOT NULL, 
    gl_account VARCHAR(40) NOT NULL, 
    counterparty_code VARCHAR(60), 
    profit_center VARCHAR(60), 
    product_sku VARCHAR(80), 
    product_group VARCHAR(120), 
    currency VARCHAR(3) NOT NULL, 
    amount NUMERIC(20, 6) NOT NULL, 
    financial_classification VARCHAR(60) NOT NULL, 
    segment_code VARCHAR(80) NOT NULL, 
    controlled_transaction_code VARCHAR(80) NOT NULL, 
    policy_code VARCHAR(80) NOT NULL, 
    mapping_rule_id INTEGER NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(workspace_id) REFERENCES workspaces (id), 
    UNIQUE (raw_record_id), 
    FOREIGN KEY(raw_record_id) REFERENCES raw_financial_records (id), 
    FOREIGN KEY(entity_id) REFERENCES entities (id), 
    FOREIGN KEY(mapping_rule_id) REFERENCES mapping_rules (id)
);

CREATE INDEX ix_norm_workspace ON normalized_financial_records (workspace_id);

CREATE INDEX ix_norm_entity ON normalized_financial_records (entity_id);

CREATE INDEX ix_norm_period ON normalized_financial_records (period);

CREATE INDEX ix_norm_segment ON normalized_financial_records (segment_code);

CREATE TABLE allocation_rules (
    id SERIAL NOT NULL, 
    workspace_id INTEGER NOT NULL, 
    rule_code VARCHAR(80) NOT NULL, 
    version INTEGER NOT NULL, 
    sender_segment VARCHAR(80) NOT NULL, 
    cost_pool_name VARCHAR(120) NOT NULL, 
    driver_type VARCHAR(60) NOT NULL, 
    recipients JSON NOT NULL, 
    exclusions JSON, 
    markup_eligible BOOLEAN NOT NULL, 
    status VARCHAR(30) NOT NULL, 
    approved_by VARCHAR(320), 
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_allocation_rule_version UNIQUE (workspace_id, rule_code, version), 
    FOREIGN KEY(workspace_id) REFERENCES workspaces (id)
);

CREATE INDEX ix_allocation_rules_workspace_id ON allocation_rules (workspace_id);

CREATE TABLE allocation_runs (
    id SERIAL NOT NULL, 
    workspace_id INTEGER NOT NULL, 
    run_code VARCHAR(100) NOT NULL, 
    rule_id INTEGER NOT NULL, 
    period VARCHAR(20) NOT NULL, 
    source_amount NUMERIC(20, 6) NOT NULL, 
    allocated_amount NUMERIC(20, 6) NOT NULL, 
    residual NUMERIC(20, 6) NOT NULL, 
    status VARCHAR(30) NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(workspace_id) REFERENCES workspaces (id), 
    UNIQUE (run_code), 
    FOREIGN KEY(rule_id) REFERENCES allocation_rules (id)
);

CREATE TABLE allocation_results (
    id SERIAL NOT NULL, 
    allocation_run_id INTEGER NOT NULL, 
    recipient_segment VARCHAR(80) NOT NULL, 
    driver_value NUMERIC(20, 6) NOT NULL, 
    driver_share NUMERIC(14, 10) NOT NULL, 
    allocated_amount NUMERIC(20, 6) NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(allocation_run_id) REFERENCES allocation_runs (id)
);

CREATE TABLE forecast_versions (
    id SERIAL NOT NULL, 
    workspace_id INTEGER NOT NULL, 
    version_code VARCHAR(80) NOT NULL, 
    scenario VARCHAR(40) NOT NULL, 
    fiscal_year INTEGER NOT NULL, 
    status VARCHAR(30) NOT NULL, 
    approved_by VARCHAR(320), 
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_forecast_workspace_version UNIQUE (workspace_id, version_code), 
    FOREIGN KEY(workspace_id) REFERENCES workspaces (id)
);

CREATE TABLE forecast_lines (
    id SERIAL NOT NULL, 
    forecast_version_id INTEGER NOT NULL, 
    entity_id INTEGER NOT NULL, 
    month INTEGER NOT NULL, 
    revenue NUMERIC(20, 6) NOT NULL, 
    cogs NUMERIC(20, 6) NOT NULL, 
    opex NUMERIC(20, 6) NOT NULL, 
    currency VARCHAR(3) NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_forecast_line UNIQUE (forecast_version_id, entity_id, month), 
    CONSTRAINT ck_forecast_month CHECK (month >= 1 AND month <= 12), 
    FOREIGN KEY(forecast_version_id) REFERENCES forecast_versions (id), 
    FOREIGN KEY(entity_id) REFERENCES entities (id)
);

CREATE TABLE simulations (
    id SERIAL NOT NULL, 
    workspace_id INTEGER NOT NULL, 
    simulation_code VARCHAR(100) NOT NULL, 
    entity_id INTEGER NOT NULL, 
    period VARCHAR(20) NOT NULL, 
    inputs JSON NOT NULL, 
    outputs JSON NOT NULL, 
    created_by VARCHAR(320) NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(workspace_id) REFERENCES workspaces (id), 
    UNIQUE (simulation_code), 
    FOREIGN KEY(entity_id) REFERENCES entities (id)
);

CREATE TABLE approval_requests (
    id SERIAL NOT NULL, 
    workspace_id INTEGER NOT NULL, 
    adjustment_id INTEGER NOT NULL, 
    current_step INTEGER NOT NULL, 
    status VARCHAR(30) NOT NULL, 
    created_by VARCHAR(320) NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(workspace_id) REFERENCES workspaces (id), 
    UNIQUE (adjustment_id), 
    FOREIGN KEY(adjustment_id) REFERENCES adjustments (id)
);

CREATE TABLE approval_steps (
    id SERIAL NOT NULL, 
    approval_request_id INTEGER NOT NULL, 
    step_order INTEGER NOT NULL, 
    required_role VARCHAR(64) NOT NULL, 
    status VARCHAR(30) NOT NULL, 
    actor VARCHAR(320), 
    comments TEXT, 
    decided_at TIMESTAMP WITHOUT TIME ZONE, 
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_approval_step_order UNIQUE (approval_request_id, step_order), 
    FOREIGN KEY(approval_request_id) REFERENCES approval_requests (id)
);

CREATE TABLE journal_headers (
    id SERIAL NOT NULL, 
    workspace_id INTEGER NOT NULL, 
    journal_code VARCHAR(120) NOT NULL, 
    adjustment_id INTEGER NOT NULL, 
    company_code VARCHAR(40) NOT NULL, 
    ledger VARCHAR(20) NOT NULL, 
    document_type VARCHAR(20) NOT NULL, 
    posting_date VARCHAR(10) NOT NULL, 
    document_date VARCHAR(10) NOT NULL, 
    currency VARCHAR(3) NOT NULL, 
    reference VARCHAR(120) NOT NULL, 
    status VARCHAR(30) NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(workspace_id) REFERENCES workspaces (id), 
    UNIQUE (journal_code), 
    UNIQUE (adjustment_id), 
    FOREIGN KEY(adjustment_id) REFERENCES adjustments (id)
);

CREATE TABLE journal_lines (
    id SERIAL NOT NULL, 
    journal_id INTEGER NOT NULL, 
    line_no INTEGER NOT NULL, 
    gl_account VARCHAR(40) NOT NULL, 
    debit_credit VARCHAR(10) NOT NULL, 
    amount NUMERIC(20, 6) NOT NULL, 
    currency VARCHAR(3) NOT NULL, 
    profit_center VARCHAR(60), 
    cost_center VARCHAR(60), 
    trading_partner VARCHAR(60), 
    assignment VARCHAR(120), 
    text VARCHAR(255), 
    tax_code VARCHAR(20), 
    PRIMARY KEY (id), 
    CONSTRAINT uq_journal_line_no UNIQUE (journal_id, line_no), 
    CONSTRAINT ck_journal_dc CHECK (debit_credit in ('DEBIT','CREDIT')), 
    FOREIGN KEY(journal_id) REFERENCES journal_headers (id)
);

ALTER TABLE erp_postings ADD CONSTRAINT fk_erp_postings_journal_header FOREIGN KEY(journal_header_id) REFERENCES journal_headers (id);

CREATE INDEX ix_erp_postings_journal_header_id ON erp_postings (journal_header_id);

CREATE TABLE posting_attempts (
    id SERIAL NOT NULL, 
    posting_id INTEGER NOT NULL, 
    attempt_no INTEGER NOT NULL, 
    request_payload JSON, 
    response_payload JSON, 
    status VARCHAR(30) NOT NULL, 
    error_message TEXT, 
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_posting_attempt UNIQUE (posting_id, attempt_no), 
    FOREIGN KEY(posting_id) REFERENCES erp_postings (id)
);

CREATE TABLE exceptions (
    id SERIAL NOT NULL, 
    workspace_id INTEGER NOT NULL, 
    exception_code VARCHAR(120) NOT NULL, 
    entity_id INTEGER, 
    category VARCHAR(80) NOT NULL, 
    severity VARCHAR(20) NOT NULL, 
    amount NUMERIC(20, 6), 
    owner VARCHAR(320), 
    due_date VARCHAR(10), 
    status VARCHAR(30) NOT NULL, 
    evidence JSON, 
    resolution TEXT, 
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(workspace_id) REFERENCES workspaces (id), 
    UNIQUE (exception_code), 
    FOREIGN KEY(entity_id) REFERENCES entities (id)
);

CREATE TABLE documents (
    id SERIAL NOT NULL, 
    workspace_id INTEGER NOT NULL, 
    document_code VARCHAR(120) NOT NULL, 
    version INTEGER NOT NULL, 
    entity_id INTEGER, 
    country VARCHAR(2), 
    period VARCHAR(20), 
    document_type VARCHAR(80) NOT NULL, 
    effective_date VARCHAR(10), 
    status VARCHAR(30) NOT NULL, 
    sha256 VARCHAR(64) NOT NULL, 
    uploader VARCHAR(320) NOT NULL, 
    access_classification VARCHAR(40) NOT NULL, 
    storage_key VARCHAR(500) NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_document_version UNIQUE (workspace_id, document_code, version), 
    FOREIGN KEY(workspace_id) REFERENCES workspaces (id), 
    FOREIGN KEY(entity_id) REFERENCES entities (id)
);

CREATE TABLE evidence_chunks (
    id SERIAL NOT NULL, 
    document_id INTEGER NOT NULL, 
    chunk_no INTEGER NOT NULL, 
    content TEXT NOT NULL, 
    metadata_json JSON, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_evidence_chunk UNIQUE (document_id, chunk_no), 
    FOREIGN KEY(document_id) REFERENCES documents (id)
);

CREATE TABLE ai_invocations (
    id SERIAL NOT NULL, 
    workspace_id INTEGER NOT NULL, 
    user_email VARCHAR(320) NOT NULL, 
    provider VARCHAR(80) NOT NULL, 
    model VARCHAR(120) NOT NULL, 
    prompt_version VARCHAR(40) NOT NULL, 
    retrieval_context JSON, 
    response_text TEXT NOT NULL, 
    citations JSON, 
    review_status VARCHAR(30) NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(workspace_id) REFERENCES workspaces (id)
);

CREATE TABLE integration_connections (
    id SERIAL NOT NULL, 
    workspace_id INTEGER NOT NULL, 
    connection_code VARCHAR(80) NOT NULL, 
    connector_type VARCHAR(80) NOT NULL, 
    config JSON, 
    secret_reference VARCHAR(255), 
    status VARCHAR(30) NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_integration_connection UNIQUE (workspace_id, connection_code), 
    FOREIGN KEY(workspace_id) REFERENCES workspaces (id)
);

CREATE TABLE integration_runs (
    id SERIAL NOT NULL, 
    connection_id INTEGER NOT NULL, 
    run_code VARCHAR(100) NOT NULL, 
    correlation_id VARCHAR(100) NOT NULL, 
    status VARCHAR(30) NOT NULL, 
    records_processed INTEGER NOT NULL, 
    error_message TEXT, 
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(connection_id) REFERENCES integration_connections (id), 
    UNIQUE (run_code)
);

CREATE TABLE workflow_runs (
    id SERIAL NOT NULL, 
    workspace_id INTEGER NOT NULL, 
    workflow_name VARCHAR(120) NOT NULL, 
    correlation_id VARCHAR(100) NOT NULL, 
    status VARCHAR(30) NOT NULL, 
    payload JSON, 
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(workspace_id) REFERENCES workspaces (id), 
    UNIQUE (correlation_id)
);

CREATE TABLE notifications (
    id SERIAL NOT NULL, 
    workspace_id INTEGER NOT NULL, 
    recipient VARCHAR(320) NOT NULL, 
    channel VARCHAR(30) NOT NULL, 
    subject VARCHAR(200) NOT NULL, 
    body TEXT NOT NULL, 
    status VARCHAR(30) NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(workspace_id) REFERENCES workspaces (id)
);

UPDATE alembic_version SET version_num='0002_enterprise_rc' WHERE alembic_version.version_num = '0001_initial';

-- Running upgrade 0002_enterprise_rc -> 0003_rls_policies

ALTER TABLE entities ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS entities_workspace_policy ON entities;

CREATE POLICY entities_workspace_policy ON entities USING (workspace_id = NULLIF(current_setting('app.workspace_id', true),'')::integer) WITH CHECK (workspace_id = NULLIF(current_setting('app.workspace_id', true),'')::integer);

ALTER TABLE tp_policies ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tp_policies_workspace_policy ON tp_policies;

CREATE POLICY tp_policies_workspace_policy ON tp_policies USING (workspace_id = NULLIF(current_setting('app.workspace_id', true),'')::integer) WITH CHECK (workspace_id = NULLIF(current_setting('app.workspace_id', true),'')::integer);

ALTER TABLE financial_periods ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS financial_periods_workspace_policy ON financial_periods;

CREATE POLICY financial_periods_workspace_policy ON financial_periods USING (workspace_id = NULLIF(current_setting('app.workspace_id', true),'')::integer) WITH CHECK (workspace_id = NULLIF(current_setting('app.workspace_id', true),'')::integer);

ALTER TABLE calculations ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS calculations_workspace_policy ON calculations;

CREATE POLICY calculations_workspace_policy ON calculations USING (workspace_id = NULLIF(current_setting('app.workspace_id', true),'')::integer) WITH CHECK (workspace_id = NULLIF(current_setting('app.workspace_id', true),'')::integer);

ALTER TABLE adjustments ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS adjustments_workspace_policy ON adjustments;

CREATE POLICY adjustments_workspace_policy ON adjustments USING (workspace_id = NULLIF(current_setting('app.workspace_id', true),'')::integer) WITH CHECK (workspace_id = NULLIF(current_setting('app.workspace_id', true),'')::integer);

ALTER TABLE erp_postings ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS erp_postings_workspace_policy ON erp_postings;

CREATE POLICY erp_postings_workspace_policy ON erp_postings USING (workspace_id = NULLIF(current_setting('app.workspace_id', true),'')::integer) WITH CHECK (workspace_id = NULLIF(current_setting('app.workspace_id', true),'')::integer);

ALTER TABLE reconciliations ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS reconciliations_workspace_policy ON reconciliations;

CREATE POLICY reconciliations_workspace_policy ON reconciliations USING (workspace_id = NULLIF(current_setting('app.workspace_id', true),'')::integer) WITH CHECK (workspace_id = NULLIF(current_setting('app.workspace_id', true),'')::integer);

ALTER TABLE audit_events ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS audit_events_workspace_policy ON audit_events;

CREATE POLICY audit_events_workspace_policy ON audit_events USING (workspace_id = NULLIF(current_setting('app.workspace_id', true),'')::integer) WITH CHECK (workspace_id = NULLIF(current_setting('app.workspace_id', true),'')::integer);

ALTER TABLE intercompany_partners ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS intercompany_partners_workspace_policy ON intercompany_partners;

CREATE POLICY intercompany_partners_workspace_policy ON intercompany_partners USING (workspace_id = NULLIF(current_setting('app.workspace_id', true),'')::integer) WITH CHECK (workspace_id = NULLIF(current_setting('app.workspace_id', true),'')::integer);

ALTER TABLE gl_accounts ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS gl_accounts_workspace_policy ON gl_accounts;

CREATE POLICY gl_accounts_workspace_policy ON gl_accounts USING (workspace_id = NULLIF(current_setting('app.workspace_id', true),'')::integer) WITH CHECK (workspace_id = NULLIF(current_setting('app.workspace_id', true),'')::integer);

ALTER TABLE profit_centers ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS profit_centers_workspace_policy ON profit_centers;

CREATE POLICY profit_centers_workspace_policy ON profit_centers USING (workspace_id = NULLIF(current_setting('app.workspace_id', true),'')::integer) WITH CHECK (workspace_id = NULLIF(current_setting('app.workspace_id', true),'')::integer);

ALTER TABLE products ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS products_workspace_policy ON products;

CREATE POLICY products_workspace_policy ON products USING (workspace_id = NULLIF(current_setting('app.workspace_id', true),'')::integer) WITH CHECK (workspace_id = NULLIF(current_setting('app.workspace_id', true),'')::integer);

ALTER TABLE source_imports ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS source_imports_workspace_policy ON source_imports;

CREATE POLICY source_imports_workspace_policy ON source_imports USING (workspace_id = NULLIF(current_setting('app.workspace_id', true),'')::integer) WITH CHECK (workspace_id = NULLIF(current_setting('app.workspace_id', true),'')::integer);

ALTER TABLE raw_financial_records ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS raw_financial_records_workspace_policy ON raw_financial_records;

CREATE POLICY raw_financial_records_workspace_policy ON raw_financial_records USING (workspace_id = NULLIF(current_setting('app.workspace_id', true),'')::integer) WITH CHECK (workspace_id = NULLIF(current_setting('app.workspace_id', true),'')::integer);

ALTER TABLE mapping_rules ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS mapping_rules_workspace_policy ON mapping_rules;

CREATE POLICY mapping_rules_workspace_policy ON mapping_rules USING (workspace_id = NULLIF(current_setting('app.workspace_id', true),'')::integer) WITH CHECK (workspace_id = NULLIF(current_setting('app.workspace_id', true),'')::integer);

ALTER TABLE normalized_financial_records ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS normalized_financial_records_workspace_policy ON normalized_financial_records;

CREATE POLICY normalized_financial_records_workspace_policy ON normalized_financial_records USING (workspace_id = NULLIF(current_setting('app.workspace_id', true),'')::integer) WITH CHECK (workspace_id = NULLIF(current_setting('app.workspace_id', true),'')::integer);

ALTER TABLE allocation_rules ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS allocation_rules_workspace_policy ON allocation_rules;

CREATE POLICY allocation_rules_workspace_policy ON allocation_rules USING (workspace_id = NULLIF(current_setting('app.workspace_id', true),'')::integer) WITH CHECK (workspace_id = NULLIF(current_setting('app.workspace_id', true),'')::integer);

ALTER TABLE allocation_runs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS allocation_runs_workspace_policy ON allocation_runs;

CREATE POLICY allocation_runs_workspace_policy ON allocation_runs USING (workspace_id = NULLIF(current_setting('app.workspace_id', true),'')::integer) WITH CHECK (workspace_id = NULLIF(current_setting('app.workspace_id', true),'')::integer);

ALTER TABLE forecast_versions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS forecast_versions_workspace_policy ON forecast_versions;

CREATE POLICY forecast_versions_workspace_policy ON forecast_versions USING (workspace_id = NULLIF(current_setting('app.workspace_id', true),'')::integer) WITH CHECK (workspace_id = NULLIF(current_setting('app.workspace_id', true),'')::integer);

ALTER TABLE simulations ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS simulations_workspace_policy ON simulations;

CREATE POLICY simulations_workspace_policy ON simulations USING (workspace_id = NULLIF(current_setting('app.workspace_id', true),'')::integer) WITH CHECK (workspace_id = NULLIF(current_setting('app.workspace_id', true),'')::integer);

ALTER TABLE approval_requests ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS approval_requests_workspace_policy ON approval_requests;

CREATE POLICY approval_requests_workspace_policy ON approval_requests USING (workspace_id = NULLIF(current_setting('app.workspace_id', true),'')::integer) WITH CHECK (workspace_id = NULLIF(current_setting('app.workspace_id', true),'')::integer);

ALTER TABLE journal_headers ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS journal_headers_workspace_policy ON journal_headers;

CREATE POLICY journal_headers_workspace_policy ON journal_headers USING (workspace_id = NULLIF(current_setting('app.workspace_id', true),'')::integer) WITH CHECK (workspace_id = NULLIF(current_setting('app.workspace_id', true),'')::integer);

ALTER TABLE exceptions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS exceptions_workspace_policy ON exceptions;

CREATE POLICY exceptions_workspace_policy ON exceptions USING (workspace_id = NULLIF(current_setting('app.workspace_id', true),'')::integer) WITH CHECK (workspace_id = NULLIF(current_setting('app.workspace_id', true),'')::integer);

ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS documents_workspace_policy ON documents;

CREATE POLICY documents_workspace_policy ON documents USING (workspace_id = NULLIF(current_setting('app.workspace_id', true),'')::integer) WITH CHECK (workspace_id = NULLIF(current_setting('app.workspace_id', true),'')::integer);

ALTER TABLE ai_invocations ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS ai_invocations_workspace_policy ON ai_invocations;

CREATE POLICY ai_invocations_workspace_policy ON ai_invocations USING (workspace_id = NULLIF(current_setting('app.workspace_id', true),'')::integer) WITH CHECK (workspace_id = NULLIF(current_setting('app.workspace_id', true),'')::integer);

ALTER TABLE integration_connections ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS integration_connections_workspace_policy ON integration_connections;

CREATE POLICY integration_connections_workspace_policy ON integration_connections USING (workspace_id = NULLIF(current_setting('app.workspace_id', true),'')::integer) WITH CHECK (workspace_id = NULLIF(current_setting('app.workspace_id', true),'')::integer);

ALTER TABLE workflow_runs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS workflow_runs_workspace_policy ON workflow_runs;

CREATE POLICY workflow_runs_workspace_policy ON workflow_runs USING (workspace_id = NULLIF(current_setting('app.workspace_id', true),'')::integer) WITH CHECK (workspace_id = NULLIF(current_setting('app.workspace_id', true),'')::integer);

ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS notifications_workspace_policy ON notifications;

CREATE POLICY notifications_workspace_policy ON notifications USING (workspace_id = NULLIF(current_setting('app.workspace_id', true),'')::integer) WITH CHECK (workspace_id = NULLIF(current_setting('app.workspace_id', true),'')::integer);

UPDATE alembic_version SET version_num='0003_rls_policies' WHERE alembic_version.version_num = '0002_enterprise_rc';

COMMIT;

