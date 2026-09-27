from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
SCRATCH = ROOT / '.pf/tmp/t06-installed-delivery-20260926'
CANDIDATE = SCRATCH / 'candidate'
spec = importlib.util.spec_from_file_location('inventory', ROOT / 'tools/validate-process-forge-checksums.py')
inventory = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inventory)
result = {'started_at': datetime.now(timezone.utc).isoformat(), 'commands': []}

def run(argv, cwd=ROOT, timeout=180):
    proc = subprocess.run(list(map(str, argv)), cwd=cwd, capture_output=True, text=True, encoding='utf-8', timeout=timeout)
    row = {'argv': list(map(str, argv)), 'cwd': str(cwd), 'exit_code': proc.returncode,
           'stdout': proc.stdout, 'stderr': proc.stderr}
    result['commands'].append(row)
    (HERE / 'candidate-build.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    if proc.returncode:
        raise AssertionError(row)
    return proc.stdout.strip()

resume = '--resume' in sys.argv
assert not CANDIDATE.exists() or resume, 'Refuse overwriting an existing candidate'
assert CANDIDATE.resolve().is_relative_to((ROOT / '.pf/tmp').resolve())
result['main_head'] = run(['git', 'rev-parse', 'HEAD'])
result['main_status'] = run(['git', 'status', '--porcelain'])
entries = inventory.public_files(ROOT) + [ROOT / 'checksums/processforge.sha256']
files = {p.relative_to(ROOT).as_posix(): p for p in entries}
result['source_raw_sha256'] = {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in files.items()}
SCRATCH.mkdir(parents=True, exist_ok=True)
if resume:
    assert run(['git', 'rev-parse', 'HEAD'], cwd=CANDIDATE) == result['main_head']
else:
    run(['git', 'worktree', 'add', '--detach', CANDIDATE, result['main_head']])
for name, source in files.items():
    target = CANDIDATE / name
    assert target.resolve().is_relative_to(CANDIDATE.resolve()), name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
candidate_names = {p.relative_to(CANDIDATE).as_posix() for p in inventory.public_files(CANDIDATE)} | {'checksums/processforge.sha256'}
assert set(files) == candidate_names, {'missing': list(set(files) - candidate_names), 'extra': list(candidate_names - set(files))}
for name, source in files.items():
    assert inventory.released_content(source) == inventory.released_content(CANDIDATE / name), name
result['normalized_product_parity_count'] = len(files)
run([sys.executable, '-B', CANDIDATE / 'tools/validate-process-forge-checksums.py', '--check'], cwd=CANDIDATE)
pathspec = SCRATCH / 'candidate-pathspec.nul'
pathspec.write_bytes(b'\0'.join(name.encode('utf-8') for name in sorted(files)) + b'\0')
run(['git', 'add', '--pathspec-from-file=' + str(pathspec), '--pathspec-file-nul'], cwd=CANDIDATE)
result['candidate_diff_stat'] = run(['git', 'diff', '--cached', '--stat'], cwd=CANDIDATE)
run(['git', 'diff', '--cached', '--check'], cwd=CANDIDATE)
run(['git', 'commit', '-m', 'Qualify reviewed Work contracts and integrated acceptance for local Core delivery'], cwd=CANDIDATE)
result['candidate_commit'] = run(['git', 'rev-parse', 'HEAD'], cwd=CANDIDATE)
result['candidate_tree'] = run(['git', 'rev-parse', 'HEAD^{tree}'], cwd=CANDIDATE)
assert run(['git', 'status', '--porcelain'], cwd=CANDIDATE) == ''
result['candidate_clean'] = True
archive = HERE / 'delivery-package' / ('processforge-1.1.0-t06-' + result['candidate_commit'][:8] + '.zip')
result['archive'] = str(archive)
run([sys.executable, '-B', CANDIDATE / 'bin/pf.py', 'release-pack', '--root', CANDIDATE, '--output', archive], cwd=CANDIDATE)
result['archive_sha256'] = hashlib.sha256(archive.read_bytes()).hexdigest()
assert run(['git', 'rev-parse', 'HEAD']) == result['main_head']
for name, digest in result['source_raw_sha256'].items():
    assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
result['finished_at'] = datetime.now(timezone.utc).isoformat()
(HERE / 'candidate-build.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
print(json.dumps({key: result[key] for key in ['candidate_commit', 'candidate_tree', 'normalized_product_parity_count', 'archive', 'archive_sha256']}))
