"""Prove portability and baseline failure using isolated public source copies."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]
base=json.loads((OUT/'baseline.json').read_text(encoding='utf-8'))
paths=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=ROOT).decode().split('\0')
paths=sorted({p for p in paths if p and not p.startswith(('.pf/','.git/','.codex/','dist/')) and (ROOT/p).is_file()})
results=[]
tag = sys.argv[1] + '-' if len(sys.argv)>1 else ''

def run(root,label,script,expected):
    label=tag+label
    start=time.monotonic()
    result=subprocess.run([sys.executable,str(root/'tools'/script)],cwd=root,capture_output=True,text=True,encoding='utf-8',errors='replace',env=dict(os.environ,PYTHONIOENCODING='utf-8',PYTHONUTF8='1'),timeout=240)
    (OUT/(label+'.stdout.txt')).write_text(result.stdout,encoding='utf-8')
    (OUT/(label+'.stderr.txt')).write_text(result.stderr,encoding='utf-8')
    success=(result.returncode==0) if expected=='pass' else (result.returncode!=0 and 'AssertionError' in result.stderr)
    row=dict(label=label,script=script,expected=expected,exit_code=result.returncode,verified=success,elapsed_seconds=round(time.monotonic()-start,3))
    print(json.dumps(row),flush=True)
    return row

with tempfile.TemporaryDirectory(prefix='pf-f0102-public-') as raw:
    public=Path(raw)/'public'
    public.mkdir()
    for path in paths:
        target=public/path
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(ROOT/path,target)
    assert not (public/'.pf').exists() and not (public/'.git').exists()
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(run,public,'portable-core-update','smoke_core_update_manifest.py','pass'),pool.submit(run,public,'portable-search-security','smoke_garage_cross_project_security.py','pass')]
        results.extend(f.result() for f in futures)
    # Only the isolated copy is changed to baseline product code. Regression
    # tests remain the new tests so their failing assertions prove sensitivity.
    for path in ['src/processforge_core/core_update.py','src/processforge_core/garage.py']:
        (public/path).write_bytes(subprocess.check_output(['git','show',f"{base['head']}:{path}"],cwd=ROOT))
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(run,public,'baseline-core-update','smoke_core_update_manifest.py','fail'),pool.submit(run,public,'baseline-search-security','smoke_garage_cross_project_security.py','fail')]
        results.extend(f.result() for f in futures)
payload=dict(status='PASS' if all(x['verified'] for x in results) else 'FAIL',baseline=base['head'],public_file_count=len(paths),results=results)
(OUT/(tag+'isolated-validation.json')).write_text(json.dumps(payload,indent=2)+'\n',encoding='utf-8')
raise SystemExit(payload['status']!='PASS')
