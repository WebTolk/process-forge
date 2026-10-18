import json
import subprocess
import sys
from pathlib import Path
import yaml
out=Path(__file__).resolve().parent
run='garage-remediate-python-core-audit-f09-f12-updater-search-and-raw-ingres'
assignment='remediate-python-core-audit-f09-f12-updater-search-and-raw-ingress-with'
cli=[sys.executable,'tools/processforge.py']
def call(args,name):
    r=subprocess.run(cli+args,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=240)
    (out/name).write_text(r.stdout+r.stderr,encoding='utf-8')
    assert r.returncode==0,(name,r.stdout,r.stderr)
    return r.stdout
stages=[
    ('task-execution-loop',[('task-iteration-log','iteration-record.md')],'task-results-recorded'),
    ('task-result-fixation',[('task-result','integration-report.md')],'all-blocking-tasks-completed'),
    ('run-review',[('run-review','review-addendum.md')],'run-doctor-passed'),
    ('run-summary',[('run-summary','summary.md'),('run-handoff','../../handoffs/core-f09-f12-20260910.md')],'run-summary-created'),
]
for stage,arts,gate in stages:
    state=json.loads(call(['work-state','--project-root','.','--run',run,'--json'],f'{stage}-before.json'))
    assert state['stage']['id']==stage,state
    if stage=='run-review':
        call(['run-doctor','--project-root','.','--run',run],'carrier-preclose-doctor.txt')
        call(['task-doctor','--project-root','.','--task',assignment],'carrier-task-doctor.txt')
    evidence=[{'kind':'artifact','artifact_id':aid,'status':'ready','path':(out/path).resolve().relative_to(Path.cwd()).as_posix()} for aid,path in arts]
    evidence.append({'kind':'gate','gate_id':gate,'status':'passed','summary':'Source/extracted/installed acceptance and preservation verified, four shell assignments completed, independent bounded review and primary final delta accepted, PF doctors passed.'})
    path=out/f'{stage}-evidence.json';path.write_text(json.dumps(evidence,indent=2))
    result=json.loads(call(['work-transition','--project-root','.','--run',run,'--outcome','completed','--evidence-file',str(path),'--notes','F09-F12 delivered to dev and installed with acceptance evidence; remaining MCP/collection/full-release boundaries documented.','--json'],f'{stage}-transition.json'))
    print(stage,result['action'],flush=True)
    assert result['action'] in ('stage_transitioned','run_completed'),result
assert result['action']=='run_completed'
call(['run-doctor','--project-root','.','--run',run],'final-carrier-doctor.txt')
call(['run-doctor','--project-root','.','--run','core-f09-f12-shell-20260910'],'final-shell-doctor.txt')
runs={r:yaml.safe_load(Path(f'.pf/runs/{r}/run.yaml').read_text())['status'] for r in [run,'core-f09-f12-shell-20260910']}
tasks={t:yaml.safe_load(Path(f'.pf/assignments/{t}.yaml').read_text())['status'] for t in [assignment,'f09-update','f1011-search','f12-ingress','f0912-review']}
assert all(v=='completed' for v in runs.values()) and all(v=='done' for v in tasks.values())
(out/'closeout.json').write_text(json.dumps({'runs':runs,'assignments':tasks,'carrier_action':result['action'],'worker_executions':'all four completed exit 0','collection':'f09 collected; search/ingress/review cardinality rejected, explicit primary acceptance used','final_state':'final-state.json'},indent=2))
print('CLOSEOUT PASS',flush=True)
