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
    codes=['invalid_evidence','not_applicable_evidence_incomplete','artifact_path_missing','outcome_not_allowed','invalid_process_definition']
    for blocker in [None,[],True,'invalid_evidence',{}, {'code':0}, {'code':'permission_denied'}, {'code':'unknown'}]+[{'code':code,'unknown':{'keep':True}} for code in codes]:
        result=cls._is_recoverable_transition_rejection(blocker)
        assert result==(isinstance(blocker,dict) and blocker.get('code') in codes)
        rows.append({'blocker':blocker,'recoverable':result})
    for run,assignment in [({'id':'r'},{'id':'a'}),({'id':0},{'id':None}),({'id':17},{'id':9})]:
        log=[];nested={'unknown':['keep']};original={'action':'old','reason':'old','blockers':['old'],'nested':nested}
        def state(**kw):log.append(kw);return original
        svc=fixture(cls,root,state=state)
        blockers=[{'code':'invalid_evidence','unknown':{'keep':True}}]
        result=svc._transition_rejected(run=run,assignment=assignment,session_id='s',reason='why',blockers=blockers)
        assert result['action']=='transition_rejected' and result['reason']=='why' and result['blockers'] is blockers
        assert result is not original and result['nested'] is nested
        assert original['action']=='old' and original['blockers']==['old']
        assert log==[{'run_id':str(run.get('id') or ''),'assignment_id':str(assignment.get('id') or ''),'session_id':'s'}]
        rows.append({'response':result,'calls':log})
    error=RuntimeError('state failed')
    def fail(**kw):raise error
    svc=fixture(cls,root,state=fail)
    try:svc._transition_rejected(run={},assignment={},session_id='',reason='r',blockers=[])
    except RuntimeError as actual:assert actual is error
    else:raise AssertionError('state failure hidden')
    rows.append({'required_failure_identity':True})
    return rows
def direct(root):
    try:from processforge_core.composition import build_transition_rejection_policy
    except ImportError:return
    calls=[]
    service=build_transition_rejection_policy(state=lambda **kw:calls.append(kw) or {'unknown':'keep'})
    assert service.is_recoverable({'code':'invalid_evidence'})
    result=service.rejected(run={'id':'r'},assignment={'id':'a'},session_id='',reason='why',blockers=[])
    assert result=={'unknown':'keep','action':'transition_rejected','reason':'why','blockers':[]}
    assert calls==[{'run_id':'r','assignment_id':'a','session_id':''}]
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
