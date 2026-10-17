"""Package and qualify the exact clean committed candidate."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parents[3]
TASK = Path(__file__).resolve().parent
OUT = ROOT / '.pf/artifacts/yaml-read-performance-20261017'
CANDIDATE = TASK / 'candidate'
sha = json.loads((TASK / 'source-commit.json').read_text())['sha']
archive = TASK / ('processforge-1.2.0-dev-20261017-yaml-' + sha[:7] + '.zip')
assert not archive.exists(), 'archive_already_exists; inspect receipt'
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=CANDIDATE, text=True).strip() == sha
assert not subprocess.check_output(['git', 'status', '--porcelain'], cwd=CANDIDATE, text=True).strip()
env = os.environ.copy()
env['PYTHONDONTWRITEBYTECODE'] = '1'
temporary = TASK / 'archive-test-tmp'
temporary.mkdir(exist_ok=True)
env['TEMP'] = env['TMP'] = str(temporary)

def run(label, command, timeout):
    start = time.monotonic()
    result = subprocess.run(command, cwd=CANDIDATE, env=env, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout)
    row = {'command': command, 'returncode': result.returncode, 'elapsed_seconds': round(time.monotonic() - start, 3), 'stdout': result.stdout, 'stderr': result.stderr}
    (OUT / (label + '.json')).write_text(json.dumps(row, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'step': label, 'returncode': result.returncode, 'elapsed_seconds': row['elapsed_seconds'], 'tail': (result.stdout + result.stderr)[-1800:]}), flush=True)
    assert result.returncode == 0, label

cli = [sys.executable, '-B', str(CANDIDATE / 'bin/pf.py')]
run('release-pack', cli + ['release-pack', '--root', str(CANDIDATE), '--output', str(archive)], 180)
with zipfile.ZipFile(archive) as package:
    assert package.testzip() is None
    entries = len(package.infolist())
with archive.open('rb') as stream:
    digest = hashlib.file_digest(stream, 'sha256').hexdigest()
receipt = {'source_commit': sha, 'clean_candidate': True, 'archive': str(archive), 'size': archive.stat().st_size, 'sha256': digest, 'zip_entries': entries}
(OUT / 'archive.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
print(json.dumps(receipt), flush=True)
run('release-archive-test', cli + ['release-archive-test', '--root', str(CANDIDATE), '--archive', str(archive), '--extracted-test', 'quick'], 600)
