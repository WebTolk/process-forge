from __future__ import annotations
import argparse, ast, copy, json, sys, tempfile, types
from dataclasses import replace
import os, subprocess
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
    svc=cls(root,None,SimpleNamespace(locate_flow_root=lambda project:project/'.pf'))
    for key,value in dependencies.items():object.__setattr__(svc,key,value)
    return svc
def suite(cls,root):
    from unittest.mock import patch
    from processforge_core.work.continuation import ContinuationService
    rows=[]
    records=[{'run_id':'r','assignment_id':'a','active':True,'objective':'A work','created_at':'1','updated_at':'2','session_id':'s'}, {'run_id':'r','assignment_id':'b','active':True,'objective':' B   WORK ','created_at':'1','updated_at':'3'}, {'run_id':'q','assignment_id':'c','active':False,'objective':'a work','created_at':'1','updated_at':'4'}]
    svc=fixture(cls,root,_work_records=lambda **kw:records,_load_run=lambda r:{'id':r},_load_assignment=lambda a:{'id':a})
    for selectors,expected in [({'assignment_id':'a'},({'id':'r'},{'id':'a'})), ({'run_id':'q'},({'id':'q'},{'id':'c'})), ({},({'id':'r'},{'id':'b'})), ({'run_id':'x'},None)]:
        r=svc._select_work(**selectors);assert r==expected;rows.append(r)
    for selectors,message in [({'run_id':'r'},'assignment_choice_required'),({'assignment_id':'../a'},'invalid_work_selector'),({'run_id':1},'invalid_work_selector'),({'run_id':'q','assignment_id':'a'},'work_identity_mismatch')]:
        try:svc._select_work(**selectors)
        except ValueError as e:assert str(e)==message;rows.append(message)
        else:raise AssertionError(message)
    assert svc._preferred_record(records,'s') is records[0]
    assert svc._preferred_record([], '') is None
    rows.extend([svc._preferred_record(records,'s'),svc._find_by_objective(' A   WORK '),svc._find_by_objective('missing')])
    calls=[]
    def selected(self,session):
        calls.append(session);return {'run_id':'r','assignment_id':'a'}
    with patch.object(ContinuationService,'selected',selected):
        r=svc._select_work(session_id='s');assert r==({'id':'r'},{'id':'a'});rows.append(r)
        assert calls==['s']
        svc._select_work(assignment_id='a',session_id='s');assert calls==['s']
    override=fixture(cls,root,_work_records=lambda **kw:records,_preferred_record=lambda rows,s:None)
    assert override._find_by_objective('a work')['active'] is None
    assert override._select_work() is None
    error=RuntimeError('record read failure')
    def fail(**kw):raise error
    failed=fixture(cls,root,_work_records=fail)
    try:failed._select_work(assignment_id='a')
    except RuntimeError as e:assert e is error;rows.append('exception identity')
    else:raise AssertionError('read failure hidden')
    records.clear();assert svc._select_work() is None;rows.append(None)
    return rows
def direct(root):
    try:from processforge_core.work.selection import WorkSelectionService
    except ModuleNotFoundError:return
    svc=WorkSelectionService(bound_selection=lambda s:None,valid_selector=lambda s:True,records=lambda **kw:[],prefer=lambda records,s:None,load_run=lambda r:{},load_assignment=lambda a:{})
    assert svc.select(assignment_id='a') is None
    assert svc.find_by_objective('x')=={'active':None,'historical':[]}
    assert svc.preferred_record([], '') is None

