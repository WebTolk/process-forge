import hashlib
import json
import pathlib
import sqlite3
from collections import Counter
from contextlib import closing

projects = [pathlib.Path('D:/dev/process-forge'), pathlib.Path('D:/dev/wt-image-resize-and-convert-joomla-plugin')]
result = []
for project in projects:
    path = project / '.pf/runtime/events/events.ndjson'
    report = {'project': str(project), 'lines': 0, 'invalid': [], 'identical_duplicates': 0, 'conflicts': 0, 'changed_keys': Counter(), 'examples': []}
    with closing(sqlite3.connect('')) as db:
        db.execute('CREATE TABLE records (id TEXT PRIMARY KEY, digest TEXT, payload TEXT, line INTEGER)')
        with path.open('rb') as stream:
            for number, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                report['lines'] += 1
                try:
                    row = json.loads(line)
                    identifier = row.get('event_id') or row.get('id')
                    if not isinstance(identifier, str) or not identifier:
                        raise ValueError('event_id_required')
                    payload = json.dumps(row, ensure_ascii=False, sort_keys=True, allow_nan=False)
                except (ValueError, TypeError, AttributeError) as error:
                    report['invalid'].append({'line': number, 'error': str(error), 'bytes': len(line), 'sha256': hashlib.sha256(line).hexdigest()})
                    continue
                digest = hashlib.sha256(payload.encode('utf-8')).hexdigest()
                old = db.execute('SELECT digest, payload, line FROM records WHERE id=?', (identifier,)).fetchone()
                if old:
                    if old[0] == digest:
                        report['identical_duplicates'] += 1
                    else:
                        first = json.loads(old[1])
                        changed = sorted(key for key in set(first) | set(row) if first.get(key) != row.get(key))
                        report['conflicts'] += 1
                        report['changed_keys'].update(changed)
                        if len(report['examples']) < 12:
                            report['examples'].append({'id': identifier, 'first_line': old[2], 'line': number, 'changed_keys': changed, 'types': [first.get('event_type'), row.get('event_type')], 'payload_changed_keys': sorted(k for k in set(first.get('payload', {})) | set(row.get('payload', {})) if first.get('payload', {}).get(k) != row.get('payload', {}).get(k)) if isinstance(first.get('payload'), dict) and isinstance(row.get('payload'), dict) else None})
                else:
                    db.execute('INSERT INTO records VALUES (?,?,?,?)', (identifier, digest, payload, number))
        report['unique_ids'] = db.execute('SELECT COUNT(*) FROM records').fetchone()[0]
    result.append(report)
destination = pathlib.Path('.pf/artifacts/hook-sqlite-device-cutover-20261017/legacy-diagnostics.json')
destination.write_text(json.dumps(result, ensure_ascii=True, indent=2) + '\n', encoding='utf-8')
print(json.dumps(result, ensure_ascii=True, indent=2))
