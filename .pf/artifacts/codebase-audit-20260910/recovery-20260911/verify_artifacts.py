"""Read-only source preservation and primary evidence assertions."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
baseline = json.loads((OUT.parent / 'baseline.json').read_text(encoding='utf-8'))
mismatches = []
for relative, expected in baseline['hashes'].items():
    target = ROOT / relative
    current = hashlib.sha256(target.read_bytes()).hexdigest() if target.is_file() else None
    if current != expected:
        mismatches.append({'path': relative, 'expected': expected, 'actual': current})
assert not mismatches, mismatches
collection = {x['case']: x for x in json.loads((OUT / 'collection-primary-results.json').read_text(encoding='utf-8'))}
assert [x['exit'] for x in collection['plain']['collect']] == [0, 0]
assert collection['plain']['assistant_count'] == 1
assert [x['exit'] for x in collection['path_content']['collect']] == [1, 1]
assert collection['path_content']['assistant_count'] == 0
assert all(x['diagnostics']['conversation']['reason'] == 'unsafe_automatic_content' for x in collection['path_content']['capture'])
assert collection['external_report']['assistant_count'] == 1
assert collection['external_report']['task_status'] == 'done'
assert 'OUTSIDE_FIXTURE_MARKER' in collection['external_report']['assistant_contents'][0]
runtime = {x['case']: x for x in json.loads((OUT / 'runtime_health.stdout.json').read_text(encoding='utf-8'))}
assert not runtime['missing_assignment']['scheduler_alive']
assert runtime['missing_assignment']['escaped'][0]['type'] == 'SystemExit'
assert runtime['invalid_task_order']['internal_health'] == 'degraded'
assert runtime['invalid_task_order']['reported_health'] == 'ready'
classification = json.loads((OUT / 'classification_origin.stdout.json').read_text(encoding='utf-8'))
assert classification['classification_equal'] is False
assert classification['source']['classifiers'][0]['sha256'] == classification['installed']['classifiers'][0]['sha256']
mcp = json.loads((OUT / 'mcp-primary-results.json').read_text(encoding='utf-8'))
assert not mcp['lower-session']['response'][0]['result'].get('isError')
mixed = json.loads(mcp['Case-Session']['response'][0]['result']['content'][0]['text'])
assert mixed['error']['code'] == 'unknown_session'
assert len(mcp['protocol']['notification']) == 1
assert 'result' in mcp['protocol']['bad_version'][0]
result = {'result': 'PASS', 'meaning': 'Audit evidence reproduces defects; not a product quality PASS.', 'source_files_checked': len(baseline['hashes']), 'source_mismatches': mismatches, 'primary_evidence_assertions': 'PASS'}
(OUT / 'source-preservation-and-evidence.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result, indent=2))