def canonical():
    """Approved exact-pair authority, live reloads and unchanged fallback guards."""
    from processforge_core.work.selection import WorkSelectionService
    calls=[]
    run={'id':'r','process':'p','tasks':[{'id':'a'}],'future':{'values':[1]}}
    task={'id':'a','run_id':'r','process':'p','future':{'values':[2]}}
    def load(kind, value):
        calls.append(kind)
        return copy.deepcopy(value)
    def catalog(**kw):
        calls.append('catalog')
        assert kw=={'include_historical':True}
        return [{'run_id':'r','assignment_id':'a','active':True}]
    svc=WorkSelectionService(bound_selection=lambda s:None,valid_selector=lambda s:s in {'r','a'},
        records=catalog,prefer=lambda records,s:records[0] if records else None,
        load_run=lambda r:load('run',run),load_assignment=lambda a:load('assignment',task))
    assert svc.select(run_id='r',assignment_id='a')==(run,task)
    assert calls==['run','assignment','run','assignment']
    count=1

    # Failure to prove a canonical pair must use the complete old catalog path.
    invalid=[({'id':'other'},{}), ({'id':None},{}), ({},{'id':'other'}),
        ({},{'id':None}), ({},{'run_id':'other'}), ({},{'run_id':None}),
        ({'tasks':None},{}), ({'tasks':{}},{}), ({'tasks':[]},{}),
        ({'tasks':[{'id':'a'},{'id':'a'}]},{}),
        ({'tasks':[{'id':'a','assignment':'.pf/assignments/other.yaml'}]},{}),
        ({},{'process':'other'}), ({},{'process':None})]
    for run_delta,task_delta in invalid:
        calls.clear()
        r,t=({**run,**run_delta},{**task,**task_delta})
        candidate=replace(svc,load_run=lambda _:load('run',r),load_assignment=lambda _:load('assignment',t))
        assert candidate.select(run_id='r',assignment_id='a')==(r,t)
        assert calls==['run','assignment','catalog','run','assignment']
        count+=1
    for selectors in ({'assignment_id':'a'},{'run_id':'r'},{}):
        calls.clear()
        assert svc.select(**selectors)==(run,task)
        assert calls==['catalog','run','assignment']
        count+=1
    for selectors in ({'run_id':'../r','assignment_id':'a'},{'run_id':1,'assignment_id':'a'}):
        calls.clear()
        try:svc.select(**selectors)
        except ValueError as error:assert str(error)=='invalid_work_selector'
        else:raise AssertionError('Invalid selector accepted')
        assert not calls
        count+=1

    # Preserve the existing legacy-container process exception in _run_matches.
    for process in ('p',{'id':'p'},'task-batch-execution','multi-agent-task-orchestration'):
        calls.clear()
        r={**run,'process':process}
        candidate=replace(svc,load_run=lambda _:load('run',r))
        assert candidate.select(run_id='r',assignment_id='a')==(r,task)
        assert calls==['run','assignment','run','assignment']
        count+=1

    # Every selected-read exception escapes unchanged, before or after proof.
    for fail_at in range(1,5):
        for error_type in (PermissionError,OSError,RuntimeError):
            calls.clear()
            failure=error_type('selected read failed')
            def failing(kind,value):
                result=load(kind,value)
                if len(calls)==fail_at:raise failure
                return result
            candidate=replace(svc,load_run=lambda _:failing('run',run),load_assignment=lambda _:failing('assignment',task))
            try:candidate.select(run_id='r',assignment_id='a')
            except error_type as error:assert error is failure
            else:raise AssertionError('Selected read failure hidden')
            assert calls==['run','assignment','run','assignment'][:fail_at]
            count+=1

    # A changed identity after proof cannot escape via catalog fallback.
    for r,t in [({**run,**rd},{**task,**td}) for rd,td in invalid]+[({},task),(run,{})]:
        calls.clear()
        candidate=replace(svc,
            load_run=lambda _:load('run',run if not calls else r),
            load_assignment=lambda _:load('assignment',task if len(calls)==1 else t))
        try:candidate.select(run_id='r',assignment_id='a')
        except ValueError as error:assert str(error)=='work_identity_mismatch'
        else:raise AssertionError('Final identity change accepted')
        assert calls==['run','assignment','run','assignment']
        count+=1

    calls.clear()
    later={**task,'future':{'values':[3]},'status':'done'}
    candidate=replace(svc,load_assignment=lambda _:load('assignment',task if len(calls)==1 else later))
    assert candidate.select(run_id='r',assignment_id='a')==(run,later)
    assert calls==['run','assignment','run','assignment']
    count+=1

    calls.clear()
    def bound(session):
        calls.append('binding');return {'run_id':'r','assignment_id':'a'}
    assert replace(svc,bound_selection=bound).select(session_id='s')==(run,task)
    assert calls==['binding','run','assignment','run','assignment']
    calls.clear()
    assert replace(svc,bound_selection=bound).select(run_id='r',assignment_id='a',session_id='s')==(run,task)
    assert calls==['run','assignment','run','assignment']
    count+=2
    return count

def optional_yaml():
    # Core raw selection remains importable with its existing non-YAML paths.
    code='''import builtins
import sys
original_import = builtins.__import__
missing_name = 'yaml'
def without_yaml(name, *args, **kwargs):
    if name == 'yaml' or name.startswith('yaml.'):
        raise ModuleNotFoundError('missing dependency', name=missing_name)
    return original_import(name, *args, **kwargs)
builtins.__import__ = without_yaml
from processforge_core.work.selection import WorkSelectionService
assert 'processforge_core.work.context' not in sys.modules
calls=[]
run={'id':'r','process':'p','tasks':[{'id':'a'}]}
task={'id':'a','run_id':'r','process':'p'}
def load(kind, value):
    calls.append(kind)
    return dict(value)
def records(**kwargs):
    calls.append('catalog')
    return [{'run_id':'r','assignment_id':'a','active':True}]
service=WorkSelectionService(bound_selection=lambda s:None,valid_selector=lambda s:True,
    records=records,prefer=lambda rows,s:rows[0],
    load_run=lambda r:load('run',run),load_assignment=lambda a:load('assignment',task))
assert service.select(assignment_id='a') == (run,task)
assert calls == ['catalog','run','assignment']
calls.clear()
assert service.select(run_id='r',assignment_id='a') == (run,task)
assert calls == ['run','assignment','catalog','run','assignment']
assert 'yaml' not in sys.modules
assert 'processforge_core.work.context' not in sys.modules
missing_name = 'required-proof-dependency'
calls.clear()
try:
    service.select(run_id='r',assignment_id='a')
except ModuleNotFoundError as error:
    assert error.name == 'required-proof-dependency'
else:
    raise AssertionError('Required dependency failure hidden')
assert calls == ['run','assignment']
'''
    result=subprocess.run([sys.executable,'-B','-c',code],env={**os.environ,
        'PYTHONPATH':str(ROOT/'src'),'PYTHONDONTWRITEBYTECODE':'1'},capture_output=True,text=True,timeout=30)
    assert result.returncode==0,result.stdout+result.stderr

def main():
    p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path);p.add_argument('--scratch-root',type=Path);a=p.parse_args()
    if a.scratch_root:a.scratch_root.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=a.scratch_root) as tmp:
        root=Path(tmp)
        current=suite(module.ProcessExecutionService,root)
        if a.baseline:assert current==suite(retained(a.baseline),root)
        direct(root)
        extra=canonical()
        optional_yaml()
        print(json.dumps({'status':'pass','cases':len(current),'canonical_cases':extra,'optional_yaml_import_and_fallback':'pass','results':current},sort_keys=True))
if __name__=='__main__':main()
