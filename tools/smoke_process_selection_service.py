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
    calls=[]
    definitions={'a':{'id':'a','name':'Alpha','purpose':'purpose','expected_result':'result'},'b':{'id':'renamed','description':'fallback'}}
    def resolve(project,pid):
        calls.append(pid)
        if pid=='missing':raise OSError('missing')
        if pid=='exit':raise SystemExit('exit')
        if pid=='invalid':raise ValueError('invalid')
        return SimpleNamespace(process=definitions.get(pid,{}))
    svc=cls(root,None,SimpleNamespace(resolve_process_definition=resolve))
    for selection,requested,identifier,reason in [({'allowed':['a']},'','a',None),({'allowed':['a','b'],'default':'a'},'','', 'process_choice_required'),({'allowed':[],'default':'a'},'','', 'process_choice_required'),({'allowed':['a']},'a','a',None),({'allowed':['a']},'b','', 'process_not_allowed'),({'allowed':['a']},'missing','', 'process_not_found'),({'allowed':['a']},'exit','', 'process_not_found'),({'allowed':['a']},'invalid','', 'process_not_found')]:
        result=svc._select_process(selection,requested)
        assert result[0]==identifier
        if reason:assert result[1]['reason']==reason
        else:assert result[1]=={}
        rows.append(result)
    result=svc._process_candidates(['a','missing','b'],default='a')
    assert result[0]['default'] and result[1]['purpose']=='Process definition unavailable.'
    assert result[2]['id']=='renamed' and result[2]['purpose']=='fallback'
    rows.append(result)
    sentinel=[{'id':'override'}]
    object.__setattr__(svc,'_process_candidates',lambda ids,**kw:sentinel)
    assert svc._select_process({'allowed':['a','b']},'')[1]['candidates'] is sentinel
    rows.append('facade override')
    object.__setattr__(svc,'_blocked',lambda reason,**kw:{'reason':reason,'custom':True,**kw})
    assert svc._select_process({'allowed':['a']},'b')[1]['custom']
    error=RuntimeError('resolver required failure')
    def fail(*a):raise error
    svc=cls(root,None,SimpleNamespace(resolve_process_definition=fail))
    try:svc._select_process({'allowed':['a']},'b')
    except RuntimeError as e:assert e is error;rows.append('exception identity')
    else:raise AssertionError('required resolver failure hidden')
    # An allowed explicit id is not resolved by the selection policy.
    assert svc._select_process({'allowed':['a']},'a')==('a',{})
    return rows
def direct(root):
    try:from processforge_core.process_catalog.selection import ProcessSelectionService
    except ModuleNotFoundError:return
    svc=ProcessSelectionService(project_root=root,stable_ids=lambda value:value,resolve_definition=lambda *a:SimpleNamespace(process={}),blocked=lambda reason,**kw:{'reason':reason,**kw},candidates=lambda *a,**kw:[])
    assert svc.select({'allowed':['a']},'')==('a',{})
    assert svc.process_candidates(['a'])==[{'id':'a','title':'a','purpose':'','expected_result':'','default':False}]

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
