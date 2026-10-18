import json,subprocess,sys
from pathlib import Path
out=Path('.pf/artifacts/publish-f06-f08-20260910');run='garage-publish-validated-fixes-to-dev-remediate-python-core-audit-f06-f0'
cli=[sys.executable,'tools/processforge.py']
def call(args,name):
 p=subprocess.run(cli+args,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=240)
 (out/name).write_text(p.stdout+p.stderr,encoding='utf-8');assert p.returncode==0,(name,p.stdout,p.stderr)
 return p.stdout
stages=[('task-execution-loop',[('task-iteration-log','iteration-record.md')],'task-results-recorded'),('task-result-fixation',[('task-result','integration-report.md')],'all-blocking-tasks-completed'),('run-review',[('run-review','review-addendum.md')],'run-doctor-passed'),('run-summary',[('run-summary','summary.md'),('run-handoff','../../handoffs/publish-f06-f08-20260910.md')],'run-summary-created')]
for stage,arts,gate in stages:
 state=json.loads(call(['work-state','--project-root','.','--run',run,'--json'],f'{stage}-before.json'))
 assert state['stage']['id']==stage,state
 if stage=='run-review':
  call(['run-doctor','--project-root','.','--run',run],'carrier-preclose-doctor.txt')
  call(['task-doctor','--project-root','.','--task','publish-validated-fixes-to-dev-remediate-python-core-audit-f06-f08-using'],'carrier-task-doctor.txt')
 evidence=[{'kind':'artifact','artifact_id':aid,'status':'ready','path':(out/path).resolve().relative_to(Path.cwd()).as_posix()} for aid,path in arts]
 evidence.append({'kind':'gate','gate_id':gate,'status':'passed','summary':'Accepted source/installed tests, two completed shell assignments, independent review and preserved final-state evidence. PF doctors pass.'})
 path=out/f'{stage}-evidence.json';path.write_text(json.dumps(evidence,indent=2))
 result=json.loads(call(['work-transition','--project-root','.','--run',run,'--outcome','completed','--evidence-file',str(path),'--notes','Accepted publication/remediation and installed verification; remaining audit/release boundaries recorded in handoff.','--json'],f'{stage}-transition.json'))
 print(stage,result['action'],flush=True)
 assert result['action'] in ('stage_transitioned','run_completed'),result
assert result['action']=='run_completed'
call(['run-doctor','--project-root','.','--run',run],'final-carrier-doctor.txt')
import yaml
runs={r:yaml.safe_load(Path(f'.pf/runs/{r}/run.yaml').read_text())['status'] for r in [run,'core-f06-f08-shell-20260910']}
tasks={t:yaml.safe_load(Path(f'.pf/assignments/{t}.yaml').read_text())['status'] for t in ['f0608-cli','f0608-review','publish-validated-fixes-to-dev-remediate-python-core-audit-f06-f08-using']}
assert all(v=='completed' for v in runs.values()) and all(v=='done' for v in tasks.values())
(out/'closeout.json').write_text(json.dumps({'runs':runs,'assignments':tasks,'carrier_action':result['action'],'implementation_worker_execution':'cancelled; primary takeover accepted','review_worker_execution':'completed exit 0, collected','final_state':'final-state.json'},indent=2))
print('CLOSEOUT PASS',flush=True)
