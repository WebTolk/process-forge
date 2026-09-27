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
    ['.pf/artifacts/t02-work-resources-20260925/verify-delivery.py'],
    ['.pf/artifacts/t02-work-resources-20260925/verify-main-legacy.py'],
    ['tools/validate-public-cleanliness.py'],
    ['tools/validate-process-forge-checksums.py', '--write'],
    ['tools/validate-process-forge-checksums.py', '--check'],
]
for command in commands:
    run = subprocess.run([sys.executable, '-B', *command], cwd=ROOT, capture_output=True, text=True, encoding='utf-8', timeout=180)
    result['checks'].append({'command': command, 'exit_code': run.returncode, 'stdout': run.stdout, 'stderr': run.stderr})
    print(command[0], run.returncode, flush=True)
    (HERE / 'final-checks.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if run.returncode:
        raise SystemExit(run.returncode)
paths = ['src/processforge_core/work_resources.py', 'src/processforge_core/work_resource_material.py',
         'src/processforge_core/local_resource_search.py', 'src/processforge_core/process_execution.py',
         'src/processforge_core/garage.py', 'tools/processforge.py', 'tools/pf_runtime/mcp_server.py',
         'tools/smoke_work_resource_binding.py', 'schemas/resource-bindings.schema.json',
         'schemas/context-capsule.schema.json', 'schemas/process-definition.schema.json',
         'docs/concepts/work-resources.md', 'docs/ru/concepts/work-resources.md']
result['source_sha256'] = {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in paths}
result['finished_at'] = datetime.now(timezone.utc).isoformat()
(HERE / 'final-checks.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
