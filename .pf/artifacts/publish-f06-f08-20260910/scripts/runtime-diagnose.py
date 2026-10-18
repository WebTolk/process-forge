import importlib.util,json,subprocess,sys,traceback
from pathlib import Path
root=Path('.pf/tmp/pf-update-5c95391').resolve();out=Path('.pf/artifacts/publish-f06-f08-20260910/runtime-diagnostics').resolve();out.mkdir(exist_ok=True)
sys.path.insert(0,str(root/'tools'))
spec=importlib.util.spec_from_file_location('probe',root/'tools/smoke_central_event_ingress.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
original=m.pf
def capture(*args,**kwargs):
 try:return original(*args,**kwargs)
 except BaseException:
  if args[:2]==('runtime','start'):
   wp=Path(args[args.index('--workplace')+1])
   for p in (wp/'runtime/pf-runtime').rglob('*.log'):
    if p.suffix=='.log':(out/p.name).write_bytes(p.read_bytes())
   (out/'failure.txt').write_text(traceback.format_exc())
  raise
m.pf=capture
raise SystemExit(m.main())
