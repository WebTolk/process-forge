import hashlib
import json
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import yaml

OUT = Path(__file__).resolve().parent
REPO = OUT.parents[3]
CORE = Path('D:/.agents/processforge')
FIXTURE = REPO / '.pf/tmp/t06-host-acceptance-20260926/project'
RUN = 'garage-t06-pf-vision-alignment-r02-integrate-acceptance-for-work-resourc'
ASSIGNMENT = 't06-pf-vision-alignment-r02-integrate-acceptance-for-work-resources-norm'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


result = {'time_utc': datetime.now(timezone.utc).isoformat(), 'commands': []}
for args in ([sys.executable, '-B', str(CORE / 'bin/pf.py'), 'run-doctor', '--project-root', str(REPO), '--run', RUN],
             ['git', '-c', 'core.safecrlf=false', 'diff', '--check']):
    completed = subprocess.run(args, cwd=REPO, capture_output=True, text=True, encoding='utf-8', timeout=120)
    result['commands'].append({'argv': args, 'exit_code': completed.returncode, 'stdout': completed.stdout, 'stderr': completed.stderr})
    (OUT / 'final-checks.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    assert completed.returncode == 0, completed.stdout + completed.stderr

task = yaml.safe_load((REPO / '.pf/assignments' / (ASSIGNMENT + '.yaml')).read_text(encoding='utf-8'))
run = yaml.safe_load((REPO / '.pf/runs' / RUN / 'run.yaml').read_text(encoding='utf-8'))
assert task['status'] == 'done' and run['status'] == 'completed'
assert sha(REPO / '.pf/contexts/assignment-capsules' / (ASSIGNMENT + '.capsule.yaml')) == '8bd7af0ba78c19c7c3aedb3e80d8d45436511ed0fa4090e501b1536dfa5467a6'
assert sha(REPO / '.pf/contexts/project-context.snapshot.yaml') == 'f73d8d332313f45a99d4e7b943e18bf4e812b44a51d4d8c682e8291b0753a562'
evidence_checked = []
for stage in task['stage_history']:
    for e in stage.get('evidence', []):
        if e.get('path') and e.get('sha256'):
            assert 'sha256:' + sha(REPO / e['path']) == e['sha256'], e['path']
            evidence_checked.append(e['path'])
result['lifecycle'] = {'run_status': run['status'], 'assignment_status': task['status'], 'history_stages': [r['stage_id'] for r in task['stage_history']], 'evidence_checks': len(evidence_checked), 'original_capsule_unchanged': True, 'snapshot_unchanged': True}

# Preserve the entire isolated fixture for reproduction before temporary cleanup.
archive = OUT / 'fixture-evidence.zip'
assert not archive.exists(), 'Archive is immutable once created'
files = [p for p in sorted(FIXTURE.rglob('*')) if p.is_file()]
assert not any(p.is_symlink() for p in files)
inventory = {p.relative_to(FIXTURE).as_posix(): sha(p) for p in files}
with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED) as handle:
    for p in files:
        handle.write(p, p.relative_to(FIXTURE).as_posix())
with zipfile.ZipFile(archive) as handle:
    assert set(handle.namelist()) == set(inventory)
    assert all(hashlib.sha256(handle.read(name)).hexdigest() == value for name, value in inventory.items())
result['fixture_archive'] = {'path': str(archive.relative_to(REPO)), 'sha256': sha(archive), 'file_count': len(inventory), 'files': inventory}

delivery = REPO / '.pf/tmp/t06-installed-delivery-20260926'
candidate = delivery / 'candidate'
head = subprocess.check_output(['git', '-C', str(candidate), 'rev-parse', 'HEAD'], text=True).strip()
status = subprocess.check_output(['git', '-C', str(candidate), 'status', '--porcelain'], text=True)
assert head == '69110c50559d994d7a31e751b7cd7afc989698db' and not status
cleanup = {'candidate': {'path': str(candidate.resolve()), 'head': head, 'status': status}, 'extracted': []}
for directory in (delivery / 'extracted', delivery / 'extracted-corrected'):
    manifest = json.loads((directory / 'processforge-core.manifest.json').read_text(encoding='utf-8'))
    mismatches = [r['relative_path'] for r in manifest['files'] if not (directory / r['relative_path']).is_file() or sha(directory / r['relative_path']) != r['sha256']]
    cleanup['extracted'].append({'path': str(directory.resolve()), 'owned_count': len(manifest['files']), 'mismatches': mismatches})
result['cleanup_preflight'] = cleanup
result['status'] = 'PASS'
(OUT / 'final-checks.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'status': 'PASS', 'run': result['lifecycle'], 'archive_files': len(inventory), 'archive_sha256': sha(archive), 'cleanup': cleanup}))
