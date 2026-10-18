import hashlib
import json
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[3]
assignment = 't02-pf-vision-alignment-r02-implement-explicit-work-context-resource-sea'
run = 'garage-t02-pf-vision-alignment-r02-implement-explicit-work-context-resou'
paths = [root / '.pf/assignments' / (assignment + '.yaml'), root / '.pf/runs' / run / 'run.yaml',
         root / '.pf/contexts/assignment-capsules' / (assignment + '.capsule.yaml'),
         root / '.pf/contexts/project-context.snapshot.yaml']
before = {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
result = subprocess.run([sys.executable, '-B', str(root / 'tools/processforge.py'), 'work-resolve', '--project-root', str(root),
                         '--run', run, '--assignment', assignment, '--context-id', assignment + '-capsule',
                         '--resource-id', 'project.process-forge:project-profile', '--json'], cwd=root,
                        capture_output=True, text=True, encoding='utf-8', timeout=120)
payload = json.loads(result.stdout)
after = {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
assert result.returncode == 1 and payload.get('reason') == 'legacy_contract_incomplete', (result.returncode, payload)
assert before == after
report = {'exit_code': result.returncode, 'payload': payload, 'stderr': result.stderr,
          'state_hashes': before, 'state_unchanged': True, 'fixture': 'actual main Work created by installed T08 core before T02 source feature'}
Path(__file__).with_name('main-legacy-proof.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('PASS: actual legacy Work explicitly blocked; assignment/run/capsule/project snapshot unchanged')
