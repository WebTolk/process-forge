"""Primary execution, retained per-command evidence; never writes public source."""
import argparse
import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument('--root',type=Path,default=Path.cwd())
p.add_argument('--label',default='source')
p.add_argument('--tests',nargs='+',required=True)
p.add_argument('--workers',type=int,default=3)
args=p.parse_args()
out=Path(__file__).resolve().parent
root=args.root.resolve()
def check(name):
    cmd=[sys.executable,str(root/'tools'/f'{name}.py')]
    t=time.monotonic()
    try:
        r=subprocess.run(cmd,cwd=root,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=420)
        log=r.stdout+r.stderr
        code=r.returncode
    except subprocess.TimeoutExpired as e:
        log=str(e);code=124
    record={'name':name,'root':str(root),'command':cmd,'exit':code,'seconds':round(time.monotonic()-t,2)}
    prefix=out/f'{args.label}-{name}'
    prefix.with_suffix('.txt').write_text(log,encoding='utf-8')
    prefix.with_suffix('.json').write_text(json.dumps(record,indent=2))
    print(json.dumps(record),flush=True)
    return record
with ThreadPoolExecutor(max_workers=args.workers) as pool: results=list(pool.map(check,args.tests))
(out/f'{args.label}-tests.json').write_text(json.dumps(results,indent=2))
sys.exit(any(x['exit'] for x in results))
