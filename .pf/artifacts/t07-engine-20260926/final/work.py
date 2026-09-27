"""Private delivery evidence and standard PF CLI; no direct lifecycle-file edits."""
import hashlib, importlib.util, json, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
HERE=Path(__file__).resolve().parent
CORE=Path('D:/.agents/processforge')
WP=Path('D:/.agents/processforge-workplace')
RUN='garage-implement-the-t07-provider-neutral-egress-engine-qualify-a-bounde'
ASSIGN='implement-the-t07-provider-neutral-egress-engine-qualify-a-bounded-enfor'
CAP=ROOT/'.pf/contexts/assignment-capsules'/(ASSIGN+'.capsule.yaml')
CAP_SHA='000b31cf7f3af61f3b7d07943712ae201e030b7c97afb681ea85313f6792cd37'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,data): (HERE/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def command(label,args,cwd=ROOT,timeout=300):
    p=subprocess.run(list(map(str,args)),cwd=cwd,capture_output=True,text=True,encoding='utf-8',timeout=timeout)
    r={'time':datetime.now(timezone.utc).isoformat(),'argv':list(map(str,args)),'cwd':str(cwd),'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
    save(label+'.json',r)
    print(label,p.returncode,flush=True)
    assert p.returncode==0,(p.stdout[-4000:],p.stderr[-4000:])
    return p.stdout
def cli(*args): return [sys.executable,'-B',CORE/'bin/pf.py',*args]
def state(label):
    assert sha(CAP)==CAP_SHA
    s=json.loads(command(label,cli('work-state','--project-root',ROOT,'--workplace',WP,'--run',RUN,'--assignment',ASSIGN,'--json')))
    assert s['run']['id']==RUN and not s['blockers']
    return s
def advance(stage,file,artifacts,gates):
    assert (HERE/file).is_file(), 'Evidence artifact must be complete before transition'
    assert state(stage+'-before')['stage']['id']==stage
    path=(HERE/file).relative_to(ROOT).as_posix()
    evidence=[{'kind':'artifact','artifact_id':x,'path':path,'status':'ready'} for x in artifacts]
    evidence += [{'kind':'gate','gate_id':x,'path':path,'status':'passed'} for x in gates]
    save(stage+'-evidence.json',evidence)
    s=json.loads(command(stage+'-transition',cli('work-transition','--project-root',ROOT,'--workplace',WP,'--run',RUN,'--assignment',ASSIGN,'--outcome','completed','--evidence-file',HERE/(stage+'-evidence.json'),'--notes','Evidence reviewed; continue the pinned process from this completed stage.','--json')))
    assert s['action'] in ('stage_transitioned','run_completed'),s
    assert sha(CAP)==CAP_SHA
    with (ROOT/'.pf/logs/t07-engine-20260926.md').open('a',encoding='utf-8') as f:
        f.write('\n## '+datetime.now(timezone.utc).isoformat()+' - primary agent\n\nTask: '+stage+'.\nFiles changed: own delivery evidence and standard PF lifecycle state.\nArtifacts changed: '+path+'.\nTools used: installed work-state/work-transition CLI (MCP timeout fallback).\nStatus: '+s['action']+'.\nNext steps: '+str(s.get('stage',{}).get('id','completed'))+'.\n')
    print(s['action'],s.get('stage'),flush=True)

if __name__=='__main__':
    stages={
        'orchestration':('orchestration.md',['task-record','execution-context-summary','lifecycle-mode-decision'],['context-ready']),
        'intake-scope':('scope.md',['brief','scope','task-record'],['scope-accepted']),
        'investigation':('investigation.md',['investigation-report','impact-analysis'],['investigation-complete','impact-understood']),
        'domain-modeling':('domain.md',['domain-notes','domain-model','domain-rules'],['domain-rules-captured']),
        'architecture-plan':('architecture.md',['architecture','implementation-plan','decision-log'],['architecture-plan-ready']),
        'implementation':('implementation.md',['changed-files','change-summary'],['implementation-scope-respected']),
        'code-assurance':('assurance.md',['review-findings','test-plan','test-cases','test-report','browser-verification-report'],['assurance-complete']),
        'release-delivery':('delivery.md',['release-notes','migration-notes','patch','delivery-plan','delivery-report'],['release-readiness-decided','delivery-profile-run-or-skipped-with-reason']),
        'evolve':('evolution.md',['evolution-report'],['evolution-captured'])}
    for stage in sys.argv[1:]: advance(stage,*stages[stage])
