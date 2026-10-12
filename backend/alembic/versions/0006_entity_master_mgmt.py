"""governed legal entity master management

Revision ID: 0006_entity_master_mgmt
Revises: 0005_pnl_variance_qual
"""
from alembic import op
import sqlalchemy as sa

revision='0006_entity_master_mgmt'
down_revision='0005_pnl_variance_qual'
branch_labels=None
depends_on=None


def upgrade():
    op.create_table('entity_versions',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('workspace_id',sa.Integer(),sa.ForeignKey('workspaces.id'),nullable=False),
        sa.Column('entity_id',sa.Integer(),sa.ForeignKey('entities.id'),nullable=False),
        sa.Column('version_no',sa.Integer(),nullable=False),
        sa.Column('snapshot',sa.JSON(),nullable=False),
        sa.Column('effective_from',sa.String(10),nullable=True),
        sa.Column('effective_to',sa.String(10),nullable=True),
        sa.Column('approved_by',sa.String(320),nullable=False),
        sa.Column('approval_request_code',sa.String(120),nullable=True),
        sa.Column('created_at',sa.DateTime(),nullable=False,server_default=sa.func.now()),
        sa.UniqueConstraint('entity_id','version_no',name='uq_entity_version_no'))
    op.create_index('ix_entity_versions_workspace_id','entity_versions',['workspace_id'])
    op.create_index('ix_entity_versions_entity_id','entity_versions',['entity_id'])

    op.create_table('entity_change_requests',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('workspace_id',sa.Integer(),sa.ForeignKey('workspaces.id'),nullable=False),
        sa.Column('entity_id',sa.Integer(),sa.ForeignKey('entities.id'),nullable=True),
        sa.Column('request_code',sa.String(120),nullable=False,unique=True),
        sa.Column('entity_code',sa.String(40),nullable=False),
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
    op.create_index('ix_entity_change_requests_workspace_id','entity_change_requests',['workspace_id'])
    op.create_index('ix_entity_change_requests_entity_id','entity_change_requests',['entity_id'])
    op.create_index('ix_entity_change_requests_request_code','entity_change_requests',['request_code'],unique=True)
    op.create_index('ix_entity_change_requests_entity_code','entity_change_requests',['entity_code'])
    op.create_index('ix_entity_change_requests_status','entity_change_requests',['status'])
    op.create_index('ix_entity_change_requests_batch_code','entity_change_requests',['batch_code'])

    bind=op.get_bind()
    if bind.dialect.name=='postgresql':
        for table in ['entity_versions','entity_change_requests']:
            op.execute(f'ALTER TABLE {table} ENABLE ROW LEVEL SECURITY')
            op.execute(f"CREATE POLICY {table}_workspace_policy ON {table} USING (workspace_id = NULLIF(current_setting('app.workspace_id', true),'')::integer) WITH CHECK (workspace_id = NULLIF(current_setting('app.workspace_id', true),'')::integer)")


def downgrade():
    bind=op.get_bind()
    if bind.dialect.name=='postgresql':
        for table in ['entity_versions','entity_change_requests']:
            op.execute(f'DROP POLICY IF EXISTS {table}_workspace_policy ON {table}')
    op.drop_table('entity_change_requests')
    op.drop_table('entity_versions')
