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
    class UnusedCore:
        @property
        def render_task_index(self):raise AssertionError('summary accessed unused renderer')
    for run in [{'id':'r','process':'p'},{'id':'r','title':'Title','process':None},{'id':'r','title':None},{}]:
        for history in [None,[],[None,'bad',{'stage_id':'s','status':'completed','outcome':'done','unknown':'keep'}]]:
            svc=fixture(cls,root,core=UnusedCore());assignment={'stage_history':history,'unknown':{'keep':True}}
            original=copy.deepcopy((run,assignment))
            result=svc._render_summary(run,assignment)
            assert result.endswith('\n') and 'status: '+chr(96)+'completed'+chr(96) in result
            assert (run,assignment)==original
            assert ('No stage history recorded.' in result)==(not history)
            rows.append({'run':run,'history':history,'summary':result})
    for custom in [False,True]:
        for tasks in [[],[{'id':'a','status':'open','extra':True},None,'bad',{'id':7,'status':None}]]:
            log=[];run={'id':'r','tasks':tasks,'unknown':True}
            def path(run_id):log.append(['path',run_id]);return root/'.pf/runs'/run_id/'run.yaml'
            def atomic(target,text):log.append(['write',target.relative_to(root).as_posix(),text])
            core=SimpleNamespace()
            if custom:
                def render(base,value):assert base==root and value is run;log.append(['render']);return 'custom\n'
                core.render_task_index=render
            svc=fixture(cls,root,core=core,_run_path=path,_atomic_text=atomic)
            original=copy.deepcopy(run)
            assert svc._write_task_index(run) is None and run==original
            assert log[0]==['path','r'] and log[-1][1]=='.pf/runs/r/task-index.md'
            assert log[-1][2].endswith('\n')
            assert (['render'] in log)==custom
            rows.append({'custom':custom,'tasks':tasks,'calls':log})
    for failure in ['path','render','write']:
        error=OSError(failure);log=[];run={'id':'r','tasks':[]}
        def fail(*a):raise error
        core=SimpleNamespace(render_task_index=fail if failure=='render' else lambda *a:'text')
        svc=fixture(cls,root,core=core,_run_path=fail if failure=='path' else lambda rid:root/'run.yaml',_atomic_text=fail if failure=='write' else lambda *a:log.append('write'))
        try:svc._write_task_index(run)
        except OSError as actual:assert actual is error
        else:raise AssertionError('publication failure hidden')
        assert not log
        rows.append({'failure':failure,'identity':True})
    class LazyCore:
        @property
        def render_task_index(self):raise error
    error=RuntimeError('capability failed')
    svc=fixture(cls,root,core=LazyCore(),_run_path=lambda rid:(_ for _ in ()).throw(OSError('path before capability')))
    try:svc._write_task_index({'id':'r'})
    except OSError as actual:assert str(actual)=='path before capability'
    else:raise AssertionError('path must precede capability')
    rows.append({'path_before_capability':True})
    return rows
def direct(root):
    try:from processforge_core.composition import build_completion_document_service
    except ImportError:return
    log=[]
    service=build_completion_document_service(project_root=root,run_path=lambda rid:root/'run.yaml',has_task_index=lambda:False,task_index=lambda *a:(_ for _ in ()).throw(AssertionError('unused')),atomic_text=lambda path,text:log.append([path.name,text]))
    assert 'No stage history recorded.' in service.summary({'id':'r'},{})
    service.write_task_index({'id':'r','tasks':[]})
    assert log==[['task-index.md','# Task Index: r\n\n']]
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
