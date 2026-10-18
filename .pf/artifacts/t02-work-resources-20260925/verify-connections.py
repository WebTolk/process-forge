import json
import sqlite3
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'src'))
from processforge_core import local_resource_search as search
from processforge_core.work_resources import WorkResourceService

original = sqlite3.connect
opened = []
def connect(*args, **kwargs):
    db = original(*args, **kwargs)
    opened.append(db)
    return db
def assert_closed():
    for db in opened:
        try:
            db.execute('SELECT 1')
        except sqlite3.ProgrammingError:
            pass
        else:
            raise AssertionError('connection remains open')
    opened.clear()

with tempfile.TemporaryDirectory(prefix='pf-t02-close-') as raw:
    root = Path(raw)
    db_path = search.index_path(root, None)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db = original(db_path)
    db.execute('CREATE TABLE documents(resource_id TEXT)')
    db.execute("INSERT INTO documents VALUES ('a')")
    db.commit()
    db.close()
    with patch.object(sqlite3, 'connect', side_effect=connect):
        assert search.authorized_coverage(root, {'local_search_resources': [{'id': 'a'}]})['status'] == 'complete'
        assert_closed()
        assert WorkResourceService._search([{'title': 'needle', 'content': 'needle'}], 'needle', 20, 0)['total'] == 1
        assert_closed()
        try:
            WorkResourceService._search([{'title': 'missing-content'}], 'needle', 20, 0)
        except KeyError:
            pass
        else:
            raise AssertionError('expected malformed document error')
        assert_closed()
    db = original(db_path)
    db.execute('DROP TABLE documents')
    db.commit()
    db.close()
    with patch.object(sqlite3, 'connect', side_effect=connect):
        assert search.authorized_coverage(root, {'local_search_resources': [{'id': 'a'}]})['status'] == 'unavailable'
        assert_closed()
result = {'status': 'PASS', 'checks': ['coverage success closes', 'coverage SQL failure closes', 'memory search success closes', 'memory search document failure closes', 'Windows temp cleanup without gc']}
Path(__file__).with_name('connection-verification.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
print(json.dumps(result))
