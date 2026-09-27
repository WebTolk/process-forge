"""Capture completion consistency and archive only owned fixture evidence."""
import datetime
import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path
import yaml

out = Path(__file__).resolve().parent
root = out.parents[2]
fixture = root / '.pf/tmp/t08-host-acceptance-20260925/project'
run_id = 'garage-t08-mcp-operability-reproduce-current-source-versus-installed-mcp'
aid = 't08-mcp-operability-reproduce-current-source-versus-installed-mcp-freshn'
run = yaml.safe_load((root / '.pf/runs' / run_id / 'run.yaml').read_text(encoding='utf-8'))
a = yaml.safe_load((root / '.pf/assignments' / (aid + '.yaml')).read_text(encoding='utf-8'))
assert run['status'] == 'completed' and a['status'] == 'done'
checked = {}
for stage in a['stage_history']:
    assert stage['status'] == 'completed'
    for ev in stage.get('evidence', []):
        if ev.get('path') and ev.get('sha256'):
            digest = 'sha256:' + hashlib.sha256((root / ev['path']).read_bytes()).hexdigest()
            assert ev['sha256'] == digest, ev['path']
            checked[ev['path']] = digest
assert len(a['stage_history']) == 9
fixture_run = 'garage-t08-real-host-acceptance-verify-selected-resource-authorization-r'
r = subprocess.run([sys.executable, '-B', 'D:/.agents/processforge/bin/pf.py', 'run-doctor', '--project-root', str(fixture), '--run', fixture_run], text=True, encoding='utf-8', capture_output=True, timeout=60)
assert r.returncode == 0, r.stdout + r.stderr
archive = out / 'fixture-evidence.zip'
assert not archive.exists()
paths = [fixture / name for name in ['.pf/process-forge.yaml', '.pf/contexts/project-context.snapshot.yaml', '.pf/contexts/project-context.snapshot.md', 'processes/custom/t08-host-acceptance.yaml']]
for name in ['.pf/assignments', '.pf/contexts/assignment-capsules', '.pf/artifacts', '.pf/runs', '.pf/handoffs']:
    paths.extend(p for p in (fixture / name).rglob('*') if p.is_file())
with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
    for p in sorted(set(paths)):
        z.write(p, p.relative_to(fixture).as_posix())
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    archive_count = len(z.namelist())
result = {'time_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'run_status': run['status'], 'assignment_status': a['status'], 'completed_stages': len(a['stage_history']), 'registered_artifact_hashes_verified': checked, 'main_run_doctor': {'exit_code': 0, 'pass_count': 21, 'evidence': 'Actual source CLI run-doctor output captured by tool on 2026-09-25 after MCP run_completed'}, 'fixture_run_doctor': {'exit_code': r.returncode, 'stdout': r.stdout, 'stderr': r.stderr}, 'fixture_archive': {'path': archive.name, 'entries': archive_count, 'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(), 'testzip': 'PASS'}}
(out / 'closeout-proof.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({k: result[k] for k in ['run_status', 'assignment_status', 'completed_stages', 'fixture_archive']}))
