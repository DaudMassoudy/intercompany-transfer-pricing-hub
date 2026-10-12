"""configurable enterprise master data and allocation workbench

Revision ID: 0007_configurable_core
Revises: 0006_entity_master_mgmt
"""
from alembic import op
import sqlalchemy as sa

revision='0007_configurable_core'
down_revision='0006_entity_master_mgmt'
branch_labels=None
depends_on=None


def upgrade():
    # Governance state must affect the operational projections consumed by
    # ingestion/mapping services; deactivated masters are not merely cosmetic.
    op.add_column('intercompany_partners', sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column('gl_accounts', sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column('profit_centers', sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column('products', sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.true()))
    op.create_table('master_data_records',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('workspace_id',sa.Integer(),sa.ForeignKey('workspaces.id'),nullable=False),
        sa.Column('domain',sa.String(60),nullable=False),
        sa.Column('record_code',sa.String(120),nullable=False),
        sa.Column('name',sa.String(240),nullable=False),
        sa.Column('attributes',sa.JSON(),nullable=False),
        sa.Column('active',sa.Boolean(),nullable=False,server_default=sa.true()),
        sa.Column('effective_from',sa.String(10),nullable=True),
        sa.Column('effective_to',sa.String(10),nullable=True),
        sa.Column('version_no',sa.Integer(),nullable=False,server_default='1'),
        sa.Column('approved_by',sa.String(320),nullable=True),
        sa.Column('approval_request_code',sa.String(120),nullable=True),
        sa.Column('created_at',sa.DateTime(),nullable=False,server_default=sa.func.now()),
        sa.Column('updated_at',sa.DateTime(),nullable=False,server_default=sa.func.now()),
        sa.UniqueConstraint('workspace_id','domain','record_code',name='uq_master_record_workspace_domain_code'))
    op.create_index('ix_master_data_records_workspace_id','master_data_records',['workspace_id'])
    op.create_index('ix_master_data_records_domain','master_data_records',['domain'])
    op.create_index('ix_master_data_records_record_code','master_data_records',['record_code'])

    op.create_table('master_data_versions',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('workspace_id',sa.Integer(),sa.ForeignKey('workspaces.id'),nullable=False),
        sa.Column('domain',sa.String(60),nullable=False),
        sa.Column('record_code',sa.String(120),nullable=False),
        sa.Column('version_no',sa.Integer(),nullable=False),
        sa.Column('snapshot',sa.JSON(),nullable=False),
        sa.Column('approved_by',sa.String(320),nullable=False),
        sa.Column('approval_request_code',sa.String(120),nullable=True),
        sa.Column('created_at',sa.DateTime(),nullable=False,server_default=sa.func.now()),
        sa.UniqueConstraint('workspace_id','domain','record_code','version_no',name='uq_master_version_domain_code_no'))
    op.create_index('ix_master_data_versions_workspace_id','master_data_versions',['workspace_id'])
    op.create_index('ix_master_data_versions_domain','master_data_versions',['domain'])
    op.create_index('ix_master_data_versions_record_code','master_data_versions',['record_code'])

    op.create_table('master_data_change_requests',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('workspace_id',sa.Integer(),sa.ForeignKey('workspaces.id'),nullable=False),
        sa.Column('domain',sa.String(60),nullable=False),
        sa.Column('record_code',sa.String(120),nullable=False),
        sa.Column('request_code',sa.String(120),nullable=False,unique=True),
        sa.Column('change_type',sa.String(30),nullable=False),
        sa.Column('status',sa.String(30),nullable=False,server_default='DRAFT'),
        sa.Column('payload',sa.JSON(),nullable=False),
        sa.Column('reason',sa.Text(),nullable=True),
        sa.Column('batch_code',sa.String(120),nullable=True),
        sa.Column('created_by',sa.String(320),nullable=False),
        sa.Column('submitted_by',sa.String(320),nullable=True),
        sa.Column('reviewed_by',sa.String(320),nullable=True),
        sa.Column('submitted_at',sa.DateTime(),nullable=True),
        sa.Column('reviewed_at',sa.DateTime(),nullable=True),
        sa.Column('created_at',sa.DateTime(),nullable=False,server_default=sa.func.now()),
        sa.Column('updated_at',sa.DateTime(),nullable=False,server_default=sa.func.now()))
    for col in ['workspace_id','domain','record_code','request_code','status','batch_code']:
        op.create_index(f'ix_master_data_change_requests_{col}','master_data_change_requests',[col],unique=(col=='request_code'))

    # AllocationRule becomes a configurable workbench object. Existing RC.10
    # records remain valid through conservative defaults.
    columns=[
        sa.Column('cost_pool_type',sa.String(60),nullable=False,server_default='CUSTOM'),
        sa.Column('sender_entity_code',sa.String(40),nullable=True),
        sa.Column('period_scope',sa.String(40),nullable=False,server_default='MONTHLY'),
        sa.Column('currency',sa.String(3),nullable=False,server_default='EUR'),
        sa.Column('source_accounts',sa.JSON(),nullable=True),
        sa.Column('source_cost_centers',sa.JSON(),nullable=True),
        sa.Column('source_profit_centers',sa.JSON(),nullable=True),
        sa.Column('source_transactions',sa.JSON(),nullable=True),
        sa.Column('source_amount_source',sa.String(40),nullable=False,server_default='MANUAL_CONTROLLED'),
        sa.Column('manual_amount_allowed',sa.Boolean(),nullable=False,server_default=sa.true()),
        sa.Column('driver_source',sa.String(40),nullable=False,server_default='MANUAL_CONTROLLED'),
        sa.Column('driver_weights',sa.JSON(),nullable=True),
        sa.Column('stages',sa.JSON(),nullable=True),
        sa.Column('recipient_rules',sa.JSON(),nullable=True),
        sa.Column('markup_treatment',sa.String(40),nullable=False,server_default='NO_MARKUP'),
        sa.Column('markup_rate',sa.Numeric(14,10),nullable=True),
        sa.Column('fx_methodology',sa.String(80),nullable=True),
        sa.Column('fx_version',sa.String(80),nullable=True),
        sa.Column('effective_from',sa.String(10),nullable=True),
        sa.Column('effective_to',sa.String(10),nullable=True),
        sa.Column('created_by',sa.String(320),nullable=True),
        sa.Column('approved_at',sa.DateTime(),nullable=True),
    ]
    for col in columns: op.add_column('allocation_rules',col)

    bind=op.get_bind()
    if bind.dialect.name=='postgresql':
        for table in ['master_data_records','master_data_versions','master_data_change_requests']:
            op.execute(f'ALTER TABLE {table} ENABLE ROW LEVEL SECURITY')
            op.execute(f"CREATE POLICY {table}_workspace_policy ON {table} USING (workspace_id = NULLIF(current_setting('app.workspace_id', true),'')::integer) WITH CHECK (workspace_id = NULLIF(current_setting('app.workspace_id', true),'')::integer)")


def downgrade():
    bind=op.get_bind()
    if bind.dialect.name=='postgresql':
        for table in ['master_data_records','master_data_versions','master_data_change_requests']:
            op.execute(f'DROP POLICY IF EXISTS {table}_workspace_policy ON {table}')
    for table in ['products','profit_centers','gl_accounts','intercompany_partners']:
        op.drop_column(table,'active')
    for col in ['approved_at','created_by','effective_to','effective_from','fx_version','fx_methodology','markup_rate','markup_treatment','recipient_rules','stages','driver_weights','driver_source','manual_amount_allowed','source_amount_source','source_transactions','source_profit_centers','source_cost_centers','source_accounts','currency','period_scope','sender_entity_code','cost_pool_type']:
        op.drop_column('allocation_rules',col)
    op.drop_table('master_data_change_requests')
    op.drop_table('master_data_versions')
    op.drop_table('master_data_records')
