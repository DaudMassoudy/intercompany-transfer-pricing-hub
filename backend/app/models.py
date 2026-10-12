from __future__ import annotations

from decimal import Decimal
import enum

from sqlalchemy import (
    Boolean, CheckConstraint, Column, DateTime, ForeignKey, Integer, JSON,
    Numeric, String, Text, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from .base import Base
from .timeutil import utcnow_naive

MONEY = Numeric(20, 6)
RATIO = Numeric(14, 10)

class PolicyStatus(str, enum.Enum):
    DRAFT='DRAFT'; REVIEW='REVIEW'; APPROVED='APPROVED'; ACTIVE='ACTIVE'; SUPERSEDED='SUPERSEDED'; ARCHIVED='ARCHIVED'
class ImportStatus(str, enum.Enum):
    RECEIVED='RECEIVED'; VALIDATING='VALIDATING'; VALIDATED='VALIDATED'; PARTIAL='PARTIAL'; FAILED='FAILED'; ACCEPTED='ACCEPTED'
class AdjustmentStatus(str, enum.Enum):
    PROPOSED='PROPOSED'; SUBMITTED='SUBMITTED'; IN_REVIEW='IN_REVIEW'; APPROVED='APPROVED'; REJECTED='REJECTED'; RETURNED='RETURNED'; WITHDRAWN='WITHDRAWN'; LOCKED='LOCKED'; REVERSED='REVERSED'
class PostingStatus(str, enum.Enum):
    PREPARED='PREPARED'; SUBMITTED='SUBMITTED'; ACCEPTED='ACCEPTED'; POSTED='POSTED'; RECONCILED='RECONCILED'; REJECTED='REJECTED'; FAILED='FAILED'; RETRYING='RETRYING'; PARTIALLY_POSTED='PARTIALLY_POSTED'; REVERSAL_REQUESTED='REVERSAL_REQUESTED'; REVERSED='REVERSED'

class TimestampMixin:
    created_at = Column(DateTime, default=utcnow_naive, nullable=False)
    updated_at = Column(DateTime, default=utcnow_naive, onupdate=utcnow_naive, nullable=False)

class Organization(Base, TimestampMixin):
    __tablename__='organizations'
    id=Column(Integer, primary_key=True)
    code=Column(String(40), unique=True, nullable=False, index=True)
    name=Column(String(200), nullable=False)
    active=Column(Boolean, default=True, nullable=False)

class Workspace(Base, TimestampMixin):
    __tablename__='workspaces'
    id=Column(Integer, primary_key=True)
    organization_id=Column(Integer, ForeignKey('organizations.id'), nullable=False, index=True)
    code=Column(String(40), nullable=False)
    name=Column(String(200), nullable=False)
    active=Column(Boolean, default=True, nullable=False)
    __table_args__=(UniqueConstraint('organization_id','code',name='uq_workspace_org_code'),)

class Client(Base, TimestampMixin):
    __tablename__='clients'
    id=Column(Integer, primary_key=True)
    workspace_id=Column(Integer, ForeignKey('workspaces.id'), nullable=False, index=True)
    code=Column(String(40), nullable=False)
    name=Column(String(200), nullable=False)
    active=Column(Boolean, default=True, nullable=False)
    __table_args__=(UniqueConstraint('workspace_id','code',name='uq_client_workspace_code'),)

class User(Base, TimestampMixin):
    __tablename__='users'
    id=Column(Integer, primary_key=True)
    workspace_id=Column(Integer, ForeignKey('workspaces.id'), nullable=True, index=True)
    email=Column(String(320), unique=True, index=True, nullable=False)
    password_hash=Column(String(500), nullable=False)
    role=Column(String(64), default='TP_ANALYST', nullable=False)
    active=Column(Boolean, default=True, nullable=False)
    failed_login_count=Column(Integer, default=0, nullable=False)
    locked_until=Column(DateTime, nullable=True)
    last_login_at=Column(DateTime, nullable=True)
    token_version=Column(Integer, default=1, nullable=False)

class UserEntityAccess(Base):
    __tablename__='user_entity_access'
    id=Column(Integer, primary_key=True)
    user_id=Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    entity_id=Column(Integer, ForeignKey('entities.id'), nullable=False, index=True)
    can_read=Column(Boolean, default=True, nullable=False)
    can_write=Column(Boolean, default=False, nullable=False)
    can_approve=Column(Boolean, default=False, nullable=False)
    __table_args__=(UniqueConstraint('user_id','entity_id',name='uq_user_entity_access'),)

class Entity(Base, TimestampMixin):
    __tablename__='entities'
    id=Column(Integer, primary_key=True)
    workspace_id=Column(Integer, ForeignKey('workspaces.id'), nullable=True, index=True)
    client_id=Column(Integer, ForeignKey('clients.id'), nullable=True, index=True)
    entity_code=Column(String(40), nullable=False, index=True)
    legal_name=Column(String(240), nullable=False)
    country=Column(String(2), nullable=False)
    tax_jurisdiction=Column(String(80), nullable=True)
    currency=Column(String(3), nullable=False)
    group_currency=Column(String(3), default='EUR', nullable=False)
    characterization=Column(String(160), nullable=False)
    company_code=Column(String(40), nullable=False)
    erp_system=Column(String(60), default='DEMO_ERP', nullable=False)
    tax_rate=Column(RATIO, nullable=True)
    customs_territory=Column(String(80), nullable=True)
    active=Column(Boolean, default=True, nullable=False)
    effective_from=Column(String(10), nullable=True)
    effective_to=Column(String(10), nullable=True)
    __table_args__=(UniqueConstraint('workspace_id','entity_code',name='uq_entity_workspace_code'),)

class EntityVersion(Base):
    __tablename__='entity_versions'
    id=Column(Integer, primary_key=True)
    workspace_id=Column(Integer, ForeignKey('workspaces.id'), nullable=False, index=True)
    entity_id=Column(Integer, ForeignKey('entities.id'), nullable=False, index=True)
    version_no=Column(Integer, nullable=False)
    snapshot=Column(JSON, nullable=False)
    effective_from=Column(String(10), nullable=True)
    effective_to=Column(String(10), nullable=True)
    approved_by=Column(String(320), nullable=False)
    approval_request_code=Column(String(120), nullable=True)
    created_at=Column(DateTime, default=utcnow_naive, nullable=False)
    __table_args__=(UniqueConstraint('entity_id','version_no',name='uq_entity_version_no'),)

class EntityChangeRequest(Base, TimestampMixin):
    __tablename__='entity_change_requests'
    id=Column(Integer, primary_key=True)
    workspace_id=Column(Integer, ForeignKey('workspaces.id'), nullable=False, index=True)
    entity_id=Column(Integer, ForeignKey('entities.id'), nullable=True, index=True)
    request_code=Column(String(120), unique=True, nullable=False, index=True)
    entity_code=Column(String(40), nullable=False, index=True)
    change_type=Column(String(30), nullable=False)  # CREATE / UPDATE / DEACTIVATE / REACTIVATE
    status=Column(String(30), default='DRAFT', nullable=False, index=True)
    payload=Column(JSON, nullable=False)
    reason=Column(Text, nullable=True)
    batch_code=Column(String(120), nullable=True, index=True)
    created_by=Column(String(320), nullable=False)
    submitted_by=Column(String(320), nullable=True)
    reviewed_by=Column(String(320), nullable=True)
    submitted_at=Column(DateTime, nullable=True)
    reviewed_at=Column(DateTime, nullable=True)

class IntercompanyPartner(Base, TimestampMixin):
    __tablename__='intercompany_partners'
    id=Column(Integer, primary_key=True)
    workspace_id=Column(Integer, ForeignKey('workspaces.id'), nullable=False, index=True)
    partner_code=Column(String(60), nullable=False)
    entity_id=Column(Integer, ForeignKey('entities.id'), nullable=True)
    trading_partner_code=Column(String(60), nullable=True)
    vendor_code=Column(String(60), nullable=True)
    customer_code=Column(String(60), nullable=True)
    country=Column(String(2), nullable=True)
    relationship_type=Column(String(80), default='RELATED_PARTY')
    effective_from=Column(String(10), nullable=True)
    effective_to=Column(String(10), nullable=True)
    active=Column(Boolean, default=True, nullable=False)
    __table_args__=(UniqueConstraint('workspace_id','partner_code',name='uq_partner_workspace_code'),)

class GLAccount(Base, TimestampMixin):
    __tablename__='gl_accounts'
    id=Column(Integer, primary_key=True)
    workspace_id=Column(Integer, ForeignKey('workspaces.id'), nullable=False, index=True)
    account_code=Column(String(40), nullable=False)
    description=Column(String(200), nullable=False)
    classification=Column(String(60), nullable=False)
    operating=Column(Boolean, default=True, nullable=False)
    pli_included=Column(Boolean, default=True, nullable=False)
    cost_plus_eligible=Column(Boolean, default=False, nullable=False)
    allocation_eligible=Column(Boolean, default=False, nullable=False)
    exceptional_item=Column(Boolean, default=False, nullable=False)
    pass_through=Column(Boolean, default=False, nullable=False)
    effective_from=Column(String(10), nullable=True)
    effective_to=Column(String(10), nullable=True)
    active=Column(Boolean, default=True, nullable=False)
    __table_args__=(UniqueConstraint('workspace_id','account_code',name='uq_gl_workspace_code'),)

class ProfitCenter(Base, TimestampMixin):
    __tablename__='profit_centers'
    id=Column(Integer, primary_key=True)
    workspace_id=Column(Integer, ForeignKey('workspaces.id'), nullable=False, index=True)
    code=Column(String(60), nullable=False)
    entity_id=Column(Integer, ForeignKey('entities.id'), nullable=False, index=True)
    function=Column(String(120), nullable=True)
    business_unit=Column(String(120), nullable=True)
    geography=Column(String(120), nullable=True)
    active=Column(Boolean, default=True, nullable=False)
    __table_args__=(UniqueConstraint('workspace_id','code',name='uq_pc_workspace_code'),)

class Product(Base, TimestampMixin):
    __tablename__='products'
    id=Column(Integer, primary_key=True)
    workspace_id=Column(Integer, ForeignKey('workspaces.id'), nullable=False, index=True)
    sku=Column(String(80), nullable=False)
    product_group=Column(String(120), nullable=True)
    entity_id=Column(Integer, ForeignKey('entities.id'), nullable=True)
    standard_cost=Column(MONEY, nullable=True)
    currency=Column(String(3), nullable=True)
    active=Column(Boolean, default=True, nullable=False)
    __table_args__=(UniqueConstraint('workspace_id','sku',name='uq_product_workspace_sku'),)

class MasterDataRecord(Base, TimestampMixin):
    """Governed master-data record for domains that do not require a dedicated
    operational table, and governance projection for operational master tables.

    The record is intentionally domain-neutral so that new master-data domains can
    be introduced without database edits. Domain-specific validation lives in the
    master-data service. Operational projections (for example GLAccount) are kept
    in sync only after maker-checker approval.
    """
    __tablename__='master_data_records'
    id=Column(Integer, primary_key=True)
    workspace_id=Column(Integer, ForeignKey('workspaces.id'), nullable=False, index=True)
    domain=Column(String(60), nullable=False, index=True)
    record_code=Column(String(120), nullable=False, index=True)
    name=Column(String(240), nullable=False)
    attributes=Column(JSON, nullable=False, default=dict)
    active=Column(Boolean, default=True, nullable=False)
    effective_from=Column(String(10), nullable=True)
    effective_to=Column(String(10), nullable=True)
    version_no=Column(Integer, default=1, nullable=False)
    approved_by=Column(String(320), nullable=True)
    approval_request_code=Column(String(120), nullable=True)
    __table_args__=(UniqueConstraint('workspace_id','domain','record_code',name='uq_master_record_workspace_domain_code'),)

class MasterDataVersion(Base):
    __tablename__='master_data_versions'
    id=Column(Integer, primary_key=True)
    workspace_id=Column(Integer, ForeignKey('workspaces.id'), nullable=False, index=True)
    domain=Column(String(60), nullable=False, index=True)
    record_code=Column(String(120), nullable=False, index=True)
    version_no=Column(Integer, nullable=False)
    snapshot=Column(JSON, nullable=False)
    approved_by=Column(String(320), nullable=False)
    approval_request_code=Column(String(120), nullable=True)
    created_at=Column(DateTime, default=utcnow_naive, nullable=False)
    __table_args__=(UniqueConstraint('workspace_id','domain','record_code','version_no',name='uq_master_version_domain_code_no'),)

class MasterDataChangeRequest(Base, TimestampMixin):
    __tablename__='master_data_change_requests'
    id=Column(Integer, primary_key=True)
    workspace_id=Column(Integer, ForeignKey('workspaces.id'), nullable=False, index=True)
    domain=Column(String(60), nullable=False, index=True)
    record_code=Column(String(120), nullable=False, index=True)
    request_code=Column(String(120), unique=True, nullable=False, index=True)
    change_type=Column(String(30), nullable=False)
    status=Column(String(30), default='DRAFT', nullable=False, index=True)
    payload=Column(JSON, nullable=False)
    reason=Column(Text, nullable=True)
    batch_code=Column(String(120), nullable=True, index=True)
    created_by=Column(String(320), nullable=False)
    submitted_by=Column(String(320), nullable=True)
    reviewed_by=Column(String(320), nullable=True)
    submitted_at=Column(DateTime, nullable=True)
    reviewed_at=Column(DateTime, nullable=True)

class Policy(Base, TimestampMixin):
    __tablename__='tp_policies'
    id=Column(Integer, primary_key=True)
    workspace_id=Column(Integer, ForeignKey('workspaces.id'), nullable=True, index=True)
    policy_code=Column(String(80), nullable=False)
    entity_id=Column(Integer, ForeignKey('entities.id'), nullable=False, index=True)
    counterparty_code=Column(String(60), nullable=True)
    transaction_type=Column(String(120), default='DISTRIBUTION', nullable=False)
    method=Column(String(40), nullable=False)
    pli=Column(String(60), nullable=False)
    target=Column(RATIO, nullable=False)
    lower_bound=Column(RATIO, nullable=True)
    median=Column(RATIO, nullable=True)
    upper_bound=Column(RATIO, nullable=True)
    markup=Column(RATIO, nullable=True)
    benchmark_id=Column(String(100), nullable=True)
    version=Column(String(40), default='1.0', nullable=False)
    status=Column(String(30), default=PolicyStatus.ACTIVE.value, nullable=False)
    effective_from=Column(String(10), nullable=True)
    effective_to=Column(String(10), nullable=True)
    true_up_frequency=Column(String(40), default='QUARTERLY')
    materiality_threshold=Column(MONEY, default=Decimal('0'))
    approval_matrix=Column(JSON, nullable=True)
    document_references=Column(JSON, nullable=True)
    tested_party_code=Column(String(80), nullable=True)
    tolerance=Column(RATIO, nullable=True)
    cost_base=Column(String(80), nullable=True)
    allocation_treatment=Column(String(80), nullable=True)
    currency=Column(String(3), nullable=True)
    journal_template_code=Column(String(120), nullable=True)
    workflow_code=Column(String(120), nullable=True)
    created_by=Column(String(320), nullable=True)
    submitted_by=Column(String(320), nullable=True)
    approved_by=Column(String(320), nullable=True)
    activated_by=Column(String(320), nullable=True)
    submitted_at=Column(DateTime, nullable=True)
    approved_at=Column(DateTime, nullable=True)
    activated_at=Column(DateTime, nullable=True)
    notes=Column(Text, nullable=True)
    entity=relationship('Entity')
    __table_args__=(UniqueConstraint('workspace_id','policy_code','version',name='uq_policy_workspace_code_version'),)

class BenchmarkComparable(Base, TimestampMixin):
    __tablename__='benchmark_comparables'
    id=Column(Integer, primary_key=True)
    workspace_id=Column(Integer, ForeignKey('workspaces.id'), nullable=False, index=True)
    benchmark_code=Column(String(120), nullable=False, index=True)
    company_name=Column(String(240), nullable=False)
    country=Column(String(2), nullable=True)
    industry=Column(String(160), nullable=True)
    status=Column(String(30), default='POTENTIAL', nullable=False, index=True)
    screening_reason=Column(Text, nullable=True)
    notes=Column(Text, nullable=True)
    evidence=Column(JSON, nullable=True)
    created_by=Column(String(320), nullable=False)

class BenchmarkFinancialObservation(Base):
    __tablename__='benchmark_financial_observations'
    id=Column(Integer, primary_key=True)
    comparable_id=Column(Integer, ForeignKey('benchmark_comparables.id'), nullable=False, index=True)
    fiscal_year=Column(Integer, nullable=False)
    sales=Column(MONEY, nullable=True)
    ebit=Column(MONEY, nullable=True)
    cost_base=Column(MONEY, nullable=True)
    assets=Column(MONEY, nullable=True)
    pli=Column(RATIO, nullable=False)
    source_reference=Column(String(255), nullable=True)
    __table_args__=(UniqueConstraint('comparable_id','fiscal_year',name='uq_benchmark_comparable_year'),)

class SourceImport(Base, TimestampMixin):
    __tablename__='source_imports'
    id=Column(Integer, primary_key=True)
    import_code=Column(String(100), unique=True, nullable=False, index=True)
    workspace_id=Column(Integer, ForeignKey('workspaces.id'), nullable=False, index=True)
    entity_id=Column(Integer, ForeignKey('entities.id'), nullable=True, index=True)
    source_system=Column(String(80), nullable=False)
    period=Column(String(20), nullable=False)
    filename=Column(String(255), nullable=False)
    sha256=Column(String(64), nullable=False)
    row_count=Column(Integer, default=0, nullable=False)
    accepted_rows=Column(Integer, default=0, nullable=False)
    rejected_rows=Column(Integer, default=0, nullable=False)
    warning_rows=Column(Integer, default=0, nullable=False)
    source_control_total=Column(MONEY, default=Decimal('0'), nullable=False)
    imported_control_total=Column(MONEY, default=Decimal('0'), nullable=False)
    status=Column(String(30), default=ImportStatus.RECEIVED.value, nullable=False)
    schema_version=Column(String(30), default='1.0', nullable=False)
    original_path=Column(String(500), nullable=True)
    actor=Column(String(320), nullable=True)

class RawFinancialRecord(Base, TimestampMixin):
    __tablename__='raw_financial_records'
    id=Column(Integer, primary_key=True)
    workspace_id=Column(Integer, ForeignKey('workspaces.id'), nullable=False, index=True)
    source_import_id=Column(Integer, ForeignKey('source_imports.id'), nullable=False, index=True)
    row_number=Column(Integer, nullable=False)
    period=Column(String(20), nullable=False, index=True)
    entity_code=Column(String(40), nullable=False, index=True)
    company_code=Column(String(40), nullable=True)
    document_number=Column(String(100), nullable=True)
    gl_account=Column(String(40), nullable=False, index=True)
    cost_center=Column(String(60), nullable=True)
    profit_center=Column(String(60), nullable=True)
    counterparty_code=Column(String(60), nullable=True)
    product_sku=Column(String(80), nullable=True)
    product_group=Column(String(120), nullable=True)
    currency=Column(String(3), nullable=False)
    amount=Column(MONEY, nullable=False)
    debit_credit=Column(String(10), nullable=True)
    validation_status=Column(String(30), default='VALID', nullable=False)
    validation_messages=Column(JSON, nullable=True)
    raw_payload=Column(JSON, nullable=True)
    __table_args__=(UniqueConstraint('source_import_id','row_number',name='uq_import_row_number'),)

class MappingRule(Base, TimestampMixin):
    __tablename__='mapping_rules'
    id=Column(Integer, primary_key=True)
    workspace_id=Column(Integer, ForeignKey('workspaces.id'), nullable=False, index=True)
    rule_code=Column(String(80), nullable=False)
    version=Column(Integer, default=1, nullable=False)
    priority=Column(Integer, default=100, nullable=False)
    match_fields=Column(JSON, nullable=False)
    segment_code=Column(String(80), nullable=False)
    controlled_transaction_code=Column(String(80), nullable=False)
    policy_code=Column(String(80), nullable=False)
    effective_from=Column(String(10), nullable=True)
    effective_to=Column(String(10), nullable=True)
    status=Column(String(30), default='ACTIVE', nullable=False)
    approved_by=Column(String(320), nullable=True)
    __table_args__=(UniqueConstraint('workspace_id','rule_code','version',name='uq_mapping_rule_version'), Index('ix_mapping_priority','workspace_id','priority'))

class NormalizedFinancialRecord(Base, TimestampMixin):
    __tablename__='normalized_financial_records'
    id=Column(Integer, primary_key=True)
    workspace_id=Column(Integer, ForeignKey('workspaces.id'), nullable=False, index=True)
    raw_record_id=Column(Integer, ForeignKey('raw_financial_records.id'), nullable=False, unique=True)
    entity_id=Column(Integer, ForeignKey('entities.id'), nullable=False, index=True)
    period=Column(String(20), nullable=False, index=True)
    gl_account=Column(String(40), nullable=False)
    counterparty_code=Column(String(60), nullable=True)
    profit_center=Column(String(60), nullable=True)
    product_sku=Column(String(80), nullable=True)
    product_group=Column(String(120), nullable=True)
    currency=Column(String(3), nullable=False)
    amount=Column(MONEY, nullable=False)
    financial_classification=Column(String(60), nullable=False)
    segment_code=Column(String(80), nullable=False, index=True)
    controlled_transaction_code=Column(String(80), nullable=False)
    policy_code=Column(String(80), nullable=False)
    mapping_rule_id=Column(Integer, ForeignKey('mapping_rules.id'), nullable=False)

class AllocationRule(Base, TimestampMixin):
    __tablename__='allocation_rules'
    id=Column(Integer, primary_key=True)
    workspace_id=Column(Integer, ForeignKey('workspaces.id'), nullable=False, index=True)
    rule_code=Column(String(80), nullable=False)
    version=Column(Integer, default=1, nullable=False)
    sender_segment=Column(String(80), nullable=False)
    cost_pool_name=Column(String(120), nullable=False)
    driver_type=Column(String(60), nullable=False)
    recipients=Column(JSON, nullable=False)
    exclusions=Column(JSON, nullable=True)
    markup_eligible=Column(Boolean, default=False, nullable=False)
    cost_pool_type=Column(String(60), default='CUSTOM', nullable=False)
    sender_entity_code=Column(String(40), nullable=True)
    period_scope=Column(String(40), default='MONTHLY', nullable=False)
    currency=Column(String(3), default='EUR', nullable=False)
    source_accounts=Column(JSON, nullable=True)
    source_cost_centers=Column(JSON, nullable=True)
    source_profit_centers=Column(JSON, nullable=True)
    source_transactions=Column(JSON, nullable=True)
    source_amount_source=Column(String(40), default='MANUAL_CONTROLLED', nullable=False)
    manual_amount_allowed=Column(Boolean, default=True, nullable=False)
    driver_source=Column(String(40), default='MANUAL_CONTROLLED', nullable=False)
    driver_weights=Column(JSON, nullable=True)
    stages=Column(JSON, nullable=True)
    recipient_rules=Column(JSON, nullable=True)
    markup_treatment=Column(String(40), default='NO_MARKUP', nullable=False)
    markup_rate=Column(RATIO, nullable=True)
    fx_methodology=Column(String(80), nullable=True)
    fx_version=Column(String(80), nullable=True)
    effective_from=Column(String(10), nullable=True)
    effective_to=Column(String(10), nullable=True)
    created_by=Column(String(320), nullable=True)
    approved_at=Column(DateTime, nullable=True)
    status=Column(String(30), default='ACTIVE', nullable=False)
    approved_by=Column(String(320), nullable=True)
    __table_args__=(UniqueConstraint('workspace_id','rule_code','version',name='uq_allocation_rule_version'),)

class AllocationRun(Base, TimestampMixin):
    __tablename__='allocation_runs'
    id=Column(Integer, primary_key=True)
    workspace_id=Column(Integer, ForeignKey('workspaces.id'), nullable=False, index=True)
    run_code=Column(String(100), unique=True, nullable=False)
    rule_id=Column(Integer, ForeignKey('allocation_rules.id'), nullable=False)
    period=Column(String(20), nullable=False)
    source_amount=Column(MONEY, nullable=False)
    allocated_amount=Column(MONEY, nullable=False)
    residual=Column(MONEY, nullable=False)
    status=Column(String(30), default='COMPLETED', nullable=False)

class AllocationResult(Base):
    __tablename__='allocation_results'
    id=Column(Integer, primary_key=True)
    allocation_run_id=Column(Integer, ForeignKey('allocation_runs.id'), nullable=False, index=True)
    recipient_segment=Column(String(80), nullable=False)
    driver_value=Column(MONEY, nullable=False)
    driver_share=Column(RATIO, nullable=False)
    allocated_amount=Column(MONEY, nullable=False)

class FinancialPeriod(Base, TimestampMixin):
    __tablename__='financial_periods'
    id=Column(Integer, primary_key=True)
    workspace_id=Column(Integer, ForeignKey('workspaces.id'), nullable=True, index=True)
    entity_id=Column(Integer, ForeignKey('entities.id'), nullable=False, index=True)
    period=Column(String(20), nullable=False)
    revenue=Column(MONEY, nullable=False)
    cogs=Column(MONEY, nullable=False)
    opex=Column(MONEY, nullable=False)
    forecast_ros=Column(RATIO, nullable=True)  # retained for legacy compatibility; new forecasts use ForecastVersion/Line
    source_import_id=Column(String(100), default='DEMO-IMPORT-001')
    entity=relationship('Entity')
    __table_args__=(UniqueConstraint('entity_id','period', name='uq_entity_period'),)

class ForecastVersion(Base, TimestampMixin):
    __tablename__='forecast_versions'
    id=Column(Integer, primary_key=True)
    workspace_id=Column(Integer, ForeignKey('workspaces.id'), nullable=False, index=True)
    version_code=Column(String(80), nullable=False)
    scenario=Column(String(40), nullable=False)
    fiscal_year=Column(Integer, nullable=False)
    status=Column(String(30), default='APPROVED', nullable=False)
    approved_by=Column(String(320), nullable=True)
    __table_args__=(UniqueConstraint('workspace_id','version_code',name='uq_forecast_workspace_version'),)

class ForecastLine(Base):
    __tablename__='forecast_lines'
    id=Column(Integer, primary_key=True)
    forecast_version_id=Column(Integer, ForeignKey('forecast_versions.id'), nullable=False, index=True)
    entity_id=Column(Integer, ForeignKey('entities.id'), nullable=False, index=True)
    month=Column(Integer, nullable=False)
    revenue=Column(MONEY, nullable=False)
    cogs=Column(MONEY, nullable=False)
    opex=Column(MONEY, nullable=False)
    currency=Column(String(3), nullable=False)
    __table_args__=(UniqueConstraint('forecast_version_id','entity_id','month',name='uq_forecast_line'), CheckConstraint('month >= 1 AND month <= 12', name='ck_forecast_month'))

class Calculation(Base, TimestampMixin):
    __tablename__='calculations'
    id=Column(Integer, primary_key=True)
    workspace_id=Column(Integer, ForeignKey('workspaces.id'), nullable=True, index=True)
    calculation_code=Column(String(120), unique=True, nullable=False)
    entity_id=Column(Integer, ForeignKey('entities.id'), nullable=False, index=True)
    policy_id=Column(Integer, ForeignKey('tp_policies.id'), nullable=False)
    period=Column(String(20), nullable=False)
    revenue=Column(MONEY, nullable=False)
    ebit=Column(MONEY, nullable=False)
    actual_pli=Column(RATIO, nullable=False)
    target_pli=Column(RATIO, nullable=False)
    suggested_adjustment=Column(MONEY, nullable=False)
    engine_version=Column(String(80), default='otp-engine-2.4.0-rc.3')
    source_hash=Column(String(64), nullable=False)
    manifest=Column(JSON, nullable=True)
    finalized=Column(Boolean, default=False, nullable=False)

class Simulation(Base, TimestampMixin):
    __tablename__='simulations'
    id=Column(Integer, primary_key=True)
    workspace_id=Column(Integer, ForeignKey('workspaces.id'), nullable=False, index=True)
    simulation_code=Column(String(100), unique=True, nullable=False)
    entity_id=Column(Integer, ForeignKey('entities.id'), nullable=False)
    period=Column(String(20), nullable=False)
    inputs=Column(JSON, nullable=False)
    outputs=Column(JSON, nullable=False)
    created_by=Column(String(320), nullable=False)

class Adjustment(Base, TimestampMixin):
    __tablename__='adjustments'
    id=Column(Integer, primary_key=True)
    workspace_id=Column(Integer, ForeignKey('workspaces.id'), nullable=True, index=True)
    adjustment_code=Column(String(120), unique=True, nullable=False)
    calculation_id=Column(Integer, ForeignKey('calculations.id'), nullable=False)
    entity_id=Column(Integer, ForeignKey('entities.id'), nullable=False, index=True)
    amount=Column(MONEY, nullable=False)
    currency=Column(String(3), default='EUR', nullable=False)
    status=Column(String(30), default=AdjustmentStatus.PROPOSED.value, nullable=False)
    version=Column(Integer, default=1, nullable=False)
    submitted_by=Column(String(320), nullable=True)
    approved_by=Column(String(320), nullable=True)  # legacy convenience field
    locked_at=Column(DateTime, nullable=True)
    materiality=Column(MONEY, default=Decimal('0'), nullable=False)
    adjustment_type=Column(String(30), default='TRUE_UP', nullable=False)
    original_adjustment_id=Column(Integer, ForeignKey('adjustments.id'), nullable=True, index=True)
    batch_code=Column(String(120), nullable=True, index=True)
    target_type=Column(String(40), nullable=True)
    target_value=Column(RATIO, nullable=True)
    frequency=Column(String(30), nullable=True)
    rounding_mode=Column(String(40), default='ROUND_HALF_UP', nullable=False)
    reason=Column(Text, nullable=True)

class ApprovalRequest(Base, TimestampMixin):
    __tablename__='approval_requests'
    id=Column(Integer, primary_key=True)
    workspace_id=Column(Integer, ForeignKey('workspaces.id'), nullable=False, index=True)
    adjustment_id=Column(Integer, ForeignKey('adjustments.id'), nullable=False, unique=True)
    current_step=Column(Integer, default=1, nullable=False)
    status=Column(String(30), default='PENDING', nullable=False)
    created_by=Column(String(320), nullable=False)
    workflow_code=Column(String(120), nullable=True)
    workflow_version=Column(Integer, nullable=True)

class ApprovalStep(Base, TimestampMixin):
    __tablename__='approval_steps'
    id=Column(Integer, primary_key=True)
    approval_request_id=Column(Integer, ForeignKey('approval_requests.id'), nullable=False, index=True)
    step_order=Column(Integer, nullable=False)
    required_role=Column(String(64), nullable=False)
    status=Column(String(30), default='PENDING', nullable=False)
    actor=Column(String(320), nullable=True)
    comments=Column(Text, nullable=True)
    decided_at=Column(DateTime, nullable=True)
    __table_args__=(UniqueConstraint('approval_request_id','step_order',name='uq_approval_step_order'),)

class JournalHeader(Base, TimestampMixin):
    __tablename__='journal_headers'
    id=Column(Integer, primary_key=True)
    workspace_id=Column(Integer, ForeignKey('workspaces.id'), nullable=False, index=True)
    journal_code=Column(String(120), unique=True, nullable=False)
    adjustment_id=Column(Integer, ForeignKey('adjustments.id'), nullable=False, unique=True)
    company_code=Column(String(40), nullable=False)
    ledger=Column(String(20), default='0L', nullable=False)
    document_type=Column(String(20), default='TP', nullable=False)
    posting_date=Column(String(10), nullable=False)
    document_date=Column(String(10), nullable=False)
    currency=Column(String(3), nullable=False)
    reference=Column(String(120), nullable=False)
    status=Column(String(30), default='PREPARED', nullable=False)
    template_code=Column(String(120), nullable=True)
    template_version=Column(Integer, nullable=True)

class JournalLine(Base):
    __tablename__='journal_lines'
    id=Column(Integer, primary_key=True)
    journal_id=Column(Integer, ForeignKey('journal_headers.id'), nullable=False, index=True)
    line_no=Column(Integer, nullable=False)
    gl_account=Column(String(40), nullable=False)
    debit_credit=Column(String(10), nullable=False)
    amount=Column(MONEY, nullable=False)
    currency=Column(String(3), nullable=False)
    profit_center=Column(String(60), nullable=True)
    cost_center=Column(String(60), nullable=True)
    trading_partner=Column(String(60), nullable=True)
    assignment=Column(String(120), nullable=True)
    text=Column(String(255), nullable=True)
    tax_code=Column(String(20), nullable=True)
    __table_args__=(UniqueConstraint('journal_id','line_no',name='uq_journal_line_no'), CheckConstraint("debit_credit in ('DEBIT','CREDIT')",name='ck_journal_dc'))

# Legacy journal table retained for migration/backward compatibility only.
class Journal(Base):
    __tablename__='journal_entries'
    id=Column(Integer, primary_key=True)
    journal_code=Column(String, unique=True, nullable=False)
    adjustment_id=Column(Integer, ForeignKey('adjustments.id'), nullable=False)
    entity_code=Column(String, nullable=False)
    counterparty_code=Column(String, nullable=False)
    debit=Column(MONEY, nullable=False)
    credit=Column(MONEY, nullable=False)
    currency=Column(String, nullable=False)
    status=Column(String, default='PREPARED')

class Posting(Base, TimestampMixin):
    __tablename__='erp_postings'
    id=Column(Integer, primary_key=True)
    workspace_id=Column(Integer, ForeignKey('workspaces.id'), nullable=True, index=True)
    journal_id=Column(Integer, ForeignKey('journal_entries.id'), nullable=True, index=True)  # legacy v0.x
    journal_header_id=Column(Integer, ForeignKey('journal_headers.id'), nullable=True, index=True)
    idempotency_key=Column(String(120), unique=True, nullable=True)
    erp_system=Column(String(60), default='SAP_SIMULATOR', nullable=False)
    erp_document_number=Column(String(120), unique=True, nullable=False)
    posted_amount=Column(MONEY, nullable=False)
    status=Column(String(30), default=PostingStatus.POSTED.value, nullable=False)
    posted_at=Column(DateTime, default=utcnow_naive)

class PostingAttempt(Base, TimestampMixin):
    __tablename__='posting_attempts'
    id=Column(Integer, primary_key=True)
    posting_id=Column(Integer, ForeignKey('erp_postings.id'), nullable=False, index=True)
    attempt_no=Column(Integer, nullable=False)
    request_payload=Column(JSON, nullable=True)
    response_payload=Column(JSON, nullable=True)
    status=Column(String(30), nullable=False)
    error_message=Column(Text, nullable=True)
    __table_args__=(UniqueConstraint('posting_id','attempt_no',name='uq_posting_attempt'),)

class Reconciliation(Base, TimestampMixin):
    __tablename__='reconciliations'
    id=Column(Integer, primary_key=True)
    workspace_id=Column(Integer, ForeignKey('workspaces.id'), nullable=True, index=True)
    adjustment_id=Column(Integer, ForeignKey('adjustments.id'), nullable=False, index=True)
    expected_amount=Column(MONEY, nullable=False)
    approved_amount=Column(MONEY, nullable=True)
    journal_amount=Column(MONEY, nullable=True)
    posted_amount=Column(MONEY, nullable=False)
    final_pnl_impact=Column(MONEY, nullable=True)
    difference=Column(MONEY, nullable=False)
    status=Column(String(30), nullable=False)
    tolerance=Column(MONEY, default=Decimal('0.01'), nullable=False)
    currency=Column(String(3), nullable=True)
    exception_code=Column(String(120), nullable=True)
    certified_by=Column(String(320), nullable=True)
    certified_at=Column(DateTime, nullable=True)
    certification_comment=Column(Text, nullable=True)

class ExceptionCase(Base, TimestampMixin):
    __tablename__='exceptions'
    id=Column(Integer, primary_key=True)
    workspace_id=Column(Integer, ForeignKey('workspaces.id'), nullable=False, index=True)
    exception_code=Column(String(120), unique=True, nullable=False)
    entity_id=Column(Integer, ForeignKey('entities.id'), nullable=True, index=True)
    category=Column(String(80), nullable=False)
    severity=Column(String(20), nullable=False)
    amount=Column(MONEY, nullable=True)
    owner=Column(String(320), nullable=True)
    due_date=Column(String(10), nullable=True)
    status=Column(String(30), default='OPEN', nullable=False)
    evidence=Column(JSON, nullable=True)
    resolution=Column(Text, nullable=True)
    source=Column(String(80), nullable=True)
    currency=Column(String(3), nullable=True)
    root_cause=Column(Text, nullable=True)
    remediation=Column(Text, nullable=True)
    comments=Column(JSON, nullable=True)
    attachments=Column(JSON, nullable=True)
    sla_hours=Column(Integer, nullable=True)
    escalated_to=Column(String(320), nullable=True)
    waived_by=Column(String(320), nullable=True)
    waiver_reason=Column(Text, nullable=True)
    closed_by=Column(String(320), nullable=True)
    closed_at=Column(DateTime, nullable=True)

class Document(Base, TimestampMixin):
    __tablename__='documents'
    id=Column(Integer, primary_key=True)
    workspace_id=Column(Integer, ForeignKey('workspaces.id'), nullable=False, index=True)
    document_code=Column(String(120), nullable=False)
    version=Column(Integer, default=1, nullable=False)
    entity_id=Column(Integer, ForeignKey('entities.id'), nullable=True)
    country=Column(String(2), nullable=True)
    period=Column(String(20), nullable=True)
    document_type=Column(String(80), nullable=False)
    effective_date=Column(String(10), nullable=True)
    status=Column(String(30), default='ACTIVE', nullable=False)
    sha256=Column(String(64), nullable=False)
    uploader=Column(String(320), nullable=False)
    access_classification=Column(String(40), default='CONFIDENTIAL', nullable=False)
    storage_key=Column(String(500), nullable=False)
    expires_at=Column(String(10), nullable=True)
    tags=Column(JSON, nullable=True)
    linked_object_type=Column(String(80), nullable=True, index=True)
    linked_object_id=Column(String(120), nullable=True, index=True)
    metadata_json=Column(JSON, nullable=True)
    __table_args__=(UniqueConstraint('workspace_id','document_code','version',name='uq_document_version'),)

class EvidenceChunk(Base):
    __tablename__='evidence_chunks'
    id=Column(Integer, primary_key=True)
    document_id=Column(Integer, ForeignKey('documents.id'), nullable=False, index=True)
    chunk_no=Column(Integer, nullable=False)
    content=Column(Text, nullable=False)
    metadata_json=Column(JSON, nullable=True)
    __table_args__=(UniqueConstraint('document_id','chunk_no',name='uq_evidence_chunk'),)

class AIInvocation(Base, TimestampMixin):
    __tablename__='ai_invocations'
    id=Column(Integer, primary_key=True)
    workspace_id=Column(Integer, ForeignKey('workspaces.id'), nullable=False, index=True)
    user_email=Column(String(320), nullable=False)
    provider=Column(String(80), nullable=False)
    model=Column(String(120), nullable=False)
    prompt_version=Column(String(40), nullable=False)
    retrieval_context=Column(JSON, nullable=True)
    response_text=Column(Text, nullable=False)
    citations=Column(JSON, nullable=True)
    review_status=Column(String(30), default='UNREVIEWED', nullable=False)

class PnLRun(Base, TimestampMixin):
    __tablename__='pnl_runs'
    id=Column(Integer, primary_key=True)
    workspace_id=Column(Integer, ForeignKey('workspaces.id'), nullable=False, index=True)
    run_code=Column(String(120), unique=True, nullable=False, index=True)
    as_of_period=Column(String(20), nullable=False, index=True)
    fiscal_year=Column(Integer, nullable=False)
    source_import_ids=Column(JSON, nullable=False)
    allocation_run_ids=Column(JSON, nullable=True)
    mapping_coverage=Column(RATIO, nullable=False)
    source_rows=Column(Integer, nullable=False)
    mapped_rows=Column(Integer, nullable=False)
    unresolved_rows=Column(Integer, nullable=False)
    source_control_total=Column(MONEY, nullable=False)
    normalized_control_total=Column(MONEY, nullable=False)
    allocation_residual=Column(MONEY, nullable=False, default=Decimal('0'))
    source_hash=Column(String(64), nullable=False)
    engine_version=Column(String(80), nullable=False)
    status=Column(String(30), nullable=False, default='CONTROLLED')
    published=Column(Boolean, nullable=False, default=True)
    created_by=Column(String(320), nullable=False)

class PnLSegmentResult(Base):
    __tablename__='pnl_segment_results'
    id=Column(Integer, primary_key=True)
    pnl_run_id=Column(Integer, ForeignKey('pnl_runs.id'), nullable=False, index=True)
    entity_id=Column(Integer, ForeignKey('entities.id'), nullable=False, index=True)
    segment_code=Column(String(80), nullable=False, index=True)
    controlled_transaction_code=Column(String(80), nullable=False)
    policy_code=Column(String(80), nullable=False)
    currency=Column(String(3), nullable=False)
    direct_revenue=Column(MONEY, nullable=False)
    direct_cogs=Column(MONEY, nullable=False)
    direct_opex=Column(MONEY, nullable=False)
    allocated_opex=Column(MONEY, nullable=False, default=Decimal('0'))
    revenue=Column(MONEY, nullable=False)
    cogs=Column(MONEY, nullable=False)
    opex=Column(MONEY, nullable=False)
    gross_profit=Column(MONEY, nullable=False)
    ebit=Column(MONEY, nullable=False)
    pli=Column(RATIO, nullable=False)
    method=Column(String(40), nullable=False)
    pli_name=Column(String(60), nullable=False)
    target=Column(RATIO, nullable=False)
    status=Column(String(20), nullable=False)
    suggested_adjustment=Column(MONEY, nullable=False)
    source_row_count=Column(Integer, nullable=False)
    lineage=Column(JSON, nullable=False)
    __table_args__=(UniqueConstraint('pnl_run_id','entity_id','segment_code','controlled_transaction_code',name='uq_pnl_run_segment'),)

class PnLSnapshot(Base, TimestampMixin):
    __tablename__='pnl_snapshots'
    id=Column(Integer, primary_key=True)
    workspace_id=Column(Integer, ForeignKey('workspaces.id'), nullable=False, index=True)
    snapshot_code=Column(String(120), unique=True, nullable=False, index=True)
    pnl_run_id=Column(Integer, ForeignKey('pnl_runs.id'), nullable=False, index=True)
    scenario=Column(String(40), default='ACTUAL', nullable=False)
    label=Column(String(160), nullable=True)
    status=Column(String(30), default='OPEN', nullable=False)
    dimensions=Column(JSON, nullable=True)
    comment=Column(Text, nullable=True)
    locked_by=Column(String(320), nullable=True)
    locked_at=Column(DateTime, nullable=True)

class ReconciliationStage(Base, TimestampMixin):
    __tablename__='reconciliation_stages'
    id=Column(Integer, primary_key=True)
    reconciliation_id=Column(Integer, ForeignKey('reconciliations.id'), nullable=False, index=True)
    stage_order=Column(Integer, nullable=False)
    stage_code=Column(String(60), nullable=False)
    source_amount=Column(MONEY, nullable=False)
    target_amount=Column(MONEY, nullable=False)
    difference=Column(MONEY, nullable=False)
    tolerance=Column(MONEY, nullable=False, default=Decimal('0.01'))
    status=Column(String(30), nullable=False)
    reason=Column(Text, nullable=True)
    linked_records=Column(JSON, nullable=True)
    __table_args__=(UniqueConstraint('reconciliation_id','stage_order',name='uq_reconciliation_stage_order'),)

class WorkflowInstance(Base, TimestampMixin):
    __tablename__='workflow_instances'
    id=Column(Integer, primary_key=True)
    workspace_id=Column(Integer, ForeignKey('workspaces.id'), nullable=False, index=True)
    instance_code=Column(String(120), unique=True, nullable=False, index=True)
    workflow_code=Column(String(120), nullable=False)
    workflow_version=Column(Integer, nullable=False)
    object_type=Column(String(80), nullable=False, index=True)
    object_id=Column(String(120), nullable=False, index=True)
    approval_mode=Column(String(30), nullable=False, default='SEQUENTIAL')
    status=Column(String(30), nullable=False, default='PENDING')
    created_by=Column(String(320), nullable=False)
    context=Column(JSON, nullable=True)
    completed_at=Column(DateTime, nullable=True)

class WorkflowTask(Base, TimestampMixin):
    __tablename__='workflow_tasks'
    id=Column(Integer, primary_key=True)
    workflow_instance_id=Column(Integer, ForeignKey('workflow_instances.id'), nullable=False, index=True)
    step_order=Column(Integer, nullable=False)
    group_no=Column(Integer, nullable=False, default=1)
    required_role=Column(String(64), nullable=False)
    status=Column(String(30), nullable=False, default='PENDING')
    actor=Column(String(320), nullable=True)
    delegated_from=Column(String(320), nullable=True)
    due_at=Column(DateTime, nullable=True)
    comments=Column(Text, nullable=True)
    decided_at=Column(DateTime, nullable=True)

class UserDelegation(Base, TimestampMixin):
    __tablename__='user_delegations'
    id=Column(Integer, primary_key=True)
    workspace_id=Column(Integer, ForeignKey('workspaces.id'), nullable=False, index=True)
    from_user=Column(String(320), nullable=False, index=True)
    to_user=Column(String(320), nullable=False, index=True)
    role=Column(String(64), nullable=True)
    effective_from=Column(DateTime, nullable=False)
    effective_to=Column(DateTime, nullable=False)
    active=Column(Boolean, nullable=False, default=True)

class QualificationEvidence(Base, TimestampMixin):
    __tablename__='qualification_evidence'
    id=Column(Integer, primary_key=True)
    workspace_id=Column(Integer, ForeignKey('workspaces.id'), nullable=False, index=True)
    release_version=Column(String(80), nullable=False, index=True)
    control_code=Column(String(100), nullable=False, index=True)
    category=Column(String(80), nullable=False)
    status=Column(String(30), nullable=False)
    environment=Column(String(120), nullable=True)
    result=Column(JSON, nullable=True)
    evidence_path=Column(String(500), nullable=True)
    executed_by=Column(String(320), nullable=True)
    duration_ms=Column(Integer, nullable=True)
    __table_args__=(UniqueConstraint('workspace_id','release_version','control_code',name='uq_qualification_evidence_release_control'),)

class ServiceAccount(Base, TimestampMixin):
    __tablename__='service_accounts'
    id=Column(Integer, primary_key=True)
    workspace_id=Column(Integer, ForeignKey('workspaces.id'), nullable=False, index=True)
    account_code=Column(String(80), nullable=False)
    token_hash=Column(String(128), nullable=False)
    permissions=Column(JSON, nullable=False)
    entity_codes=Column(JSON, nullable=True)
    active=Column(Boolean, nullable=False, default=True)
    expires_at=Column(DateTime, nullable=True)
    created_by=Column(String(320), nullable=False)
    __table_args__=(UniqueConstraint('workspace_id','account_code',name='uq_service_account_code'),)

class VarianceRun(Base, TimestampMixin):
    __tablename__='variance_runs'
    id=Column(Integer, primary_key=True)
    workspace_id=Column(Integer, ForeignKey('workspaces.id'), nullable=False, index=True)
    run_code=Column(String(120), unique=True, nullable=False, index=True)
    entity_id=Column(Integer, ForeignKey('entities.id'), nullable=False, index=True)
    actual_period=Column(String(20), nullable=False)
    baseline_type=Column(String(40), nullable=False)
    baseline_reference=Column(String(120), nullable=True)
    currency=Column(String(3), nullable=False)
    baseline_revenue=Column(MONEY, nullable=False)
    baseline_cogs=Column(MONEY, nullable=False)
    baseline_direct_opex=Column(MONEY, nullable=False)
    baseline_allocated_opex=Column(MONEY, nullable=False, default=Decimal('0'))
    actual_revenue=Column(MONEY, nullable=False)
    actual_cogs=Column(MONEY, nullable=False)
    actual_direct_opex=Column(MONEY, nullable=False)
    actual_allocated_opex=Column(MONEY, nullable=False, default=Decimal('0'))
    baseline_ebit=Column(MONEY, nullable=False)
    actual_ebit=Column(MONEY, nullable=False)
    ebit_variance=Column(MONEY, nullable=False)
    component_total=Column(MONEY, nullable=False)
    residual=Column(MONEY, nullable=False)
    status=Column(String(30), nullable=False)
    created_by=Column(String(320), nullable=False)

class VarianceComponent(Base):
    __tablename__='variance_components'
    id=Column(Integer, primary_key=True)
    variance_run_id=Column(Integer, ForeignKey('variance_runs.id'), nullable=False, index=True)
    component_order=Column(Integer, nullable=False)
    component_code=Column(String(80), nullable=False)
    label=Column(String(160), nullable=False)
    amount=Column(MONEY, nullable=False)
    direction=Column(String(20), nullable=False)
    source=Column(String(120), nullable=False)
    evidence=Column(JSON, nullable=True)
    __table_args__=(UniqueConstraint('variance_run_id','component_order',name='uq_variance_component_order'),)

class QualificationControl(Base, TimestampMixin):
    __tablename__='qualification_controls'
    id=Column(Integer, primary_key=True)
    workspace_id=Column(Integer, ForeignKey('workspaces.id'), nullable=False, index=True)
    control_code=Column(String(100), nullable=False)
    domain=Column(String(80), nullable=False)
    title=Column(String(220), nullable=False)
    control_type=Column(String(30), nullable=False, default='INTERNAL')
    requirement=Column(Text, nullable=False)
    status=Column(String(30), nullable=False, default='NOT_STARTED')
    evidence=Column(JSON, nullable=True)
    reviewer=Column(String(320), nullable=True)
    reviewed_at=Column(DateTime, nullable=True)
    expires_at=Column(DateTime, nullable=True)
    blocking=Column(Boolean, nullable=False, default=True)
    __table_args__=(UniqueConstraint('workspace_id','control_code',name='uq_qualification_control'),)

class IntegrationConnection(Base, TimestampMixin):
    __tablename__='integration_connections'
    id=Column(Integer, primary_key=True)
    workspace_id=Column(Integer, ForeignKey('workspaces.id'), nullable=False, index=True)
    connection_code=Column(String(80), nullable=False)
    connector_type=Column(String(80), nullable=False)
    config=Column(JSON, nullable=True)
    secret_reference=Column(String(255), nullable=True)
    status=Column(String(30), default='CONFIGURED', nullable=False)
    __table_args__=(UniqueConstraint('workspace_id','connection_code',name='uq_integration_connection'),)

class IntegrationRun(Base, TimestampMixin):
    __tablename__='integration_runs'
    id=Column(Integer, primary_key=True)
    connection_id=Column(Integer, ForeignKey('integration_connections.id'), nullable=False, index=True)
    run_code=Column(String(100), unique=True, nullable=False)
    correlation_id=Column(String(100), nullable=False)
    status=Column(String(30), nullable=False)
    records_processed=Column(Integer, default=0, nullable=False)
    error_message=Column(Text, nullable=True)

class WorkflowRun(Base, TimestampMixin):
    __tablename__='workflow_runs'
    id=Column(Integer, primary_key=True)
    workspace_id=Column(Integer, ForeignKey('workspaces.id'), nullable=False, index=True)
    workflow_name=Column(String(120), nullable=False)
    correlation_id=Column(String(100), unique=True, nullable=False)
    status=Column(String(30), nullable=False)
    payload=Column(JSON, nullable=True)

class AuditEvent(Base):
    __tablename__='audit_events'
    id=Column(Integer, primary_key=True)
    workspace_id=Column(Integer, ForeignKey('workspaces.id'), nullable=True, index=True)
    event_type=Column(String(120), nullable=False, index=True)
    actor=Column(String(320), nullable=False)
    actor_role=Column(String(64), nullable=True)
    entity_code=Column(String(40), nullable=True)
    object_type=Column(String(80), nullable=True)
    object_id=Column(String(120), nullable=True)
    previous_value=Column(JSON, nullable=True)
    new_value=Column(JSON, nullable=True)
    reason=Column(Text, nullable=True)
    request_id=Column(String(100), nullable=True)
    correlation_id=Column(String(100), nullable=True, index=True)
    source_system=Column(String(80), nullable=True)
    details=Column(Text, nullable=False)
    created_at=Column(DateTime, default=utcnow_naive, nullable=False)

class Notification(Base, TimestampMixin):
    __tablename__='notifications'
    id=Column(Integer, primary_key=True)
    workspace_id=Column(Integer, ForeignKey('workspaces.id'), nullable=False, index=True)
    recipient=Column(String(320), nullable=False)
    channel=Column(String(30), nullable=False)
    subject=Column(String(200), nullable=False)
    body=Column(Text, nullable=False)
    status=Column(String(30), default='PENDING', nullable=False)
