"""posting schema compatibility for enterprise journal headers

Revision ID: 0004_posting_schema_compat
Revises: 0003_rls_policies
"""
from alembic import op
import sqlalchemy as sa

revision='0004_posting_schema_compat'; down_revision='0003_rls_policies'; branch_labels=None; depends_on=None

def upgrade():
    # v0.x required erp_postings.journal_id (legacy journal_entries FK).
    # Enterprise RC posts from journal_headers via journal_header_id, so the legacy
    # FK must be nullable or PostgreSQL rejects valid enterprise postings.
    op.alter_column('erp_postings','journal_id',existing_type=sa.Integer(),nullable=True)

def downgrade():
    # Safe downgrade only when no enterprise-only posting lacks a legacy journal_id.
    bind=op.get_bind()
    missing=bind.execute(sa.text('SELECT COUNT(*) FROM erp_postings WHERE journal_id IS NULL')).scalar()
    if missing:
        raise RuntimeError('Cannot downgrade: enterprise postings exist without legacy journal_id')
    op.alter_column('erp_postings','journal_id',existing_type=sa.Integer(),nullable=False)
