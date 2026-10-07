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

class JournalPath:
    def __init__(self,present,log,error=None):self.present=present;self.log=log;self.error=error
    def is_file(self):
        self.log.append('is_file')
        if self.error:raise self.error
        return self.present
def suite(cls,root):
    rows=[]
    for run_id,assignment_id in [('r','a'),('', 'a'),(None,'a'),(0,'a'),('bad/path','a'),('r','bad/path'),(17,9)]:
        for present in [False,True]:
            log=[];path=JournalPath(present,log);intent={'unknown':{'keep':True}}
            def locate(rid):log.append(['path',rid]);return path
            def load(p):assert p is path;log.append('load');return intent
            def validate(value,run,assignment,p):assert value is intent and p is path;log.append('validate');return None
            svc=fixture(cls,root,core=SimpleNamespace(load_yaml_document=load),_completion_intent_path=locate,_validate_completion_intent=validate)
            result=svc._load_completion_intent({'id':run_id},{'id':assignment_id})
            valid=bool(module.SAFE_ID_RE.fullmatch(str(run_id or '')) and module.SAFE_ID_RE.fullmatch(str(assignment_id or '')))
            assert result==((intent,None) if valid and present else (None,None))
            if valid and present:assert result[0] is intent
            assert log==([] if not valid else [['path',str(run_id or '')],'is_file']+(['load','validate'] if present else []))
            rows.append({'ids':[run_id,assignment_id],'present':present,'result':result,'calls':log})
    for error in [OSError('disk'),ValueError('yaml'),TypeError('format')]:
        log=[];path=JournalPath(True,log)
        def fail(path):log.append('load');raise error
        svc=fixture(cls,root,core=SimpleNamespace(load_yaml_document=fail),_completion_intent_path=lambda rid:path,_validate_completion_intent=lambda *a:(_ for _ in ()).throw(AssertionError('validation after load error')))
        result=svc._load_completion_intent({'id':'r'},{'id':'a'})
        assert result==(None,'journal unreadable: '+str(error)) and log==['is_file','load']
        rows.append({'handled':type(error).__name__,'result':result,'calls':log})
    for diagnostic in ['journal kind is invalid','journal identity does not match selected work','journal owner paths are invalid']:
        log=[];path=JournalPath(True,log)
        svc=fixture(cls,root,core=SimpleNamespace(load_yaml_document=lambda p:{'keep':True}),_completion_intent_path=lambda rid:path,_validate_completion_intent=lambda *a:diagnostic)
        result=svc._load_completion_intent({'id':'r'},{'id':'a'})
        assert result==(None,diagnostic);rows.append({'validation_error':result})
    for location in ['path','is_file','load','validate']:
        error=RuntimeError(location);log=[];path=JournalPath(True,log,error if location=='is_file' else None)
        def fail(*a):raise error
        svc=fixture(cls,root,core=SimpleNamespace(load_yaml_document=fail if location=='load' else lambda path:{}),_completion_intent_path=fail if location=='path' else lambda rid:path,_validate_completion_intent=fail if location=='validate' else lambda *a:None)
        try:svc._load_completion_intent({'id':'r'},{'id':'a'})
        except RuntimeError as actual:assert actual is error
        else:raise AssertionError('unexpected failure hidden')
        rows.append({'required_failure':location,'identity':True})
    class UnusedCore:
        @property
        def load_yaml_document(self):raise AssertionError('unused loader')
    svc=fixture(cls,root,core=UnusedCore(),_completion_intent_path=lambda rid:JournalPath(False,[]))
    assert svc._load_completion_intent({'id':'unsafe/path'},{'id':'a'})==(None,None)
    assert svc._load_completion_intent({'id':'r'},{'id':'a'})==(None,None)
    rows.append({'loader_lazy':True})
    path=JournalPath(True,[]);document={'sequence':1}
    svc=fixture(cls,root,core=SimpleNamespace(load_yaml_document=lambda path:copy.deepcopy(document)),_completion_intent_path=lambda rid:path,_validate_completion_intent=lambda *a:None)
    first=svc._load_completion_intent({'id':'r'},{'id':'a'})
    document['sequence']=2
    second=svc._load_completion_intent({'id':'r'},{'id':'a'})
    assert first[0]['sequence']==1 and second[0]['sequence']==2
    rows.append({'live_reads':[first,second]})
    log=[]
    svc=fixture(cls,root,_run_path=lambda rid:log.append(rid) or root/'.pf/runs'/rid/'run.yaml')
    result=svc._completion_intent_path('r')
    assert result==root/'.pf/runs/r/completion-intent.yaml' and log==['r']
    rows.append({'journal_path':result.relative_to(root).as_posix(),'calls':log})
    return rows
def direct(root):
    try:from processforge_core.composition import build_completion_intent_read_service
    except ImportError:return
    path=JournalPath(True,[]);document={'keep':True};seen=[]
    service=build_completion_intent_read_service(run_path=lambda rid:root/'run.yaml',intent_path=lambda rid:path,valid_id=lambda value:True,load_document=lambda path:document,validate=lambda value,run,assignment,path:seen.append(value) or None)
    assert service.path('r')==root/'completion-intent.yaml'
    result=service.load({'id':'r'},{'id':'a'})
    assert result[0] is document and seen[0] is document and not hasattr(service,'core')

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
