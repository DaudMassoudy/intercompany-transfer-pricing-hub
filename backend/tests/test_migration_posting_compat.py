from pathlib import Path

def test_posting_compat_migration_relaxes_legacy_journal_fk():
    migration = Path(__file__).resolve().parents[1] / 'alembic' / 'versions' / '0004_posting_schema_compat.py'
    text = migration.read_text(encoding='utf-8')
    assert "alter_column('erp_postings','journal_id'" in text
    assert 'nullable=True' in text

def test_enterprise_posting_model_uses_journal_header_id():
    model = Path(__file__).resolve().parents[1] / 'app' / 'models.py'
    text = model.read_text(encoding='utf-8')
    assert "journal_header_id=Column(Integer, ForeignKey('journal_headers.id'), nullable=True" in text
