"""Run the genuine ingress E2E, preserving startup diagnostics before fixture cleanup."""
import importlib
import json
import shutil
import sys
from pathlib import Path
root=Path.cwd();out=Path(__file__).resolve().parent
sys.path.insert(0,str(root/'tools'))
m=importlib.import_module('smoke_central_event_ingress')
original=m.pf
def checked(*args,**kwargs):
    try:
        return original(*args,**kwargs)
    except BaseException:
        if '--workplace' in args:
            workplace=Path(args[args.index('--workplace')+1])
            logs=workplace/'runtime/pf-runtime/logs'
            dest=out/'runtime-failure-diagnostics';dest.mkdir(exist_ok=True)
            for p in logs.glob('*.log'):
                shutil.copy2(p,dest/p.name)
            (dest/'command.json').write_text(json.dumps(list(args),indent=2))
        raise
m.pf=checked
raise SystemExit(m.main())
