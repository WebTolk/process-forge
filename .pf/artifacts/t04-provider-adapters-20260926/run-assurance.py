from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
names = ['smoke_central_event_ingress_kernel', 'smoke_central_event_ingress', 'smoke_central_event_replay', 'smoke_codex_lifecycle_identity', 'smoke_conversation_completeness', 'smoke_authenticated_report_content', 'smoke_expected_report_containment', 'smoke_codex_exec_worker', 'smoke_codex_worker_governance', 'smoke_project_init_codex_integration', 'smoke_runtime_ledger_hooks_mcp', 'smoke_mcp_codex_contract', 'smoke_work_capsule_contract_parity']
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
