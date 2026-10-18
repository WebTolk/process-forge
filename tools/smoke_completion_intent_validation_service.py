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

def sign(intent):
    intent['fingerprint']=module.canonical_fingerprint({k:v for k,v in intent.items() if k!='fingerprint'})
    return intent
def documents(root):
    pin={key:key+'-value' for key in ['process_id','process_version','process_fingerprint','snapshot_id','snapshot_checksum']}
    run={'id':'r','process_execution':copy.deepcopy(pin)}
    assignment={'id':'a'}
    journal=root/'.pf/runs/r/completion.yaml'
    final={
        'run':{'id':'r','status':'completed','process_execution':copy.deepcopy(pin),'tasks':[{'id':'a','status':'done','extra':True}]},
        'assignment':{'id':'a','run_id':'r','status':'done','unknown':{'keep':True}},
        'summary':{'path':'.pf/runs/r/summary.md'},'handoff':{'path':'.pf/handoffs/runs/r-handoff.md'},
        'task_index':{'path':'.pf/runs/r/task-index.md'},'projection':{'path':'.pf/artifacts/projections/process-execution-state.json'},
        'events':[{'event_type':'completed','event_id':'e','extra':True}],
    }
    intent={'kind':'pf.process.completion-intent','run_id':'r','assignment_id':'a','process_execution':pin,'journal_path':'.pf/runs/r/completion.yaml','owner':{'run_path':'.pf/runs/r/run.yaml','assignment_path':'.pf/assignments/a.yaml','project_id':'p'},'final':final,'unknown':{'keep':True}}
    return run,assignment,sign(intent),journal
def dependencies(root,log,with_project=True):
    def rel(path,base):
        log.append(['rel',path.name]);return path.relative_to(base).as_posix()
    def effective(value):log.append(['effective']);return {},'pinned'
    core=SimpleNamespace(rel=rel)
    if with_project:core.project_id=lambda path:log.append(['project_id']) or 'p'
    return {'core':core,'_effective_process':effective,'_run_path':lambda rid:root/'.pf/runs'/rid/'run.yaml','_assignment_path':lambda aid:root/'.pf/assignments'/(aid+'.yaml'),'_flow_root':lambda:root/'.pf'}
def set_path(value,path,replacement):
    node=value
    for key in path[:-1]:node=node[key]
    node[path[-1]]=replacement
