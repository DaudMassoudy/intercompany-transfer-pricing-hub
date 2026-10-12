from alembic import op
import sqlalchemy as sa

revision='0009_practicality_10'
down_revision='0008_practicality_upgrade'
branch_labels=None
depends_on=None


def upgrade():
    for name,typ in [
        ('tested_party_code',sa.String(80)),('tolerance',sa.Numeric(14,10)),('cost_base',sa.String(80)),
        ('allocation_treatment',sa.String(80)),('currency',sa.String(3)),('journal_template_code',sa.String(120)),
        ('workflow_code',sa.String(120)),('created_by',sa.String(320)),('submitted_by',sa.String(320)),
        ('approved_by',sa.String(320)),('activated_by',sa.String(320)),('submitted_at',sa.DateTime()),
        ('approved_at',sa.DateTime()),('activated_at',sa.DateTime()),('notes',sa.Text())]:
        op.add_column('tp_policies',sa.Column(name,typ,nullable=True))
    op.add_column('adjustments',sa.Column('adjustment_type',sa.String(30),nullable=False,server_default='TRUE_UP'))
    op.add_column('adjustments',sa.Column('original_adjustment_id',sa.Integer(),sa.ForeignKey('adjustments.id'),nullable=True))
    op.add_column('adjustments',sa.Column('batch_code',sa.String(120),nullable=True))
    op.add_column('adjustments',sa.Column('target_type',sa.String(40),nullable=True))
    op.add_column('adjustments',sa.Column('target_value',sa.Numeric(14,10),nullable=True))
    op.add_column('adjustments',sa.Column('frequency',sa.String(30),nullable=True))
    op.add_column('adjustments',sa.Column('rounding_mode',sa.String(40),nullable=False,server_default='ROUND_HALF_UP'))
    op.add_column('adjustments',sa.Column('reason',sa.Text(),nullable=True))
    op.create_index('ix_adjustments_original_adjustment_id','adjustments',['original_adjustment_id'])
    op.create_index('ix_adjustments_batch_code','adjustments',['batch_code'])

    for name,typ in [('source',sa.String(80)),('currency',sa.String(3)),('root_cause',sa.Text()),('remediation',sa.Text()),
                     ('comments',sa.JSON()),('attachments',sa.JSON()),('sla_hours',sa.Integer()),('escalated_to',sa.String(320)),
                     ('waived_by',sa.String(320)),('waiver_reason',sa.Text()),('closed_by',sa.String(320)),('closed_at',sa.DateTime())]:
        op.add_column('exceptions',sa.Column(name,typ,nullable=True))

    for name,typ in [('expires_at',sa.String(10)),('tags',sa.JSON()),('linked_object_type',sa.String(80)),
                     ('linked_object_id',sa.String(120)),('metadata_json',sa.JSON())]:
        op.add_column('documents',sa.Column(name,typ,nullable=True))
    op.create_index('ix_documents_linked_object_type','documents',['linked_object_type'])
    op.create_index('ix_documents_linked_object_id','documents',['linked_object_id'])

    op.create_table('pnl_snapshots',
        sa.Column('id',sa.Integer(),primary_key=True),sa.Column('workspace_id',sa.Integer(),sa.ForeignKey('workspaces.id'),nullable=False),
        sa.Column('snapshot_code',sa.String(120),nullable=False,unique=True),sa.Column('pnl_run_id',sa.Integer(),sa.ForeignKey('pnl_runs.id'),nullable=False),
        sa.Column('scenario',sa.String(40),nullable=False,server_default='ACTUAL'),sa.Column('label',sa.String(160),nullable=True),
        sa.Column('status',sa.String(30),nullable=False,server_default='OPEN'),sa.Column('dimensions',sa.JSON(),nullable=True),
        sa.Column('comment',sa.Text(),nullable=True),sa.Column('locked_by',sa.String(320),nullable=True),sa.Column('locked_at',sa.DateTime(),nullable=True),
        sa.Column('created_at',sa.DateTime(),nullable=False),sa.Column('updated_at',sa.DateTime(),nullable=False))
    op.create_index('ix_pnl_snapshots_workspace_id','pnl_snapshots',['workspace_id']);op.create_index('ix_pnl_snapshots_pnl_run_id','pnl_snapshots',['pnl_run_id']);op.create_index('ix_pnl_snapshots_snapshot_code','pnl_snapshots',['snapshot_code'])

    op.create_table('reconciliation_stages',
        sa.Column('id',sa.Integer(),primary_key=True),sa.Column('reconciliation_id',sa.Integer(),sa.ForeignKey('reconciliations.id'),nullable=False),
        sa.Column('stage_order',sa.Integer(),nullable=False),sa.Column('stage_code',sa.String(60),nullable=False),
        sa.Column('source_amount',sa.Numeric(20,6),nullable=False),sa.Column('target_amount',sa.Numeric(20,6),nullable=False),
        sa.Column('difference',sa.Numeric(20,6),nullable=False),sa.Column('tolerance',sa.Numeric(20,6),nullable=False,server_default='0.01'),
        sa.Column('status',sa.String(30),nullable=False),sa.Column('reason',sa.Text(),nullable=True),sa.Column('linked_records',sa.JSON(),nullable=True),
        sa.Column('created_at',sa.DateTime(),nullable=False),sa.Column('updated_at',sa.DateTime(),nullable=False),
        sa.UniqueConstraint('reconciliation_id','stage_order',name='uq_reconciliation_stage_order'))
    op.create_index('ix_reconciliation_stages_reconciliation_id','reconciliation_stages',['reconciliation_id'])

    op.create_table('workflow_instances',
        sa.Column('id',sa.Integer(),primary_key=True),sa.Column('workspace_id',sa.Integer(),sa.ForeignKey('workspaces.id'),nullable=False),
        sa.Column('instance_code',sa.String(120),nullable=False,unique=True),sa.Column('workflow_code',sa.String(120),nullable=False),sa.Column('workflow_version',sa.Integer(),nullable=False),
        sa.Column('object_type',sa.String(80),nullable=False),sa.Column('object_id',sa.String(120),nullable=False),sa.Column('approval_mode',sa.String(30),nullable=False,server_default='SEQUENTIAL'),
        sa.Column('status',sa.String(30),nullable=False,server_default='PENDING'),sa.Column('created_by',sa.String(320),nullable=False),sa.Column('context',sa.JSON(),nullable=True),
        sa.Column('completed_at',sa.DateTime(),nullable=True),sa.Column('created_at',sa.DateTime(),nullable=False),sa.Column('updated_at',sa.DateTime(),nullable=False))
    for c in ['workspace_id','instance_code','object_type','object_id']: op.create_index(f'ix_workflow_instances_{c}','workflow_instances',[c])
    op.create_table('workflow_tasks',
        sa.Column('id',sa.Integer(),primary_key=True),sa.Column('workflow_instance_id',sa.Integer(),sa.ForeignKey('workflow_instances.id'),nullable=False),
        sa.Column('step_order',sa.Integer(),nullable=False),sa.Column('group_no',sa.Integer(),nullable=False,server_default='1'),sa.Column('required_role',sa.String(64),nullable=False),
        sa.Column('status',sa.String(30),nullable=False,server_default='PENDING'),sa.Column('actor',sa.String(320),nullable=True),sa.Column('delegated_from',sa.String(320),nullable=True),
        sa.Column('due_at',sa.DateTime(),nullable=True),sa.Column('comments',sa.Text(),nullable=True),sa.Column('decided_at',sa.DateTime(),nullable=True),
        sa.Column('created_at',sa.DateTime(),nullable=False),sa.Column('updated_at',sa.DateTime(),nullable=False))
    op.create_index('ix_workflow_tasks_workflow_instance_id','workflow_tasks',['workflow_instance_id'])
    op.create_table('user_delegations',
        sa.Column('id',sa.Integer(),primary_key=True),sa.Column('workspace_id',sa.Integer(),sa.ForeignKey('workspaces.id'),nullable=False),sa.Column('from_user',sa.String(320),nullable=False),
        sa.Column('to_user',sa.String(320),nullable=False),sa.Column('role',sa.String(64),nullable=True),sa.Column('effective_from',sa.DateTime(),nullable=False),sa.Column('effective_to',sa.DateTime(),nullable=False),
        sa.Column('active',sa.Boolean(),nullable=False,server_default=sa.true()),sa.Column('created_at',sa.DateTime(),nullable=False),sa.Column('updated_at',sa.DateTime(),nullable=False))
    op.create_index('ix_user_delegations_workspace_id','user_delegations',['workspace_id']);op.create_index('ix_user_delegations_from_user','user_delegations',['from_user']);op.create_index('ix_user_delegations_to_user','user_delegations',['to_user'])

    op.create_table('qualification_evidence',
        sa.Column('id',sa.Integer(),primary_key=True),sa.Column('workspace_id',sa.Integer(),sa.ForeignKey('workspaces.id'),nullable=False),sa.Column('release_version',sa.String(80),nullable=False),
        sa.Column('control_code',sa.String(100),nullable=False),sa.Column('category',sa.String(80),nullable=False),sa.Column('status',sa.String(30),nullable=False),
        sa.Column('environment',sa.String(120),nullable=True),sa.Column('result',sa.JSON(),nullable=True),sa.Column('evidence_path',sa.String(500),nullable=True),
        sa.Column('executed_by',sa.String(320),nullable=True),sa.Column('duration_ms',sa.Integer(),nullable=True),sa.Column('created_at',sa.DateTime(),nullable=False),sa.Column('updated_at',sa.DateTime(),nullable=False),
        sa.UniqueConstraint('workspace_id','release_version','control_code',name='uq_qualification_evidence_release_control'))
    for c in ['workspace_id','release_version','control_code']:op.create_index(f'ix_qualification_evidence_{c}','qualification_evidence',[c])

    op.create_table('service_accounts',
        sa.Column('id',sa.Integer(),primary_key=True),sa.Column('workspace_id',sa.Integer(),sa.ForeignKey('workspaces.id'),nullable=False),sa.Column('account_code',sa.String(80),nullable=False),
        sa.Column('token_hash',sa.String(128),nullable=False),sa.Column('permissions',sa.JSON(),nullable=False),sa.Column('entity_codes',sa.JSON(),nullable=True),
        sa.Column('active',sa.Boolean(),nullable=False,server_default=sa.true()),sa.Column('expires_at',sa.DateTime(),nullable=True),sa.Column('created_by',sa.String(320),nullable=False),
        sa.Column('created_at',sa.DateTime(),nullable=False),sa.Column('updated_at',sa.DateTime(),nullable=False),sa.UniqueConstraint('workspace_id','account_code',name='uq_service_account_code'))
    op.create_index('ix_service_accounts_workspace_id','service_accounts',['workspace_id'])


def downgrade():
    for table in ['service_accounts','qualification_evidence','user_delegations','workflow_tasks','workflow_instances','reconciliation_stages','pnl_snapshots']:
        op.drop_table(table)
    for c in ['metadata_json','linked_object_id','linked_object_type','tags','expires_at']:op.drop_column('documents',c)
    for c in ['closed_at','closed_by','waiver_reason','waived_by','escalated_to','sla_hours','attachments','comments','remediation','root_cause','currency','source']:op.drop_column('exceptions',c)
    for c in ['reason','rounding_mode','frequency','target_value','target_type','batch_code','original_adjustment_id','adjustment_type']:op.drop_column('adjustments',c)
    for c in ['notes','activated_at','approved_at','submitted_at','activated_by','approved_by','submitted_by','created_by','workflow_code','journal_template_code','currency','allocation_treatment','cost_base','tolerance','tested_party_code']:op.drop_column('tp_policies',c)
