from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib, json, subprocess, sys, time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
CORE=Path('D:/.agents/processforge');WP=Path('D:/.agents/processforge-workplace')
install=json.loads((HERE/'install-result.json').read_text())
assert install['installed_payload_hashes_verified']==987 and install['backup_hashes_verified']==37
assert any(x['label']=='runtime-after-doctor' and x['exit_code']==0 for x in install['commands'])
result={'started_at':datetime.now(timezone.utc).isoformat(),'checks':[],
 'prior_runner_correction':'Installation and Runtime restart completed. The extra doctor-workplace invocation used --workplace instead of required --root; updater automatic doctor already passed. Continue read-only verification, do not repeat apply.'}
prior_verification=json.loads((HERE/'installed-inventory-observation.json').read_text())
result['checks']=prior_verification['checks'][:4]
result['installed_inventory_boundary']='The source-wide checksum scanner includes 10 preserved unowned Joomla process files and reports actual-only entries. Raw observation retained separately. Installed integrity uses the Core ownership manifest; do not delete unowned files or rewrite the installed checksum inventory.'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(): (HERE/'installed-verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
def run(name,args,timeout=180):
    start=time.monotonic();p=subprocess.run(list(map(str,args)),cwd=ROOT,capture_output=True,text=True,encoding='utf-8',timeout=timeout)
    return {'name':name,'argv':list(map(str,args)),'exit_code':p.returncode,'seconds':round(time.monotonic()-start,3),'stdout':p.stdout,'stderr':p.stderr}
def record(row):
    result['checks'].append(row);save();print(row['name'],row['exit_code'],row['seconds'],flush=True)
    assert row['exit_code']==0,row['stdout'][-2000:]+row['stderr'][-2000:]
def cli(*args):return [sys.executable,'-B',CORE/'bin/pf.py',*args]
for name,args in [
 ('workplace-doctor',cli('doctor-workplace','--root',WP)),
 ('core-update-status',cli('core-update','status','--core-root',CORE)),
 ('context-freshness',cli('project-context-check','--project-root',ROOT,'--workplace',WP,'--json','--strict')),
 ('runtime-doctor',cli('runtime','doctor','--workplace',WP))]:
    if not any(x['name']==name and x['exit_code']==0 for x in result['checks']):record(run(name,args))
sys.path.insert(0,str(CORE/'tools'));import processforge
registry={x.label:x for x in processforge.release_test_commands(CORE,clean_first=False)}
def smoke(name):
    row=registry.get(name)
    return run(name,row.command if row else [sys.executable,'-B',CORE/'tools'/(name+'.py')],row.timeout if row else 120)
# Performance measurements run without concurrent smoke load.
record(smoke('smoke_diagnostics'))
names=['smoke_prepared_execution_recovery','smoke_work_resource_binding','smoke_work_capsule_contract_parity',
       'smoke_diagnostics_process_invariance','smoke_mcp_jsonrpc_validation','smoke_provider_adapter_admission','smoke_runtime_ledger_hooks_mcp']
with ThreadPoolExecutor(max_workers=3) as pool:
    for future in as_completed([pool.submit(smoke,n) for n in names]):record(future.result())
manifest=json.loads((CORE/'processforge-core.manifest.json').read_text())
assert all(sha(CORE/x['relative_path'])==x['sha256'] for x in manifest['files'])
result['installed_payload_hashes_verified']=len(manifest['files'])
assert all(sha(Path(p))==h for p,h in install['protected_sha256'].items())
result['protected_config_snapshot_capsule_count']=len(install['protected_sha256'])
prior=json.loads((ROOT/'.pf/artifacts/t06-integrated-acceptance-20260926/baseline.json').read_text())
assert all(sha(ROOT/p)==h for p,h in prior['frozen_sha256'].items());result['frozen_unchanged_count']=len(prior['frozen_sha256'])
build=json.loads((HERE/'candidate-corrected.json').read_text())
assert all(sha(ROOT/p)==h for p,h in build['source_raw_sha256'].items());result['source_unchanged_count']=len(build['source_raw_sha256'])
result['finished_at']=datetime.now(timezone.utc).isoformat();save();print('PASS: installed tests and preserved state',flush=True)