def suite(cls,root):
    rows=[]
    changes=[
        ('run_id',['run_id'],'wrong','journal identity does not match selected work'),
        ('assignment_id',['assignment_id'],'wrong','journal identity does not match selected work'),
        ('final_run_id',['final','run','id'],'wrong','journal final payload identity is invalid'),
        ('final_assignment_id',['final','assignment','id'],'wrong','journal final payload identity is invalid'),
        ('final_assignment_run',['final','assignment','run_id'],'wrong','journal final payload identity is invalid'),
        ('final_malformed',['final'],None,'journal final payload identity is invalid'),
        ('run_open',['final','run','status'],'open','journal final payload is not terminal'),
        ('assignment_open',['final','assignment','status'],'open','journal final payload is not terminal'),
        ('assignment_failed',['final','assignment','status'],'failed','journal final assignment is not done'),
        ('assignment_cancelled',['final','assignment','status'],'cancelled','journal final assignment is not done'),
        ('assignment_completed',['final','assignment','status'],'completed','journal final assignment is not done'),
        ('task_open',['final','run','tasks',0,'status'],'open','journal final task status is invalid'),
        ('task_malformed',['final','run','tasks'],None,'journal final task status is invalid'),
        ('task_missing',['final','run','tasks'],[{'id':'other','status':'done'}],'journal final task status is invalid'),
        ('task_first',['final','run','tasks'],[{'id':'a','status':'open'},{'id':'a','status':'done'}],'journal final task status is invalid'),
        ('journal_path',['journal_path'],'other','journal path is not owned by the selected run'),
        ('owner_run',['owner','run_path'],'other','journal owner paths are invalid'),
        ('owner_assignment',['owner','assignment_path'],'other','journal owner paths are invalid'),
        ('owner_project',['owner','project_id'],'other','journal project owner is invalid'),
        ('owner_malformed',['owner'],None,'journal owner paths are invalid'),
        ('events_empty',['final','events'],[],'journal event metadata is invalid'),
        ('events_type',['final','events'],{},'journal event metadata is invalid'),
        ('events_bad',['final','events'],['bad'],'journal event metadata is invalid'),
        ('event_id_missing',['final','events'],[{'event_type':'completed'}],'journal event metadata is invalid'),
        ('event_type_missing',['final','events'],[{'event_id':'e'}],'journal event metadata is invalid'),
    ]
    for key in ['process_id','process_version','process_fingerprint','snapshot_id','snapshot_checksum']:
        for place,path in [('intent',['process_execution',key]),('final',['final','run','process_execution',key])]:
            changes.append((place+'_'+key,path,'changed','journal process pin mismatch: '+key))
    for key in ['summary','handoff','task_index','projection']:
        changes.append((key+'_path',['final',key,'path'],'other','journal '+key+' path is invalid'))
    for name,path,replacement,expected in [('valid',None,None,None)]+changes:
        run,assignment,intent,journal=documents(root);log=[]
        if path:set_path(intent,path,replacement);sign(intent)
        original=copy.deepcopy((run,assignment,intent))
        svc=fixture(cls,root,**dependencies(root,log))
        reason=svc._validate_completion_intent(intent,run,assignment,journal)
        assert reason==expected,(name,reason,expected)
        assert (run,assignment,intent)==original
        if name in ['journal_path','owner_run','owner_assignment','owner_malformed']:assert ['project_id'] not in log
        rows.append({'case':name,'reason':reason,'calls':log})
    for name,bad,expected in [('none',None,'journal kind is invalid'),('kind',{'kind':'bad'},'journal kind is invalid')]:
        run,assignment,intent,journal=documents(root);log=[]
        reason=fixture(cls,root,**dependencies(root,log))._validate_completion_intent(bad,run,assignment,journal)
        assert reason==expected and not log
        rows.append({'case':name,'reason':reason})
    run,assignment,intent,journal=documents(root);intent['run_id']='tampered';log=[]
    reason=fixture(cls,root,**dependencies(root,log))._validate_completion_intent(intent,run,assignment,journal)
    assert reason=='journal content fingerprint mismatch' and not log
    rows.append({'case':'fingerprint_first','reason':reason})
    for value in [object(),None]:
        run,assignment,intent,journal=documents(root)
        if value is None:intent['unknown']=intent
        else:intent['unknown']=value
        reason=fixture(cls,root,**dependencies(root,[]))._validate_completion_intent(intent,run,assignment,journal)
        assert reason=='journal content is invalid'
        rows.append({'case':'invalid_content','reason':reason})
    run,assignment,intent,journal=documents(root);log=[]
    deps=dependencies(root,log);deps['_effective_process']=lambda run:({},'legacy')
    assert fixture(cls,root,**deps)._validate_completion_intent(intent,run,assignment,journal)=='journal final process pin is invalid'
    rows.append({'case':'effective_process_override','reason':'journal final process pin is invalid'})
    run,assignment,intent,journal=documents(root);log=[]
    intent['owner']['project_id']='irrelevant';sign(intent)
    assert fixture(cls,root,**dependencies(root,log,False))._validate_completion_intent(intent,run,assignment,journal) is None
    rows.append({'case':'optional_project_id_absent','calls':log})
    class LazyCore:
        def rel(self,path,base):return path.relative_to(base).as_posix()
        @property
        def project_id(self):raise error
    error=RuntimeError('project capability unavailable')
    run,assignment,intent,journal=documents(root);deps=dependencies(root,[]);deps['core']=LazyCore()
    svc=fixture(cls,root,**deps)
    assert svc._validate_completion_intent(None,run,assignment,journal)=='journal kind is invalid'
    wrong=copy.deepcopy(intent);wrong['owner']['run_path']='other';sign(wrong)
    assert svc._validate_completion_intent(wrong,run,assignment,journal)=='journal owner paths are invalid'
    try:svc._validate_completion_intent(intent,run,assignment,journal)
    except RuntimeError as actual:assert actual is error
    else:raise AssertionError('lazy capability failure hidden')
    rows.append({'case':'project_capability_lazy','error_identity':True})
    for name in ['_effective_process','_run_path']:
        run,assignment,intent,journal=documents(root);deps=dependencies(root,[]);error=OSError(name)
        def fail(*a,**kw):raise error
        deps[name]=fail
        try:fixture(cls,root,**deps)._validate_completion_intent(intent,run,assignment,journal)
        except OSError as actual:assert actual is error
        else:raise AssertionError('required callback failure hidden')
        rows.append({'case':'required_failure_'+name,'error_identity':True})
    run,assignment,intent,journal=documents(root)
    intent['final']['run']['tasks'][0]['status']='completed';sign(intent)
    assert fixture(cls,root,**dependencies(root,[]))._validate_completion_intent(intent,run,assignment,journal) is None
    rows.append({'case':'task_completed','reason':None})
    return rows
def direct(root):
    try:from processforge_core.composition import build_completion_intent_validation_service
    except ImportError:return
    run,assignment,intent,journal=documents(root);log=[]
    deps=dependencies(root,log)
    service=build_completion_intent_validation_service(
        project_root=root,fingerprint=module.canonical_fingerprint,terminal_assignment_statuses=lambda:module.TERMINAL_ASSIGNMENT_STATUSES,
        effective_process=deps['_effective_process'],rel=deps['core'].rel,run_path=deps['_run_path'],assignment_path=deps['_assignment_path'],flow_root=deps['_flow_root'],
        has_project_id=lambda:False,project_id=lambda root:(_ for _ in ()).throw(AssertionError('unused project_id')),
    )
    assert service.validate(intent,run,assignment,journal) is None
    assert not hasattr(service,'core')
    from dataclasses import replace
    for error in [TypeError('bad'),ValueError('bad'),RecursionError('bad')]:
        def fail(value):raise error
        assert replace(service,fingerprint=fail).validate(intent,run,assignment,journal)=='journal content is invalid'
    error=OSError('required')
    def fail(value):raise error
    try:replace(service,fingerprint=fail).validate(intent,run,assignment,journal)
    except OSError as actual:assert actual is error
    else:raise AssertionError('fingerprint infrastructure error hidden')

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
