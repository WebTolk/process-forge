import json
from pathlib import Path
import subprocess
import sys
import time
from datetime import datetime, timezone

root = Path(__file__).resolve().parents[3]
names = ['smoke_project_resource_narrowing_search', 'smoke_resource_indexing_policy_acceptance',
         'smoke_workplace_search_index', 'smoke_multi_process_work_capsule',
         'smoke_work_transition_snapshot_pinned_process', 'smoke_garage_no_hooks_sessionless',
         'smoke_mcp_jsonrpc_validation', 'smoke_mcp_missing_session_diagnostics',
         'smoke_project_init_local_search_mcp']
report = {'started_at': datetime.now(timezone.utc).isoformat(), 'checks': []}
for name in names:
    started = time.perf_counter()
    result = subprocess.run([sys.executable, '-B', str(root / 'tools' / (name + '.py'))], cwd=root,
                            capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=240)
    report['checks'].append({'name': name, 'exit_code': result.returncode, 'stdout': result.stdout,
                            'stderr': result.stderr, 'seconds': round(time.perf_counter() - started, 3)})
    Path(__file__).with_name('assurance-results.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(name, result.returncode, flush=True)
report['finished_at'] = datetime.now(timezone.utc).isoformat()
Path(__file__).with_name('assurance-results.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
raise SystemExit(0 if all(row['exit_code'] == 0 for row in report['checks']) else 1)
