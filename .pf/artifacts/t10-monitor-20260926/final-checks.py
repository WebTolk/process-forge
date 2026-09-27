import hashlib,json,re,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
RUN='garage-t10-pf-vision-follow-up-implement-the-first-local-read-only-termi'
TASK='t10-pf-vision-follow-up-implement-the-first-local-read-only-terminal-mon'
out=HERE/'final-checks.json';assert not out.exists()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
task=yaml.safe_load((ROOT/'.pf/assignments'/f'{TASK}.yaml').read_text(encoding='utf-8'))
run=yaml.safe_load((ROOT/'.pf/runs'/RUN/'run.yaml').read_text(encoding='utf-8'))
assert task['status']=='done' and run['status']=='completed'
stages=['orchestration','intake-scope','investigation','domain-modeling','architecture-plan','implementation','code-assurance','release-delivery','evolve']
assert [s['stage_id'] for s in task['stage_history']]==stages
evidence={};count=0
for stage in task['stage_history']:
 assert stage['status']=='completed' and stage['outcome']=='completed' and stage['notes'].strip()
 for item in stage['evidence']:
  if item.get('path') and item.get('sha256'):
   actual=sha(ROOT/item['path']);assert 'sha256:'+actual==item['sha256'],item
   evidence[item['path']]=actual;count+=1
capsule=ROOT/task['process_execution']['assignment_capsule']
assert sha(capsule)=='6fb471b0e5f7ec47533c9acc17a18ef1cd262dd6ccb3cb79dd4044ebd0fe2cf4'
quality=json.loads((HERE/'assurance-results.json').read_text())
assert all(sha(ROOT/p)==h for p,h in quality['source_hashes'].items())
baseline=json.loads((HERE/'baseline.json').read_text())['files']
allowed=set(quality['source_hashes'])
assert all((ROOT/p).is_file() and sha(ROOT/p)==h for p,h in baseline.items() if p not in allowed)
links=0
for p in [*HERE.glob('*.md'),ROOT/'docs/concepts/runtime-monitor.md',ROOT/'docs/ru/concepts/runtime-monitor.md']:
 body=p.read_text(encoding='utf-8');assert '\ufffd' not in body
 for link in re.findall(r'\]\(([^)]+)\)',body):
  if not link.startswith(('http:','https:','#')):
   assert (p.parent/link.split('#')[0]).resolve().exists(),(p,link);links+=1
cmd=[sys.executable,'-B','D:/.agents/processforge/bin/pf.py','run-doctor','--project-root',str(ROOT),'--run',RUN]
d=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',timeout=120)
result={'recorded_at':datetime.now(timezone.utc).isoformat(),'run':RUN,'run_status':run['status'],'assignment_status':task['status'],'completed_stages':stages,'evidence_records':count,'evidence_hashes':evidence,'capsule_sha256':sha(capsule),'source_hashes':quality['source_hashes'],'baseline_files':len(baseline),'links_checked':links,'doctor':{'command':cmd,'exit_code':d.returncode,'stdout':d.stdout,'stderr':d.stderr},'source_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'doctor_passes':sum(s.startswith('PASS:') for s in d.stdout.splitlines()),'status':'PASS' if d.returncode==0 else 'FAIL'}
out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
assert d.returncode==0,(d.stdout,d.stderr)
print(json.dumps({k:result[k] for k in ['status','doctor_passes','evidence_records','baseline_files','links_checked','source_head']}))
