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

class Reader:
    def __init__(self, snapshot, log):
        self.snapshot=snapshot;self.log=log;self.fail=None
    def load(self,path=None):
        self.log.append(['load',None if path is None else path.name])
        if self.fail=='load':raise self.error
        return self.snapshot
    def checksum(self,path):
        self.log.append(['checksum',path.name])
        if self.fail=='checksum':raise self.error
        return 'sha256:snapshot'
def suite(cls,root):
    rows=[]
    for meta in [{'id':'snap-1'},None,[],{'id':0}]:
        log=[];reader=Reader({'snapshot':meta},log)
        def read():log.append(['reader']);return reader
        svc=fixture(cls,root,_flow_root=lambda:root/'.pf',_snapshot_reader=read)
        process={'id':'process','version':'1.0','unknown':{'tuple':(1,2),'text':'Русский'}}
        active=['python'];selected=['docs.example'];allowed=['process']
        pin=svc._process_pin(process,root/'process.yaml',active_specializations=active,selected_resource_ids=selected,allowed_processes=allowed)
        assert pin['definition']['unknown']['tuple']==[1,2]
        assert pin['definition'] is not process and pin['definition']['unknown'] is not process['unknown']
        assert pin['active_specializations'] is active and pin['selected_resource_ids'] is selected and pin['allowed_processes'] is allowed
        assert pin['process_source']=='process.yaml' and pin['process_fingerprint']==module.canonical_fingerprint(pin['definition'])
        assert log==[['reader'],['load','project-context.snapshot.yaml'],['reader'],['checksum','project-context.snapshot.yaml']]
        rows.append({'meta':meta,'pin':pin,'calls':copy.deepcopy(log)})
        reader.snapshot={'snapshot':{'id':'snap-2'}}
        assert svc._process_pin(process,root/'process.yaml',active_specializations=active,selected_resource_ids=selected,allowed_processes=allowed)['snapshot_id']=='snap-2'
    for process in [{'id':'outside','version':2,'extra':True},{'id':'','version':None}]:
        svc=fixture(cls,root,_flow_root=lambda:root/'.pf',_snapshot_reader=lambda:Reader({},[]))
        pin=svc._process_pin(process,root.parent/'external.yaml',active_specializations=[],selected_resource_ids=[],allowed_processes=[])
        assert pin['process_source']=='catalog:'+(process['id'] or 'external')
        rows.append({'outside':pin})
    for resolved in [{'knowledge_resources':['z','a','z','',' a ',None]},{'knowledge_resources':[]},None,[],{}]:
        log=[];reader=Reader({'resolved':resolved},log)
        svc=fixture(cls,root,_snapshot_reader=lambda:reader)
        ids=svc._selected_resource_ids()
        assert ids==sorted(set(ids))
        reader.snapshot={'resolved':{'knowledge_resources':['fresh']}}
        assert svc._selected_resource_ids()==['fresh']
        rows.append({'resolved':resolved,'ids':ids,'calls':log})
    for failure in ['load','checksum']:
        log=[];reader=Reader({},log);reader.fail=failure;reader.error=OSError(failure)
        svc=fixture(cls,root,_flow_root=lambda:root/'.pf',_snapshot_reader=lambda:reader)
        try:svc._process_pin({'id':'x'},root/'p.yaml',active_specializations=[],selected_resource_ids=[],allowed_processes=[])
        except OSError as error:assert error is reader.error
        else:raise AssertionError('required failure hidden')
        rows.append({'failure':failure,'calls':log})
    log=[];reader=Reader({},log)
    svc=fixture(cls,root,_flow_root=lambda:root/'.pf',_snapshot_reader=lambda:reader)
    try:svc._process_pin({'bad':object()},root/'p.yaml',active_specializations=[],selected_resource_ids=[],allowed_processes=[])
    except TypeError:pass
    else:raise AssertionError('non-JSON definition accepted')
    assert log==[['load','project-context.snapshot.yaml'],['checksum','project-context.snapshot.yaml']]
    rows.append({'json_failure':log})
    return rows
def direct(root):
    try:from processforge_core.composition import build_process_pin_read_service
    except ImportError:return
    log=[];reader=Reader({'resolved':{'knowledge_resources':['b','a']}},log)
    fingerprints=[]
    def fingerprint(value):fingerprints.append(copy.deepcopy(value));return 'injected'
    service=build_process_pin_read_service(project_root=root,flow_root=lambda:root/'.pf',snapshots=lambda:reader,fingerprint=fingerprint,stable_ids=lambda value:['injected','a'])
    assert service.selected_resource_ids()==['a','injected']
    pin=service.pin({'id':'p','custom':{'keep':True}},root/'p.yaml',active_specializations=[],selected_resource_ids=[],allowed_processes=[])
    assert pin['process_fingerprint']=='injected' and fingerprints==[pin['definition']]
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
