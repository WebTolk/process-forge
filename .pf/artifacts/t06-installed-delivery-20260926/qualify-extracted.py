from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys
import time
import zipfile

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
EXTRACTED=ROOT/'.pf/tmp/t06-installed-delivery-20260926/extracted'
build=json.loads((HERE/'candidate-build.json').read_text())
archive=Path(build['archive'])
assert hashlib.sha256(archive.read_bytes()).hexdigest()==build['archive_sha256']
assert not EXTRACTED.exists(), 'Refuse existing extraction root'
assert EXTRACTED.resolve().is_relative_to((ROOT/'.pf/tmp').resolve())
with zipfile.ZipFile(archive) as z:
    for entry in z.infolist():
        name=PurePosixPath(entry.filename)
        assert not name.is_absolute() and '..' not in name.parts and '\\' not in entry.filename and ':' not in entry.filename
        assert (entry.external_attr >> 16) & 0o170000 != 0o120000
    assert z.testzip() is None
    z.extractall(EXTRACTED)
manifest=json.loads((EXTRACTED/'processforge-core.manifest.json').read_text())
for item in manifest['files']:
    raw=(EXTRACTED/item['relative_path']).read_bytes()
    assert len(raw)==item['size'] and hashlib.sha256(raw).hexdigest()==item['sha256'],item['relative_path']
sys.path.insert(0,str(EXTRACTED/'tools'))
import processforge as core
registry={row.label:row for row in core.release_test_commands(EXTRACTED,clean_first=False)}
names=['smoke_prepared_execution_recovery','smoke_prepared_execution_context',
       'smoke_work_resource_binding','smoke_work_capsule_contract_parity',
       'smoke_provider_adapter_admission','smoke_diagnostics_process_invariance',
       'smoke_core_update_manifest','smoke_core_update_missing_owned','smoke_core_update_migration_sources',
       'smoke_classifier_distribution_parity','smoke_mcp_jsonrpc_validation','smoke_mcp_missing_session_diagnostics',
       'smoke_project_init_local_search_mcp','smoke_garage_cross_project_security',
       'smoke_docs_current_code_contract','smoke_docs_mcp_host_owned_stdio','smoke_docs_agent_no_manual_infra',
       'smoke_docs_codex_hooks_optional','smoke_runtime_driver_registry','smoke_worker_workspace_access',
       'smoke_codex_exec_worker','smoke_codex_worker_governance']
results={'started_at':datetime.now(timezone.utc).isoformat(),'extracted_root':str(EXTRACTED),
         'archive_sha256':build['archive_sha256'],'payload_hashes_verified':len(manifest['files']),
         'scope':'targeted extracted feature and update checks, not full release suite','checks':[]}
def run(name):
    row=registry[name]; started=time.monotonic()
    proc=core.run_subprocess_command(row.command,cwd=EXTRACTED,timeout=row.timeout)
    return {'name':name,'argv':row.command,'timeout':row.timeout,'exit_code':124 if proc.timed_out else proc.returncode,
            'seconds':round(time.monotonic()-started,3),'stdout':proc.stdout,'stderr':proc.stderr}
with ThreadPoolExecutor(max_workers=3) as pool:
    for future in as_completed([pool.submit(run,name) for name in names]):
        row=future.result(); results['checks'].append(row)
        print(row['name'],row['exit_code'],row['seconds'],flush=True)
        (HERE/'extracted-features.json').write_text(json.dumps(results,indent=2)+'\n',encoding='utf-8')
results['finished_at']=datetime.now(timezone.utc).isoformat()
(HERE/'extracted-features.json').write_text(json.dumps(results,indent=2)+'\n',encoding='utf-8')
raise SystemExit(any(row['exit_code'] for row in results['checks']))
