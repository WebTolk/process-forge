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

class RoutePath:
    name='process-routes.yaml'
    def __init__(self,exists,log):self.available=exists;self.log=log
    def __truediv__(self,name):assert name=='process-routes.yaml';return self
    def exists(self):self.log.append('exists');return self.available
def suite(cls,root):
    rows=[]
    runs=[
        {'process':'current','process_execution':{'allowed_processes':['current','other','third','other','']},'final_artifacts':['summary.md','r-handoff.md','second-handoff.md'],'unknown':{'keep':True}},
        {'process':'current','process_execution':None,'final_artifacts':None},
        {'process':0,'process_execution':{'allowed_processes':['other','third']},'final_artifacts':['unrelated.md']},
    ]
    declarations=[[],[{'to_process':'third'},{'target_process':'other'}],['bad',None,{'to_process':'unavailable'},{'target_process':'other'}],None]
    for run in runs:
        for transitions in declarations:
            for exists in [False,True]:
                log=[];route=RoutePath(exists,log)
                routes={'routes':[{'from_process':'unrelated','to_process':'third'},{'from_process':str(run.get('process') or ''),'target_process':'other'}]}
                def load(path):assert path is route;log.append('load');return routes
                def flow():log.append('flow');return route
                class Core:
                    def load_yaml_document(self,path):return load(path)
                svc=fixture(cls,root,core=Core(),_flow_root=flow)
                process={'process_transitions':copy.deepcopy(transitions)}
                original=copy.deepcopy((run,process))
                result=svc._next_work_advisory(process,run)
                assert (run,process)==original
                assert log==(['flow','exists','load'] if exists else ['flow','exists'])
                available=result['next']['available_processes']
                assert str(run.get('process') or '') not in available
                assert result['session_continuity']=={'recommendation':'auto','reason':'process_boundary'}
                if 'handoff' in result:assert result['handoff']['path']=='r-handoff.md'
                declared=[str(x.get('to_process') or x.get('target_process') or '') for x in transitions if isinstance(x,dict)] if isinstance(transitions,list) else []
                routed=declared+(['other'] if exists else [])
                recommended=next((x for x in routed if x in available),'')
                assert result['next'].get('recommended_process','')==recommended
                rows.append({'run':run,'transitions':transitions,'exists':exists,'result':result,'calls':log})
    log=[];route=RoutePath(False,log)
    class LazyCore:
        @property
        def load_yaml_document(self):raise AssertionError('unused loader touched')
    svc=fixture(cls,root,core=LazyCore(),_flow_root=lambda:route)
    assert svc._next_work_advisory({}, {})['next']=={'available_processes':[]}
    rows.append({'lazy_loader':True})
    error=OSError('routes failure')
    def fail(path):raise error
    svc=fixture(cls,root,core=SimpleNamespace(load_yaml_document=fail),_flow_root=lambda:RoutePath(True,[]))
    try:svc._next_work_advisory({}, {})
    except OSError as actual:assert actual is error
    else:raise AssertionError('required route failure hidden')
    rows.append({'required_failure_identity':True})
    # Every operation reads route content anew.
    log=[];document={'routes':[{'from_process':'current','to_process':'other'}]}
    svc=fixture(cls,root,core=SimpleNamespace(load_yaml_document=lambda path:document),_flow_root=lambda:RoutePath(True,log))
    run={'process':'current','process_execution':{'allowed_processes':['other','third']}}
    first=svc._next_work_advisory({},run)
    document['routes'][0]['to_process']='third'
    second=svc._next_work_advisory({},run)
    assert first['next']['recommended_process']=='other' and second['next']['recommended_process']=='third'
    rows.append({'live_routes':[first,second]})
    return rows
def direct(root):
    try:from processforge_core.composition import build_work_boundary_advisory_service
    except ImportError:return
    path=RoutePath(False,[])
    service=build_work_boundary_advisory_service(flow_root=lambda:path,stable_ids=module._stable_ids,load_document=lambda path:(_ for _ in ()).throw(AssertionError('unused')))
    assert service.advisory({'process_transitions':[{'to_process':'b'}]},{'process':'a','process_execution':{'allowed_processes':['a','b']}})['next']['recommended_process']=='b'
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
