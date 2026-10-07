"""Characterize existing automation projectors and live assignment-event selection."""
from __future__ import annotations
import argparse, ast, json, sys, tempfile, types
from pathlib import Path
from types import SimpleNamespace
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from processforge_core import process_execution as module
def retained(path):
    ns=dict(vars(module));ns['__name__']='processforge_core._automation_baseline'
    old=types.ModuleType(ns['__name__']);old.__dict__.update(ns);sys.modules[old.__name__]=old
    tree=ast.parse(path.read_text(encoding='utf-8-sig'))
    cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='ProcessExecutionService')
    exec('from __future__ import annotations\n'+ast.unparse(cls),old.__dict__)
    return old.ProcessExecutionService
def suite(cls,root):
    (root/'events.ndjson').unlink(missing_ok=True)
    assignment={'id':'task'}
    rows=[]
    class LazyCore:
        @property
        def required_output_checks(self):
            raise RuntimeError('must not inspect unused optional capability')
        @property
        def task_verification_fingerprint(self):
            raise RuntimeError('must not inspect unused verification capability')
        @property
        def event_runtime_paths(self):
            raise RuntimeError('must not inspect unused journal capability')
    lazy=cls(root,None,LazyCore())
    assert lazy._automation_states({}, {}, assignment)==[]
    assert lazy._latest_assignment_event('task',set()) is None
    rows.append('lazy optional capabilities')
    def project(stage,core=SimpleNamespace(),event=None):
        svc=cls(root,None,core)
        if event is not None:object.__setattr__(svc,'_latest_assignment_event',lambda *a:event)
        return svc._automation_states({},stage,assignment)
    assert project({})==[];rows.append([])
    stage={'technical_obligations':[None,{'id':'u','projector':'other'}]}
    r=project(stage);assert r[0]['status']=='unsupported';rows.append(r)
    binding={'id':'o','projector':'required-output-readiness'}
    for levels,expected in [([], 'ready'),(['WARN'],'ready'),(['FAIL'],'blocked'),(['FAIL','FAIL'],'blocked')]:
        core=SimpleNamespace(required_output_checks=lambda *a:[SimpleNamespace(level=l,message=l) for l in levels])
        r=project({'automation_bindings':[binding]},core);assert r[0]['status']==expected;rows.append(r)
    rows.append(project({'automation_bindings':[binding]}))
    v={'projector':'verification-state','verification':{'passed_event':'passed','failed_event':'failed'}}
    for event,fp,expected in [(None,None,'missing'),({'event_type':'passed'},None,'ready'),({'event_type':'failed'},None,'blocked'),({'event_type':'unknown'},None,'missing'),({'event_type':'passed','data':{'verification_fingerprint':'fp'}},'fp','ready'),({'event_type':'passed','data':{}},'fp','stale')]:
        core=SimpleNamespace()
        if fp is not None:core.task_verification_fingerprint=lambda *a:fp
        r=project({'automation_bindings':[v]},core,event);assert r[0]['status']==expected;rows.append(r)
    r=project({'automation_bindings':[{'projector':'verification-state'}]});assert r[0]['status']=='ready';rows.append(r)
    svc=cls(root,None,SimpleNamespace())
    assert svc._latest_assignment_event('task',{'passed'}) is None
    events=root/'events.ndjson'
    svc=cls(root,None,SimpleNamespace(event_runtime_paths=lambda *a:(events,None)))
    assert svc._latest_assignment_event('task',{'passed'}) is None
    for data,expected in [('not json\n'+json.dumps({'event_type':'passed','assignment':{'id':'task'}})+'\n', 'passed'),
                          (json.dumps({'event_type':'failed','subject':'task'})+'\n'+json.dumps({'event_type':'passed','subject':'other'})+'\n', 'failed'),
                          (json.dumps({'event_type':'passed','subject':'task'})+'\ninvalid\n', 'passed')]:
        events.write_text(data,encoding='utf-8')
        r=svc._latest_assignment_event('task',{'passed','failed'});assert r['event_type']==expected;rows.append(r)
    events.write_text('[]\n',encoding='utf-8')
    try:svc._latest_assignment_event('task',{'passed'})
    except AttributeError:rows.append('AttributeError')
    else:raise AssertionError('Preserve existing malformed event error')
    error=RuntimeError('required output failure')
    def fail(*args):raise error
    svc=cls(root,None,SimpleNamespace(required_output_checks=fail))
    try:svc._automation_states({}, {'automation_bindings':[binding]},assignment)
    except RuntimeError as e:assert e is error;rows.append('required exception identity')
    else:raise AssertionError('required error swallowed')
    return rows
def main():
    p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path);p.add_argument('--scratch-root',type=Path);a=p.parse_args()
    with tempfile.TemporaryDirectory(dir=a.scratch_root) as tmp:
        root=Path(tmp)
        current=suite(module.ProcessExecutionService,root)
        if a.baseline:assert current==suite(retained(a.baseline),root)
        try:
            from processforge_core.work.automation_readiness import AutomationReadinessService
        except ModuleNotFoundError:
            assert not a.baseline
        else:
            from dataclasses import FrozenInstanceError
            fake=AutomationReadinessService(project_root=root,has_output_checks=lambda:False,output_checks=lambda *a:[],has_fingerprint=lambda:False,fingerprint=lambda *a:'',has_event_paths=lambda:False,event_paths=lambda *a:(root/'missing',None),latest_event=lambda *a:None)
            assert fake.states({}, {}, {})==[]
            assert fake.latest_assignment_event('x',set()) is None
            try:fake.has_output_checks=True
            except FrozenInstanceError:pass
            else:raise AssertionError('mutable dependencies')
        print(json.dumps({'status':'pass','cases':len(current),'results':current},sort_keys=True))
if __name__=='__main__':main()
