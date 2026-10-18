from concurrent.futures import ThreadPoolExecutor, as_completed
import ast, fnmatch, importlib.util
from work import *

assert state('assurance-start')['stage']['id']=='code-assurance'
scripts=['smoke_egress_engine','smoke_egress_work','smoke_egress_transport',
         'smoke_work_capsule_contract_parity','smoke_work_resource_binding',
         'smoke_prepared_execution_context','smoke_prepared_execution_recovery',
         'smoke_work_start_no_stage_guessing','smoke_runtime_metrics','smoke_server_operator',
         'smoke_process_event_concurrency']
jobs=[(s,[sys.executable,'-B',ROOT/'tools'/(s+'.py'),*(['--json'] if s.startswith('smoke_egress') else [])]) for s in scripts]
jobs += [(label,[sys.executable,'-B',ROOT/'tools'/script,*args]) for label,script,args in [
    ('schemas','validate-process-forge-schemas.py',[]),('public-cleanliness','validate-public-cleanliness.py',[]),
    ('checksums','validate-process-forge-checksums.py',['--check'])]]
passed,failed=[],[]
with ThreadPoolExecutor(max_workers=3) as pool:
    futures={pool.submit(command,'source-'+name,args,timeout=420):name for name,args in jobs}
    for future in as_completed(futures):
        name=futures[future]
        try:
            future.result();passed.append(name)
        except Exception as error:
            failed.append({'check':name,'error':str(error)[-500:]})
save('assurance-check-results.json',{'passed':sorted(passed),'failed':failed})
assert not failed,failed
accepted=json.loads((HERE/'implementation-files.json').read_text(encoding='utf-8'))
assert all(sha(ROOT/n)==h for n,h in accepted['sha256'].items()),'source changed after implementation evidence'
save('assurance-results.json',{'changed_files':accepted['files'],'source_sha256':accepted['sha256'],'passed':sorted(passed),'failed':[]})
print('PASS',len(passed),'source assurance commands',flush=True)
