from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
names = ['smoke_capsule_pins_context_snapshot', 'smoke_parameter_assignment_capsule',
         'smoke_project_overrides_capsule_summary', 'smoke_specialization_capsule_activation',
         'smoke_worker_workspace_access', 'smoke_work_transition_updates_assignment_stage',
         'smoke_work_transition_snapshot_pinned_process', 'smoke_multi_process_work_capsule',
         'smoke_work_resource_binding', 'smoke_worker_run_shell', 'smoke_codex_worker_governance']
result = {'started_at': datetime.now(timezone.utc).isoformat(), 'checks': []}
def execute(name):
    start = time.monotonic()
    try:
        value = subprocess.run([sys.executable, '-B', str(ROOT / 'tools' / (name + '.py'))], cwd=ROOT, capture_output=True, text=True, encoding='utf-8', timeout=300)
        return {'name': name, 'exit_code': value.returncode, 'stdout': value.stdout, 'stderr': value.stderr, 'seconds': round(time.monotonic() - start, 3)}
    except subprocess.TimeoutExpired as exc:
        return {'name': name, 'exit_code': 124, 'error': str(exc), 'seconds': round(time.monotonic() - start, 3)}
with ThreadPoolExecutor(max_workers=3) as pool:
    for future in as_completed([pool.submit(execute, name) for name in names]):
        check = future.result()
        result['checks'].append(check)
        print(check['name'], check['exit_code'], check['seconds'], flush=True)
        (HERE / 'assurance-results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
result['finished_at'] = datetime.now(timezone.utc).isoformat()
(HERE / 'assurance-results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
raise SystemExit(1 if any(item['exit_code'] for item in result['checks']) else 0)
