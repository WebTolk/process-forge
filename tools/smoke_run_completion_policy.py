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

def suite(cls,root):
    rows=[]
    diagnostic={'detail':{'values':['keep']}}
    gates={
        'missing':{'required':True,'blocking':True,'satisfied':False,'diagnostic':diagnostic},
        'ready':{'required':True,'blocking':True,'satisfied':True},
        'optional':{'required':False,'blocking':True,'satisfied':False},
        'nonblocking':{'required':True,'blocking':False,'satisfied':False},
        'bad-diagnostic':{'required':True,'blocking':True,'satisfied':False,'diagnostic':[]},
    }
    for gate_ids in [[],list(gates),['missing','missing'],None]:
        calls=[];evidence=[{'unknown':{'keep':True}}]
        assignment={'id':'selected','extra':True}
        def accumulate(value):assert value is assignment;calls.append(['evidence']);return evidence
        def state(process,gate_id,ev,*,phase):
            assert ev is evidence and phase=='run_completion'
            calls.append(['gate',gate_id,phase]);return gates[gate_id]
        svc=fixture(cls,root,_accumulated_evidence=accumulate,_gate_state=state)
        process={'run_completion':{'gates':gate_ids},'unknown':{'keep':True}}
        run={'tasks':[{'id':'selected','status':'open'},{'id':'open','status':'open','extra':1},{'id':'optional','blocking':False,'status':'open'},{'id':'zero','blocking':0,'status':None},None,'bad',{'id':'done','status':'done'},{'id':'completed','status':'completed'},{'id':'cancelled','status':'cancelled'},{'id':None,'status':9}]}
        original=copy.deepcopy((process,run,assignment))
        result=svc._run_completion_blockers(process,run,assignment)
        assert (process,run,assignment)==original
        assert [x['assignment_id'] for x in result if x['code']=='blocking_assignment_incomplete']==['open','zero','']
        for blocker in result:
            if 'diagnostic' in blocker:
                assert blocker['diagnostic'] is not diagnostic and blocker['diagnostic']['detail'] is not diagnostic['detail']
        rows.append({'gate_ids':gate_ids,'blockers':result,'calls':calls})
    for completion,tasks in [(None,None),([],{}),({},'bad')]:
        calls=[]
        svc=fixture(cls,root,_accumulated_evidence=lambda value:calls.append('evidence') or [])
        assert svc._run_completion_blockers({'run_completion':completion},{'tasks':tasks},{'id':'a'})==[]
        rows.append({'malformed':completion,'tasks':tasks,'calls':calls})
    calls=[]
    svc=fixture(cls,root,_accumulated_evidence=lambda value:['custom'],_string_list=lambda value:['custom'],_gate_state=lambda process,gate_id,ev,*,phase:calls.append([gate_id,ev,phase]) or {'required':True,'blocking':True,'satisfied':False})
    rows.append({'overrides':svc._run_completion_blockers({}, {}, {}),'calls':calls})
    for failing in ['_accumulated_evidence','_string_list','_gate_state']:
        error=RuntimeError(failing)
        def fail(*a,**kw):raise error
        deps={'_accumulated_evidence':lambda value:[],'_string_list':lambda value:['g'],'_gate_state':lambda *a,**kw:{}}
        deps[failing]=fail
        svc=fixture(cls,root,**deps)
        try:svc._run_completion_blockers({}, {}, {})
        except RuntimeError as actual:assert actual is error
        else:raise AssertionError('required failure masked')
        rows.append({'failure':failing})
    for tasks,target in [([{'id':'a','status':'open','custom':{'keep':True}},{'id':'a','status':'failed'},{'id':'b','status':'open'},None],'a'),([{'id':0,'custom':1},{'id':None},{'id':''}],'') ,(None,'a'),({},'a')]:
        svc=fixture(cls,root);run={'tasks':copy.deepcopy(tasks),'unknown':'keep'}
        original_tasks=run['tasks'];original_items=list(original_tasks) if isinstance(original_tasks,list) else []
        assert svc._set_run_task_status(run,target,'done') is None
        assert run['tasks'] is original_tasks and run['unknown']=='keep'
        if isinstance(original_tasks,list):
            assert all(run['tasks'][i] is original_items[i] for i in range(len(original_items)))
            for task in original_tasks:
                if isinstance(task,dict) and str(task.get('id') or '')==target:assert task['status']=='done'
        rows.append({'mutation':run,'target':target})
    return rows
def direct(root):
    try:from processforge_core.composition import build_run_completion_policy
    except ImportError:return
    diag={'nested':['keep']}
    service=build_run_completion_policy(accumulated_evidence=lambda a:['injected'],string_list=lambda value:['g'],gate_state=lambda process,gate_id,evidence,*,phase:{'required':True,'blocking':True,'satisfied':False,'diagnostic':diag})
    result=service.blockers({}, {}, {})
    assert result==[{'code':'run_completion_gate_missing','gate_id':'g','diagnostic':diag}]
    result[0]['diagnostic']['nested'].append('changed')
    assert diag=={'nested':['keep']}
    run={'tasks':[{'id':'a','status':'open','extra':True}]}
    service.set_task_status(run,'a','done')
    assert run=={'tasks':[{'id':'a','status':'done','extra':True}]}
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
