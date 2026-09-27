import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
baseline = json.loads((HERE / 'baseline.json').read_text(encoding='utf-8'))
paths = [name for name in baseline['source_sha256'] if name != 'checksums/processforge.sha256']
paths.append('tools/smoke_prepared_execution_recovery.py')
result = {'started_at': datetime.now(timezone.utc).isoformat(), 'checks': []}
for name in paths:
    path = ROOT / name
    body = path.read_text(encoding='utf-8-sig')
    if path.suffix == '.py':
        ast.parse(body, filename=name)
    if path.suffix == '.md':
        assert not path.read_bytes().startswith(b'\xef\xbb\xbf'), name
        assert all(line == line.rstrip() for line in body.splitlines()), name
        for link in re.findall(r'\]\(([^)]+)\)', body):
            if not link.startswith(('http:', 'https:', '#')):
                assert (path.parent / link.split('#')[0]).exists(), (name, link)
result['syntax_and_changed_doc_links'] = 'PASS'
assert 'ReleaseCommand("smoke_prepared_execution_recovery"' in (ROOT / 'tools/processforge.py').read_text(encoding='utf-8')
frozen_changed = [name for name, value in baseline['frozen_sha256'].items()
                  if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != value]
assert not frozen_changed, frozen_changed
result['frozen_files_unchanged'] = len(baseline['frozen_sha256'])
for args in [['tools/validate-process-forge-schemas.py'], ['tools/validate-public-cleanliness.py'],
             ['tools/validate-process-forge-checksums.py', '--write'],
             ['tools/validate-process-forge-checksums.py', '--check'],
             ['bin/pf.py', 'run-doctor', '--project-root', str(ROOT), '--run',
              'garage-t06-pf-vision-alignment-r02-integrate-acceptance-for-work-resourc']]:
    run = subprocess.run([sys.executable, '-B', *args], cwd=ROOT, capture_output=True,
                         text=True, encoding='utf-8', timeout=240)
    result['checks'].append({'command': args, 'exit_code': run.returncode,
                             'stdout': run.stdout, 'stderr': run.stderr})
    print(args[0], args[1] if len(args) > 1 else '', run.returncode, flush=True)
    (HERE / 'final-checks.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    if run.returncode:
        raise SystemExit(run.returncode)
result['source_sha256'] = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                           for name in [*paths, 'checksums/processforge.sha256']}
result['finished_at'] = datetime.now(timezone.utc).isoformat()
(HERE / 'final-checks.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
print('PASS: source QA, registered recovery check, links and frozen evidence/capsule preservation')
