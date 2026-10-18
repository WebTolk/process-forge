"""Private documentation-work preservation check; not a privacy-engine test."""
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]


def capture():
    listed = subprocess.check_output(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'], cwd=ROOT).decode('utf-8').split('\0')
    paths = {ROOT / p for p in listed if p and not p.startswith('.pf/') and (ROOT / p).is_file()}
    for parent in (ROOT / '.pf/artifacts', ROOT / '.pf/contexts/assignment-capsules', ROOT / '.pf/contexts/project-context.snapshots'):
        paths.update(p for p in parent.rglob('*') if p.is_file() and OUT not in p.parents and 'projections' not in p.parts and p.parent != ROOT / '.pf/artifacts')
    paths.update([ROOT / '.pf/contexts/project-context.snapshot.yaml', ROOT / '.pf/process-forge.yaml'])
    return {str(p.relative_to(ROOT)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}


mode = sys.argv[1]
current = capture()
if mode == 'baseline':
    target = OUT / 'baseline.json'
    assert not target.exists()
    target.write_text(json.dumps({'recorded_at': datetime.now(timezone.utc).isoformat(), 'files': current}, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'protected_files': len(current)}))
elif mode == 'verify':
    old = json.loads((OUT / 'baseline.json').read_text(encoding='utf-8'))['files']
    changed = [p for p, h in old.items() if current.get(p) != h]
    result = {'status': 'FAIL' if changed else 'PASS', 'protected_files': len(old), 'changed': changed}
    (OUT / 'boundary-result.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result))
    assert not changed
