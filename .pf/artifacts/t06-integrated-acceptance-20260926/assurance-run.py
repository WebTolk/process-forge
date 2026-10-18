from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'tools'))
import processforge as core

parallel = ['smoke_prepared_execution_context', 'smoke_worker_run_shell',
            'smoke_worker_workspace_access', 'smoke_codex_exec_worker',
            'smoke_codex_worker_governance', 'smoke_runtime_driver_registry',
            'smoke_authenticated_report_content', 'smoke_conversation_completeness',
            'smoke_expected_report_containment', 'smoke_work_capsule_contract_parity',
            'smoke_work_resource_binding', 'smoke_provider_adapter_admission',
            'smoke_central_event_ingress', 'smoke_mcp_jsonrpc_validation',
            'smoke_session_identity_roundtrip']
serial = ['smoke_diagnostics_process_invariance', 'smoke_diagnostics',
          'smoke_runtime_ledger_hooks_mcp']
registry = {item.label: item for item in core.release_test_commands(ROOT, clean_first=False)}
# This older integration proof is supplemental, not in the release registry.
registry['smoke_runtime_ledger_hooks_mcp'] = core.ReleaseCommand(
    'smoke_runtime_ledger_hooks_mcp',
    [sys.executable, '-B', str(ROOT / 'tools/smoke_runtime_ledger_hooks_mcp.py')], 240)
assert all(name in registry for name in parallel + serial), set(parallel + serial) - registry.keys()
assert registry['smoke_prepared_execution_recovery'].timeout == 240
results = {'started_at': datetime.now(timezone.utc).isoformat(),
           'kind': 'source_registered_integration_subset', 'checks': []}

def run(name):
    spec = registry[name]
    start = time.monotonic()
    proc = core.run_subprocess_command(spec.command, cwd=ROOT, timeout=spec.timeout)
    return {'name': name, 'command': spec.command, 'timeout': spec.timeout,
            'exit_code': 124 if proc.timed_out else proc.returncode,
            'seconds': round(time.monotonic() - start, 3),
            'stdout': proc.stdout, 'stderr': proc.stderr}

def record(row):
    results['checks'].append(row)
    (HERE / 'assurance-results.json').write_text(json.dumps(results, indent=2) + '\n', encoding='utf-8')
    print(row['name'], row['exit_code'], row['seconds'], flush=True)

with ThreadPoolExecutor(max_workers=3) as pool:
    for future in as_completed([pool.submit(run, name) for name in parallel]):
        record(future.result())
for name in serial:
    record(run(name))
results['finished_at'] = datetime.now(timezone.utc).isoformat()
(HERE / 'assurance-results.json').write_text(json.dumps(results, indent=2) + '\n', encoding='utf-8')
raise SystemExit(any(row['exit_code'] for row in results['checks']))
