import hashlib
import json
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
result = {'started_at': datetime.now(timezone.utc).isoformat(), 'checks': []}
commands = [
    ['.pf/artifacts/t03-unified-context-20260926/verify-delivery.py'],
    ['tools/validate-process-forge-schemas.py'],
    ['tools/validate-public-cleanliness.py'],
    ['tools/validate-process-forge-checksums.py', '--write'],
    ['tools/validate-process-forge-checksums.py', '--check'],
]
for command in commands:
    run = subprocess.run([sys.executable, '-B', *command], cwd=ROOT, capture_output=True, text=True, encoding='utf-8', timeout=180)
    result['checks'].append({'command': command, 'exit_code': run.returncode, 'stdout': run.stdout, 'stderr': run.stderr})
    print(command[0], run.returncode, flush=True)
    if run.returncode:
        (HERE/'final-checks.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
        raise SystemExit(run.returncode)
paths = ['src/processforge_core/work_context.py', 'src/processforge_core/process_execution.py', 'src/processforge_core/work_resources.py', 'tools/processforge.py', 'tools/smoke_work_capsule_contract_parity.py', 'tools/smoke_work_resource_binding.py', 'tools/smoke_worker_run_shell.py', 'tools/smoke_worker_workspace_access.py', 'schemas/execution-contract.schema.json', 'schemas/context-capsule.schema.json', 'schemas/assignment.schema.json', 'docs/concepts/work-context.md', 'docs/ru/concepts/work-context.md']
result['source_sha256'] = {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in paths}
capsule = ROOT/'.pf/contexts/assignment-capsules/t03-pf-vision-alignment-r02-implement-one-shared-normalized-complete-wor.capsule.yaml'
result['main_legacy_capsule_sha256'] = hashlib.sha256(capsule.read_bytes()).hexdigest()
assert result['main_legacy_capsule_sha256'] == '8ee0d2ac810317140423b23529603a42183f2c6be3649e8c94ee33544fdcea9a'
result['finished_at'] = datetime.now(timezone.utc).isoformat()
(HERE/'final-checks.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
print('PASS: T03 final source checks and original main capsule byte pin')
