"""Native one-shot Core update and managed Runtime restart for this archive."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
TASK = Path(__file__).resolve().parent
OUT = ROOT / '.pf/artifacts/yaml-read-performance-20261017'
CORE = Path('D:/.agents/processforge')
WORKPLACE = Path('D:/.agents/processforge-workplace')
SERVICE = WORKPLACE / 'runtime/pf-runtime/service.json'
CLI = [sys.executable, '-B', str(CORE / 'bin/pf.py')]
archive = json.loads((OUT / 'archive.json').read_text())

def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def run(label, arguments, timeout=180, allow_failure=False):
    target = OUT / (label + '.json')
    assert not target.exists(), label + '_already_attempted; inspect saved result'
    start = time.monotonic()
    result = subprocess.run(CLI + arguments, cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout)
    row = {'command': CLI + arguments, 'returncode': result.returncode, 'elapsed_seconds': round(time.monotonic() - start, 3), 'stdout': result.stdout, 'stderr': result.stderr}
    target.write_text(json.dumps(row, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'step': label, 'returncode': result.returncode, 'elapsed_seconds': row['elapsed_seconds'], 'tail': (result.stdout + result.stderr)[-1000:]}), flush=True)
    assert allow_failure or result.returncode == 0, label
    return row

def service(label):
    row = json.loads(SERVICE.read_text(encoding='utf-8'))
    row.pop('token_ref', None)
    row.pop('token_hash', None)
    (OUT / (label + '.json')).write_text(json.dumps(row, indent=2) + '\n', encoding='utf-8')
    return row

assert digest(Path(archive['archive'])) == archive['sha256'], 'archive_hash_changed'
mode = sys.argv[1]
if mode == 'plan':
    assert not (OUT / 'configuration-preimages.json').exists()
    configurations = [ROOT / '.pf/process-forge.yaml', CORE / '.pf/process-forge.yaml', WORKPLACE / 'configuration.yaml', ROOT / '.pf/configuration.yaml', Path('D:/dev/wt-image-resize-and-convert-joomla-plugin/.pf/configuration.yaml')]
    preimages = [{'path': str(path), 'exists': path.exists(), 'sha256': digest(path) if path.is_file() else None} for path in configurations]
    (OUT / 'configuration-preimages.json').write_text(json.dumps(preimages, indent=2) + '\n', encoding='utf-8')
    before = service('runtime-before-update')
    assert before['pid'] == 9716 and before['instance_id'] == '1c0b979a99bb4da095fa7e1510d0e141', 'Runtime owner changed; inspect'
    row = run('core-update-plan', ['core-update', 'plan', '--core-root', str(CORE), '--archive', archive['archive'], '--workplace-root', str(WORKPLACE)])
    plan = json.loads(row['stdout'])
    assert not plan['blockers'], plan['blockers']
    assert plan['counts']['added'] == 4 and plan['counts']['changed'] == 7 and plan['counts']['removed'] == 0, plan['counts']
    assert plan['locally_modified'] == ['.pf/process-forge.yaml'], plan['locally_modified']
    print(json.dumps({'reviewed_counts': plan['counts'], 'blockers': plan['blockers']}), flush=True)
elif mode == 'apply':
    assert json.loads((OUT / 'release-archive-test.json').read_text())['returncode'] == 0, 'archive_not_qualified'
    assert json.loads((OUT / 'core-update-plan.json').read_text())['returncode'] == 0
    assert not (OUT / 'core-update-apply.json').exists(), 'apply_already_attempted; inspect native status'
    current = json.loads(SERVICE.read_text(encoding='utf-8'))
    assert current['pid'] == 9716 and current['instance_id'] == '1c0b979a99bb4da095fa7e1510d0e141', 'Runtime owner changed; inspect'
    stop = run('managed-stop', ['server', 'stop', '--workplace', str(WORKPLACE), '--timeout', '30'], allow_failure=True)
    if stop['returncode']:
        # The operator already authorized the owned managed-service restart.
        # Force is restricted to a native busy/unknown quiescence refusal.
        assert any(word in (stop['stdout'] + stop['stderr']).lower() for word in ('busy', 'unknown')), 'Unexpected stop failure'
        run('managed-stop-force', ['server', 'stop', '--workplace', str(WORKPLACE), '--timeout', '30', '--force'])
    assert not (WORKPLACE / 'runtime/pf-runtime/runtime.lock').exists(), 'Runtime remains owned'
    run('core-update-before-status', ['core-update', 'status', '--core-root', str(CORE)])
    run('core-update-apply', ['core-update', 'apply', '--core-root', str(CORE), '--archive', archive['archive'], '--workplace-root', str(WORKPLACE), '--confirm'], timeout=600)
    status = run('core-update-after-status', ['core-update', 'status', '--core-root', str(CORE)])
    assert json.loads(status['stdout'])['incomplete_update'] is False, 'incomplete_update'
    manifest = json.loads((CORE / 'processforge-core.manifest.json').read_text(encoding='utf-8'))
    assert manifest['source']['commit'] == archive['source_commit'] and not manifest['source']['dirty']
    failures = []
    verified = 0
    preserved = []
    for row in manifest['files']:
        relative = row['relative_path']
        actual = digest(CORE / relative) if (CORE / relative).is_file() else None
        if relative == '.pf/process-forge.yaml':
            preserved.append({'path': relative, 'expected': row['sha256'], 'actual': actual})
        elif actual != row['sha256']:
            failures.append({'path': relative, 'expected': row['sha256'], 'actual': actual})
        else:
            verified += 1
    configurations = []
    for row in json.loads((OUT / 'configuration-preimages.json').read_text()):
        path = Path(row['path'])
        same = path.exists() == row['exists'] and (digest(path) if path.is_file() else None) == row['sha256']
        configurations.append({'path': row['path'], 'unchanged': same})
    proof = {'source': manifest['source'], 'version': manifest['version'], 'verified_files': verified, 'preserved_local_files': preserved, 'failures': failures, 'configuration_preimages': configurations}
    (OUT / 'installed-byte-proof.json').write_text(json.dumps(proof, indent=2) + '\n', encoding='utf-8')
    assert not failures and all(row['unchanged'] for row in configurations), 'Installed byte proof failed'
    run('updated-runtime-start', ['server', 'start', '--workplace', str(WORKPLACE), '--timeout', '30'], timeout=90)
    after = service('runtime-after-start')
    assert after['pid'] != 9716 and after['instance_id'] != current['instance_id'] and after['status'] == 'ready'
    run('installed-context-check', ['project-context-check', '--project-root', str(ROOT), '--workplace', str(WORKPLACE), '--json'])
    print(json.dumps({'new_pid': after['pid'], 'new_instance': after['instance_id'], 'started_at': after['started_at'], 'source_commit': archive['source_commit'], 'verified_installed_files': verified}), flush=True)
else:
    raise SystemExit('mode must be plan or apply')
