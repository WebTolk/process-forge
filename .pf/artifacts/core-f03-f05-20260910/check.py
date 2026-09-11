"""Private bounded command runner and public-copy regression proof."""
from pathlib import Path
import argparse,subprocess,sys,time,json,tempfile,shutil
ROOT=Path(__file__).resolve().parents[3]
BASE=Path(__file__).resolve().parent
def execute(label,cmd,cwd=ROOT,timeout=360):
    start=time.monotonic()
    with (BASE/(label+'.stdout.txt')).open('w',encoding='utf-8') as out,(BASE/(label+'.stderr.txt')).open('w',encoding='utf-8') as err:
        try:
            result=subprocess.run(cmd,cwd=cwd,stdout=out,stderr=err,timeout=timeout)
            code=result.returncode
        except subprocess.TimeoutExpired:code=124
    record={'command':cmd,'cwd':str(cwd),'exit_code':code,'seconds':round(time.monotonic()-start,3)}
    (BASE/(label+'.json')).write_text(json.dumps(record,indent=2),encoding='utf-8')
    print(label,json.dumps(record),flush=True)
    return code
def main():
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['check','isolated']);parser.add_argument('label');parser.add_argument('args',nargs='+');a=parser.parse_args()
    if a.mode=='check':return execute(a.label,[sys.executable,*a.args])
    names=a.args
    sys.path.insert(0,str(ROOT/'tools'))
    import importlib.util
    spec=importlib.util.spec_from_file_location('inventory',ROOT/'tools/validate-process-forge-checksums.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    with tempfile.TemporaryDirectory(prefix='pf-evidence-public-') as raw:
        copy=Path(raw)/'public';copy.mkdir()
        for name,path in module.public_file_entries(ROOT):
            target=copy/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)
        results={}
        for name in names:results['portable-'+name]=execute(a.label+'-portable-'+name,[sys.executable,str(copy/'tools'/f'{name}.py')],cwd=copy)
        shutil.copyfile(BASE/'baseline-process_execution.py',copy/'src/processforge_core/process_execution.py')
        for cache in copy.rglob('__pycache__'):
            if cache.is_dir():
                if not cache.resolve().is_relative_to(copy.resolve()):
                    raise RuntimeError('cache escaped isolated public copy')
                shutil.rmtree(cache)
        for name in names:results['baseline-'+name]=execute(a.label+'-baseline-'+name,[sys.executable,str(copy/'tools'/f'{name}.py')],cwd=copy)
        if 'smoke_work_evidence_freshness' in names:
            code = 'import sys; sys.path.insert(0, sys.argv[1]); from smoke_work_evidence_freshness import test_saved_file_changed_and_resubmitted; test_saved_file_changed_and_resubmitted()'
            results['baseline-f04-file-change']=execute(a.label+'-baseline-f04-file-change',[sys.executable,'-c',code,str(copy/'tools')],cwd=copy)
        (BASE/(a.label+'-results.json')).write_text(json.dumps(results,indent=2),encoding='utf-8')
        return 0 if all(value==0 if key.startswith('portable-') else value not in (0,124) for key,value in results.items()) else 1
if __name__=='__main__':raise SystemExit(main())
