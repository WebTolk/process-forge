from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
names = ['smoke_worker_run_shell', 'smoke_worker_workspace_access', 'smoke_codex_exec_worker',
         'smoke_codex_worker_governance', 'smoke_runtime_driver_registry', 'smoke_authenticated_report_content',
         'smoke_conversation_completeness', 'smoke_expected_report_containment', 'smoke_work_capsule_contract_parity',
         'smoke_work_resource_binding', 'smoke_provider_adapter_admission', 'smoke_diagnostics_process_invariance']
result = {'started_at': datetime.now(timezone.utc).isoformat(), 'checks': []}
def run(name):
    begin = time.monotonic()
    try:
        completed = subprocess.run([sys.executable, '-B', str(ROOT/'tools'/f'{name}.py')],cwd=ROOT,
                                   capture_output=True,text=True,encoding='utf-8',timeout=360)
        return {'name':name,'exit_code':completed.returncode,'stdout':completed.stdout,'stderr':completed.stderr,'seconds':round(time.monotonic()-begin,3)}
    except subprocess.TimeoutExpired as exc:
        return {'name':name,'exit_code':124,'stderr':str(exc),'seconds':round(time.monotonic()-begin,3)}
with ThreadPoolExecutor(max_workers=3) as pool:
    for future in as_completed([pool.submit(run,name) for name in names]):
        row = future.result()
        result['checks'].append(row)
        print(row['name'],row['exit_code'],flush=True)
        (HERE/'assurance-initial.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
result['finished_at'] = datetime.now(timezone.utc).isoformat()
(HERE/'assurance-initial.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
raise SystemExit(any(row['exit_code'] for row in result['checks']))
