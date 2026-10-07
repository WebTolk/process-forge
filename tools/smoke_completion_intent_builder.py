from __future__ import annotations
import argparse, ast, copy, json, sys, tempfile, types
from pathlib import Path
from types import SimpleNamespace
ROOT = next(p for p in Path(__file__).resolve().parents if (p/'src/processforge_core').is_dir())
sys.path.insert(0,str(ROOT/'src'))
from processforge_core import process_execution as module
def retained(path):
    ns=dict(vars(module));ns['__name__']='processforge_core._retained_baseline'
    old=types.ModuleType(ns['__name__']);old.__dict__.update(ns);sys.modules[old.__name__]=old
    tree=ast.parse(path.read_text(encoding='utf-8-sig'))
    cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='ProcessExecutionService')
    exec('from __future__ import annotations\n'+ast.unparse(cls),old.__dict__)
    return old.ProcessExecutionService
def fixture(cls,root,**dependencies):
    svc=cls(root,None,SimpleNamespace())
    for key,value in dependencies.items():object.__setattr__(svc,key,value)
    return svc

def documents(events):
    pin={'process_id':'p','process_version':'1','process_fingerprint':'fp','snapshot_id':'s','snapshot_checksum':'hash','definition':{'unknown':True}}
    run={'id':'r','title':'Title','process':'p','status':'in_progress','tasks':[{'id':'a','status':'open','unknown':{'keep':True}},None,{'id':'other','status':'open'}],'process_execution':pin,'events':copy.deepcopy(events),'unknown':{'keep':True}}
    assignment={'id':'a','run_id':'r','stage':'finish','status':'open','unknown':{'keep':True}}
    return run,assignment
def make(cls,root,log,custom=False,failure=None):
    error=OSError('required-'+str(failure))
    def record(name,*values):
        log.append([name,*values])
        if name==failure:raise error
    def evidence(assignment):
        assert assignment['status']=='done';record('evidence');return [{'path':'z.md'},{'path':'a.md'},{'path':'z.md'},None,{}]
    def status(run,assignment_id,value):
        record('status',assignment_id,value)
        for item in run['tasks']:
            if isinstance(item,dict) and str(item.get('id') or '')==assignment_id:item['status']=value
    def run_path(run_id):record('run_path',run_id);return root/'.pf/runs'/run_id/'run.yaml'
    def assignment_path(aid):record('assignment_path',aid);return root/'.pf/assignments'/(aid+'.yaml')
    def flow():record('flow');return root/'.pf'
    def summary(run,assignment):record('summary');return 'injected summary\n'
    def rel(path,base):record('rel',path.relative_to(base).as_posix());return path.relative_to(base).as_posix()
    def project_id(base):record('project_id');return 'example'
    def intent_path(rid):record('intent_path',rid);return root/'.pf/runs'/rid/'completion-intent.yaml'
    def task_index(base,run):record('task_index');return 'injected index\n'
    core=SimpleNamespace(rel=rel,project_id=project_id)
    if custom:core.render_task_index=task_index
    svc=fixture(cls,root,core=core,_accumulated_evidence=evidence,_set_run_task_status=status,_run_path=run_path,_assignment_path=assignment_path,_flow_root=flow,_render_summary=summary,_completion_intent_path=intent_path)
    return svc,error
def suite(cls,root):
    rows=[]
    for events in [{}, {'emitted':['task.completed','custom']},{'emitted':'malformed'},[]]:
        for notes in ['', 'provided']:
            for custom in [False,True]:
                run,assignment=documents(events);log=[];svc,error=make(cls,root,log,custom)
                original=copy.deepcopy((run,assignment))
                result=svc._build_completion_intent(run,assignment,{'unknown':True},outcome='completed',notes=notes,completed_at='fixed-time')
                assert (run,assignment)==original
                final=result['final'];assert final['run']['status']=='completed' and final['assignment']['status']=='done'
                assert final['run'] is not run and final['assignment'] is not assignment
                assert final['run']['unknown'] is not run['unknown'] and final['assignment']['unknown'] is not assignment['unknown']
                assert final['assignment']['result']['artifacts']==['a.md','z.md']
                assert final['assignment']['result']['summary']==(notes or 'Completed declarative process with outcome completed.')
                assert final['run']['tasks'][0]['status']=='done' and final['run']['tasks'][2]['status']=='open'
                assert len(final['events'])==6 and len({x['event_id'] for x in final['events']})==6
                assert all(x['stage_id']=='finish' and x['outcome']=='completed' for x in final['events'])
                assert result['created_at']==result['completed_at']=='fixed-time'
                assert result['fingerprint']==module.canonical_fingerprint({k:v for k,v in result.items() if k!='fingerprint'})
                again=svc._build_completion_intent(run,assignment,{},outcome='completed',notes=notes,completed_at='fixed-time')
                assert result==again
                rows.append({'events':events,'notes':notes,'custom':custom,'intent':result,'calls':log[:len(log)//2]})
    for failure in ['evidence','status','summary','task_index','project_id']:
        run,assignment=documents({});log=[];svc,error=make(cls,root,log,True,failure)
        try:svc._build_completion_intent(run,assignment,{},outcome='done',notes='',completed_at='t')
        except OSError as actual:assert actual is error
        else:raise AssertionError('builder failure hidden')
        assert log[-1][0]==failure
        rows.append({'failure':failure,'calls':log})
    class LazyCore:
        @property
        def render_task_index(self):raise AssertionError('before run id')
        @property
        def project_id(self):raise AssertionError('before run id')
    svc=fixture(cls,root,core=LazyCore())
    try:svc._build_completion_intent({}, {}, {},outcome='',notes='',completed_at='')
    except KeyError as actual:assert actual.args==('id',)
    else:raise AssertionError('required id accepted')
    rows.append({'identity_before_capabilities':True})
    return rows
def direct(root):
    try:from processforge_core.composition import build_completion_intent_builder
    except ImportError:return
    service=build_completion_intent_builder(
        project_root=root,accumulated_evidence=lambda assignment:[],set_task_status=lambda run,aid,status:run['tasks'][0].update(status=status),
        run_path=lambda rid:root/'.pf/runs'/rid/'run.yaml',assignment_path=lambda aid:root/'.pf/assignments'/(aid+'.yaml'),flow_root=lambda:root/'.pf',
        summary=lambda run,assignment:'summary',has_task_index=lambda:False,task_index=lambda *a:(_ for _ in ()).throw(AssertionError('unused')),
        rel=lambda path,base:path.relative_to(base).as_posix(),intent_path=lambda rid:root/'.pf/runs'/rid/'completion-intent.yaml',project_id=lambda root:'example',fingerprint=lambda value:'injected',
    )
    run,assignment=documents({})
    result=service.build(run,assignment,{},outcome='done',notes='',completed_at='fixed')
    assert result['fingerprint']=='injected' and result['final']['assignment']['result']['artifacts']==[]
    assert not hasattr(service,'core')

def main():
    p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path);p.add_argument('--scratch-root',type=Path);a=p.parse_args()
    if a.scratch_root:a.scratch_root.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=a.scratch_root) as tmp:
        root=Path(tmp)
        current=suite(module.ProcessExecutionService,root)
        if a.baseline:assert current==suite(retained(a.baseline),root)
        direct(root)
        print(json.dumps({'status':'pass','cases':len(current),'results':current},sort_keys=True))
if __name__=='__main__':main()
