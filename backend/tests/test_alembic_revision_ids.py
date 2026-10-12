from pathlib import Path
import re


def test_all_alembic_revision_ids_fit_default_version_column():
    versions = Path(__file__).resolve().parents[1] / 'alembic' / 'versions'
    found = []
    for path in versions.glob('*.py'):
        text = path.read_text(encoding='utf-8')
        m = re.search(r"revision\s*=\s*['\"]([^'\"]+)['\"]", text)
        assert m, f'No revision id found in {path.name}'
        rev = m.group(1)
        found.append((path.name, rev))
        assert len(rev) <= 32, f'{path.name}: Alembic revision id {rev!r} has {len(rev)} chars; maximum is 32'
    assert found
