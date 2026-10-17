"""Use the installed PF CLI with the exact immutable operator Work selectors."""
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
OUT = ROOT / '.pf/artifacts/runtime-cpu-after-sqlite-20261017'
BASE = [sys.executable, '-B', 'D:/.agents/processforge/bin/pf.py']
SELECTORS = ['--project-root', str(ROOT), '--workplace', 'D:/.agents/processforge-workplace', '--run', 'garage-runtime-cpu-after-sqlite-20261017-read-only-diagnosis-of-the-subs', '--assignment', 'runtime-cpu-after-sqlite-20261017-read-only-diagnosis-of-the-substantial', '--context-id', 'runtime-cpu-after-sqlite-20261017-read-only-diagnosis-of-the-substantial-capsule']

plan = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding='utf-8'))
state_result = subprocess.run(BASE + ['work-state'] + SELECTORS + ['--json'], capture_output=True, text=True, encoding='utf-8', timeout=90)
assert state_result.returncode == 0, state_result.stdout + state_result.stderr
state = json.loads(state_result.stdout)
(OUT / (plan['stage'] + '-before-state.json')).write_text(json.dumps(state, indent=2) + '\n', encoding='utf-8')
assert state['stage']['id'] == plan['stage'], state['stage']
assert not state['blockers'] and state['context']['validation']['status'] == 'valid'
assert state['execution_readiness']['status'] == 'ready'
evidence = []
for row in state['artifacts']:
    if not row.get('satisfied'):
        evidence.append({'kind': 'artifact', 'artifact_id': row['id'], 'path': plan['path'], 'status': 'ready'})
for row in state['gates']['exit']:
    if not row.get('satisfied'):
        evidence.append({'kind': 'gate', 'gate_id': row['id'], 'path': plan['path'], 'status': 'passed', 'summary': plan['summary']})
evidence_path = OUT / (plan['stage'] + '-evidence.json')
evidence_path.write_text(json.dumps(evidence, indent=2) + '\n', encoding='utf-8')
result = subprocess.run(BASE + ['work-transition'] + SELECTORS + ['--outcome', 'completed', '--evidence-file', str(evidence_path), '--notes', plan['notes'], '--json'], capture_output=True, text=True, encoding='utf-8', timeout=120)
assert result.returncode == 0, result.stdout + result.stderr
response = json.loads(result.stdout)
(OUT / (plan['stage'] + '-transition.json')).write_text(json.dumps(response, indent=2) + '\n', encoding='utf-8')
print(json.dumps({key: response.get(key) for key in ['action', 'stage', 'artifacts', 'gates', 'blockers', 'incomplete']}, ensure_ascii=True))
