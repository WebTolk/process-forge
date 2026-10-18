"""Verify installed ownership and immutable main T08 evidence after live acceptance."""
import datetime
import hashlib
import json
import subprocess
import sys
from pathlib import Path
import yaml
out = Path(__file__).resolve().parent
root = out.parents[2]
installed = Path('D:/.agents/processforge')
workplace = Path('D:/.agents/processforge-workplace')
result = {'time_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}
manifest = json.loads((installed / 'processforge-core.manifest.json').read_text(encoding='utf-8'))
bad = []
for row in manifest['files']:
    path = installed / row['relative_path']
    actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else 'missing'
    if actual != row['sha256']:
        bad.append({'path': row['relative_path'], 'expected': row['sha256'], 'actual': actual})
result['installed_ownership'] = {'count': len(manifest['files']), 'mismatches': bad}
result['entrypoint_hashes'] = {name: hashlib.sha256((installed / name).read_bytes()).hexdigest() for name in ['tools/processforge.py', 'tools/pf_runtime/mcp_server.py']}
assignment_id = 't08-mcp-operability-reproduce-current-source-versus-installed-mcp-freshn'
assignment = yaml.safe_load((root / '.pf/assignments' / (assignment_id + '.yaml')).read_text(encoding='utf-8'))
registered = {}
for stage in assignment['stage_history']:
    for row in stage.get('evidence', []):
        if row.get('path') and row.get('sha256'):
            actual = 'sha256:' + hashlib.sha256((root / row['path']).read_bytes()).hexdigest()
            assert actual == row['sha256'], row['path']
            registered[row['path']] = actual
result['registered_evidence_unchanged'] = registered
capsule = assignment['process_execution']
result['capsule_unchanged'] = 'sha256:' + hashlib.sha256((root / capsule['assignment_capsule']).read_bytes()).hexdigest() == capsule['assignment_capsule_checksum']
before = json.loads((out / 'fixture-setup.json').read_text(encoding='utf-8'))['workplace_config_before']
after = {str(p.relative_to(workplace)): hashlib.sha256(p.read_bytes()).hexdigest() for p in [workplace / 'workplace.yaml', *sorted((workplace / 'registries').rglob('*.yaml'))]}
result['workplace_config_unchanged'] = before == after
cmd = [sys.executable, '-B', str(installed / 'bin/pf.py'), 'runtime', 'status', '--workplace', str(workplace), '--json']
r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', timeout=60)
assert r.returncode == 0, r.stderr
status = json.loads(r.stdout)
result['runtime'] = {k: status.get(k) for k in ['status', 'health', 'pid', 'started_at', 'runtime', 'last_scheduler_error']}
for label, args in [('source_work_state', ['work-state', '--project-root', str(root), '--run', assignment['run_id'], '--json'])]:
    r = subprocess.run([sys.executable, '-B', str(root / 'bin/pf.py'), *args], capture_output=True, text=True, encoding='utf-8', timeout=90)
    assert r.returncode == 0, r.stderr
    state = json.loads(r.stdout)
    result[label] = {k: state.get(k) for k in ['project', 'run', 'assignment', 'stage', 'process', 'work', 'blockers']}
tests = json.loads((out / 'installed-regressions-after-restart.json').read_text(encoding='utf-8'))
assert len(tests) == 6 and all(t['exit_code'] == 0 for t in tests)
result['installed_regressions'] = {'passed': len(tests), 'seconds': round(sum(t['seconds'] for t in tests), 3)}
assert not bad and result['capsule_unchanged'] and result['workplace_config_unchanged']
(out / 'final-verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(result, ensure_ascii=False, indent=2))
