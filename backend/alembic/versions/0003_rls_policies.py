"""PostgreSQL row-level security policies for tenant-scoped tables.

Policies become fully effective when the runtime DB role is NOT the table owner (recommended production deployment).
The application also applies workspace filters at the service/API layer.
"""
from alembic import op

revision='0003_rls_policies'; down_revision='0002_enterprise_rc'; branch_labels=None; depends_on=None
TABLES=[
 'entities','tp_policies','financial_periods','calculations','adjustments','erp_postings','reconciliations','audit_events',
 'intercompany_partners','gl_accounts','profit_centers','products','source_imports','raw_financial_records','mapping_rules',
 'normalized_financial_records','allocation_rules','allocation_runs','forecast_versions','simulations','approval_requests',
 'journal_headers','exceptions','documents','ai_invocations','integration_connections','workflow_runs','notifications'
]

def upgrade():
    bind=op.get_bind()
    if bind.dialect.name!='postgresql': return
    for table in TABLES:
        op.execute(f'ALTER TABLE {table} ENABLE ROW LEVEL SECURITY')
        op.execute(f"DROP POLICY IF EXISTS {table}_workspace_policy ON {table}")
        op.execute(f"CREATE POLICY {table}_workspace_policy ON {table} USING (workspace_id = NULLIF(current_setting('app.workspace_id', true),'')::integer) WITH CHECK (workspace_id = NULLIF(current_setting('app.workspace_id', true),'')::integer)")

def downgrade():
    bind=op.get_bind()
    if bind.dialect.name!='postgresql': return
    for table in TABLES:
        op.execute(f'DROP POLICY IF EXISTS {table}_workspace_policy ON {table}')
        op.execute(f'ALTER TABLE {table} DISABLE ROW LEVEL SECURITY')
