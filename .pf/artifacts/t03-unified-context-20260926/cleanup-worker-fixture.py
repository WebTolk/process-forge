import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
parent = (ROOT / '.pf/tmp').resolve()
paths = [parent / '.pf-worker-shell-3c9c38d0e0b447fdb08a9d12c5f62160', parent / '.pf-worker-shell-driver-a03492958e864563a63b29da59d4e2e4']
result = {'reason': 'T03 old shell-smoke cleanup expected terminal but the newly accepted comment-only prepare left state ready', 'stops': []}
for path in paths:
    path = path.resolve()
    assert path.is_relative_to(parent) and path != parent
    project = path / 'project'
    for status in (project / '.pf/runtime/agent-runs').glob('*/*/status.yaml'):
        raise AssertionError('unexpected YAML state location')
    for status in (project / '.pf/runtime/agent-runs').glob('*/*/status.json'):
        data = json.loads(status.read_text(encoding='utf-8'))
        if data.get('status') not in {'completed','failed','timed_out','unknown_exit','lost','cancelled','stopped'}:
            run = subprocess.run([sys.executable,'-B',str(ROOT/'tools/processforge.py'),'worker-run','stop','--project-root',str(project),'--task',status.parent.name],capture_output=True,text=True,encoding='utf-8',timeout=60)
            result['stops'].append({'task':status.parent.name,'exit_code':run.returncode,'stdout':run.stdout,'stderr':run.stderr})
            assert run.returncode == 0
archive = HERE / 'shell-fixture-cleanup-failure.zip'
with zipfile.ZipFile(archive, 'x', zipfile.ZIP_DEFLATED) as bundle:
    for path in paths:
        for child in path.rglob('*'):
            if child.is_file():
                bundle.write(child, child.relative_to(parent).as_posix())
with zipfile.ZipFile(archive) as bundle:
    assert bundle.testzip() is None
    result['archived_files'] = len(bundle.namelist())
for path in paths:
    resolved = path.resolve()
    assert resolved.is_relative_to(parent) and resolved != parent
    shutil.rmtree(resolved)
result['status'] = 'PASS'
(HERE/'shell-cleanup.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
