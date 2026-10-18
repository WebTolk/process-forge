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

def intent_data(stage='finish'):
    return {'run_id':'r','assignment_id':'a','unknown':{'keep':True},'final':{
        'assignment':{'id':'a','run_id':'r','stage':stage,'status':'done','unknown':{'keep':True}},
        'run':{'id':'r','status':'completed','unknown':{'keep':True}},
        'summary':{'content':'summary'},'handoff':{'content':None},'task_index':{'content':17},
        'events':[{'event_type':'run.completed','event_id':'event-one'},{'event_type':'run.summary.created','event_id':'event-two','stage_id':'explicit','outcome':'custom','previous_stage_id':'before','next_stage_id':'after'}],
    }}
class Journal:
    def __init__(self,log,failure,error):self.log=log;self.failure=failure;self.error=error
    def unlink(self,*,missing_ok):
        assert missing_ok is True;self.log.append(['unlink',missing_ok])
        if self.failure=='unlink':raise self.error
def operations(root,log,failure=None,mutate=False):
    error=OSError('failure-'+str(failure));state={'action':'old','recovered':False,'nested':{'keep':True}}
    def record(label,*values):
        log.append([label,*values])
        if label==failure:raise error
    def yaml(path,document):
        name='assignment' if path.name=='a.yaml' else 'run'
        record('yaml-'+name,path.relative_to(root).as_posix(),copy.deepcopy(document))
        if mutate:document['writer_marker']=name
    def text(path,value):record('text-'+path.name,path.relative_to(root).as_posix(),value)
    def read_state(**selectors):record('state',selectors);return state
    def projection(value):assert value is state;record('projection',copy.deepcopy(value))
    def emit(event_type,run,assignment,stage_id,**metadata):
        label='emit-'+str(metadata['event_id'])
        record(label,event_type,stage_id,metadata,copy.deepcopy(run),copy.deepcopy(assignment))
    def intent_path(run_id):record('intent_path',run_id);return Journal(log,failure,error)
    deps={'_assignment_path':lambda aid:root/'.pf/assignments'/(aid+'.yaml'),'_run_path':lambda rid:root/'.pf/runs'/rid/'run.yaml','_flow_root':lambda:root/'.pf','_atomic_yaml':yaml,'_atomic_text':text,'state':read_state,'_write_projection':projection,'_emit':emit,'_completion_intent_path':intent_path}
    return deps,state,error
def suite(cls,root):
    rows=[]
    for remove in [False,True]:
        for stage in ['finish',None]:
            for mutate in [False,True]:
                log=[];deps,state,error=operations(root,log,mutate=mutate);svc=fixture(cls,root,**deps);intent=intent_data(stage)
                original=copy.deepcopy(intent)
                result=svc._replay_completion_intent(intent,session_id='session',remove_intent=remove)
                assert intent==original
                assert result['action']=='run_completed' and result['recovered'] is True and result['previous_stage_id']==str(stage or '') and result['next_stage_id']==''
                assert result is not state and result['nested'] is state['nested'] and state['action']=='old' and state['recovered'] is False
                expected=['yaml-assignment','yaml-run','text-summary.md','text-r-handoff.md','text-task-index.md','state','projection','emit-event-one','emit-event-two']
                if remove:expected+=['intent_path','unlink']
                assert [x[0] for x in log]==expected
                assert log[3][-1]=='' and log[4][-1]=='17'
                first=log[7];assert first[2]==str(stage or '') and first[3]['outcome']=='completed'
                if mutate:assert first[4]['writer_marker']=='run' and first[5]['writer_marker']=='assignment'
                assert log[5][1]=={'run_id':'r','assignment_id':'a','session_id':'session'}
                rows.append({'remove':remove,'stage':stage,'mutate':mutate,'response':result,'calls':log})
    steps=['yaml-assignment','yaml-run','text-summary.md','text-r-handoff.md','text-task-index.md','state','projection','emit-event-one','emit-event-two','intent_path','unlink']
    for failure in steps:
        log=[];deps,state,error=operations(root,log,failure);svc=fixture(cls,root,**deps);intent=intent_data();original=copy.deepcopy(intent)
        try:svc._replay_completion_intent(intent)
        except OSError as actual:assert actual is error
        else:raise AssertionError('required replay failure hidden')
        assert intent==original and [x[0] for x in log]==steps[:steps.index(failure)+1]
        rows.append({'failure':failure,'prefix':[x[0] for x in log],'identity':True})
    log=[];deps,state,error=operations(root,log,'intent_path');svc=fixture(cls,root,**deps)
    svc._replay_completion_intent(intent_data(),remove_intent=False)
    assert all(x[0]!='intent_path' for x in log)
    rows.append({'optional_intent_cleanup_lazy':True})
    log=[];deps,state,error=operations(root,log);svc=fixture(cls,root,**deps);intent=intent_data()
    first=svc._replay_completion_intent(intent,remove_intent=False);first_calls=copy.deepcopy(log);log.clear()
    second=svc._replay_completion_intent(intent,remove_intent=False)
    assert first==second and log==first_calls
    rows.append({'repeat_payload_and_events':True})
    return rows
def direct(root):
    try:from processforge_core.composition import build_completion_intent_replay_service
    except ImportError:return
    log=[];deps,state,error=operations(root,log)
    service=build_completion_intent_replay_service(assignment_path=deps['_assignment_path'],run_path=deps['_run_path'],flow_root=deps['_flow_root'],atomic_yaml=deps['_atomic_yaml'],atomic_text=deps['_atomic_text'],state=deps['state'],write_projection=deps['_write_projection'],emit=deps['_emit'],intent_path=deps['_completion_intent_path'])
    result=service.replay(intent_data(),remove_intent=False)
    assert result['action']=='run_completed' and result['nested'] is state['nested'] and not hasattr(service,'core')

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
