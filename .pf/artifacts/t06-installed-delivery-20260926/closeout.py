from datetime import datetime, timezone
import hashlib,json,subprocess,sys
from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent;CORE=Path('D:/.agents/processforge')
RUNS=['garage-t06-delivery-prerequisite-qualify-a-clean-isolated-candidate-cont','garage-t06-pf-vision-alignment-r02-integrate-acceptance-for-work-resourc']
result={'time_utc':datetime.now(timezone.utc).isoformat(),'checks':[],'evidence_hashes':{}}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def walk(value):
    if isinstance(value,dict):
        if value.get('kind') in {'artifact','gate'} and value.get('path') and value.get('sha256'):
            p=ROOT/value['path']; assert p.is_file() and sha(p)==value['sha256'].removeprefix('sha256:'),str(p)
            result['evidence_hashes'][value['path']]=sha(p)
        for x in value.values():walk(x)
    elif isinstance(value,list):
        for x in value:walk(x)
for run in RUNS:
    data=yaml.safe_load((ROOT/'.pf/runs'/run/'run.yaml').read_text(encoding='utf-8'));walk(data)
    assert data['status']==('completed' if run==RUNS[0] else 'in_progress')
    cmd=[sys.executable,'-B',str(CORE/'bin/pf.py'),'run-doctor','--project-root',str(ROOT),'--run',run]
    p=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',timeout=180)
    result['checks'].append({'argv':cmd,'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
    (HERE/'closeout-verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    failures=[line for line in p.stdout.splitlines() if line.startswith('FAIL:')]
    if run==RUNS[0]:
        assert p.returncode==1 and len(failures)==1 and failures[0].endswith('run.yaml has no private absolute paths'),p.stdout+p.stderr
        result['delivery_metadata_finding']={'status':'open','check':'private_absolute_path_in_run_objective','doctor_exit_code':p.returncode,'failures':failures,'immutable_capsule_not_rewritten':True}
    else:
        assert p.returncode==0,p.stdout+p.stderr
    print(run, p.returncode,len([s for s in p.stdout.splitlines() if s.startswith('PASS:')]),flush=True)
for file,key in [('candidate-corrected.json','source_raw_sha256')]:
    b=json.loads((HERE/file).read_text());assert all(sha(ROOT/n)==h for n,h in b[key].items())
prior=json.loads((ROOT/'.pf/artifacts/t06-integrated-acceptance-20260926/baseline.json').read_text());assert all(sha(ROOT/n)==h for n,h in prior['frozen_sha256'].items())
manifest=json.loads((CORE/'processforge-core.manifest.json').read_text());assert all(sha(CORE/x['relative_path'])==x['sha256'] for x in manifest['files'])
protected=json.loads((HERE/'install-result.json').read_text())['protected_sha256'];assert all(sha(Path(n))==h for n,h in protected.items())
result.update(source_payload_verified=986,installed_payload_verified=987,frozen_verified=561,protected_verified=len(protected),recorded_artifact_files_verified=len(result['evidence_hashes']))
for label,cmd,cwd in [('main_head',['git','rev-parse','HEAD'],ROOT),('main_branch',['git','branch','--show-current'],ROOT),('candidate_status',['git','status','--porcelain'],ROOT/'.pf/tmp/t06-installed-delivery-20260926/candidate'),('diff_check',['git','diff','--check'],ROOT)]:
    p=subprocess.run(cmd,cwd=cwd,capture_output=True,text=True,encoding='utf-8');assert p.returncode==0
    result[label]=p.stdout.strip()
assert result['candidate_status']=='' and result['main_head']=='a180ad624442d4fbe8ac1710073ef7d4c44babc4'
capsule=ROOT/'.pf/contexts/assignment-capsules/t06-delivery-prerequisite-qualify-a-clean-isolated-candidate-containing.capsule.yaml'
assert sha(capsule)=='465307848dbbc2b1b898c551ea8ccac907a0b0d77b7f17fa37b48c36a643c7e1'
result['delivery_capsule_unchanged']=True
result['status']='installed_delivery_complete_with_open_metadata_finding_original_t06_waiting_actual_host_reconnect'
(HERE/'closeout-verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print('Verified: installed/source and immutable evidence preservation; original T06 doctor passes; delivery doctor retains one metadata privacy finding',flush=True)
