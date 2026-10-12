from alembic import op
import sqlalchemy as sa

revision='0008_practicality_upgrade'
down_revision='0007_configurable_core'
branch_labels=None
depends_on=None


def upgrade():
    op.create_table(
        'benchmark_comparables',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('workspace_id',sa.Integer(),sa.ForeignKey('workspaces.id'),nullable=False),
        sa.Column('benchmark_code',sa.String(length=120),nullable=False),
        sa.Column('company_name',sa.String(length=240),nullable=False),
        sa.Column('country',sa.String(length=2),nullable=True),
        sa.Column('industry',sa.String(length=160),nullable=True),
        sa.Column('status',sa.String(length=30),nullable=False,server_default='POTENTIAL'),
        sa.Column('screening_reason',sa.Text(),nullable=True),
        sa.Column('notes',sa.Text(),nullable=True),
        sa.Column('evidence',sa.JSON(),nullable=True),
        sa.Column('created_by',sa.String(length=320),nullable=False),
        sa.Column('created_at',sa.DateTime(),nullable=False),
        sa.Column('updated_at',sa.DateTime(),nullable=False),
    )
    op.create_index('ix_benchmark_comparables_workspace_id','benchmark_comparables',['workspace_id'])
    op.create_index('ix_benchmark_comparables_benchmark_code','benchmark_comparables',['benchmark_code'])
    op.create_index('ix_benchmark_comparables_status','benchmark_comparables',['status'])
    op.create_table(
        'benchmark_financial_observations',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('comparable_id',sa.Integer(),sa.ForeignKey('benchmark_comparables.id'),nullable=False),
        sa.Column('fiscal_year',sa.Integer(),nullable=False),
        sa.Column('sales',sa.Numeric(20,6),nullable=True),
        sa.Column('ebit',sa.Numeric(20,6),nullable=True),
        sa.Column('cost_base',sa.Numeric(20,6),nullable=True),
        sa.Column('assets',sa.Numeric(20,6),nullable=True),
        sa.Column('pli',sa.Numeric(14,10),nullable=False),
        sa.Column('source_reference',sa.String(length=255),nullable=True),
        sa.UniqueConstraint('comparable_id','fiscal_year',name='uq_benchmark_comparable_year'),
    )
    op.create_index('ix_benchmark_financial_observations_comparable_id','benchmark_financial_observations',['comparable_id'])
    op.add_column('approval_requests',sa.Column('workflow_code',sa.String(length=120),nullable=True))
    op.add_column('approval_requests',sa.Column('workflow_version',sa.Integer(),nullable=True))
    op.add_column('journal_headers',sa.Column('template_code',sa.String(length=120),nullable=True))
    op.add_column('journal_headers',sa.Column('template_version',sa.Integer(),nullable=True))
    op.add_column('reconciliations',sa.Column('currency',sa.String(length=3),nullable=True))
    op.add_column('reconciliations',sa.Column('exception_code',sa.String(length=120),nullable=True))
    op.add_column('reconciliations',sa.Column('certified_by',sa.String(length=320),nullable=True))
    op.add_column('reconciliations',sa.Column('certified_at',sa.DateTime(),nullable=True))
    op.add_column('reconciliations',sa.Column('certification_comment',sa.Text(),nullable=True))


def downgrade():
    op.drop_column('reconciliations','certification_comment')
    op.drop_column('reconciliations','certified_at')
    op.drop_column('reconciliations','certified_by')
    op.drop_column('reconciliations','exception_code')
    op.drop_column('reconciliations','currency')
    op.drop_column('journal_headers','template_version')
    op.drop_column('journal_headers','template_code')
    op.drop_column('approval_requests','workflow_version')
    op.drop_column('approval_requests','workflow_code')
    op.drop_index('ix_benchmark_financial_observations_comparable_id',table_name='benchmark_financial_observations')
    op.drop_table('benchmark_financial_observations')
    op.drop_index('ix_benchmark_comparables_status',table_name='benchmark_comparables')
    op.drop_index('ix_benchmark_comparables_benchmark_code',table_name='benchmark_comparables')
    op.drop_index('ix_benchmark_comparables_workspace_id',table_name='benchmark_comparables')
    op.drop_table('benchmark_comparables')
